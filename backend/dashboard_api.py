"""
Dashboard API (FastAPI) running in a background thread.

Security model:
- Binds to 127.0.0.1 unless TOM_API_HOST says otherwise.
- Every data endpoint requires a session token from /api/auth/login, sent as
  `Authorization: Bearer <token>`, or as `?token=` for <img> and WebSocket
  URLs that cannot set headers.
- A session only sees data while its user is the one Tom is talking to.
- Accounts without a password can only log in from the local machine.
"""
import asyncio
import ipaddress
import logging
import secrets
import threading
import time

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import config

log = logging.getLogger(__name__)

app = FastAPI(title="AI Talking Tom Dashboard API", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

_services = {}

# ---- Sessions ----

_sessions = {}          # token -> {"user_id", "expires"}
_failed_logins = {}     # user_id -> (count, first_failure_time)
_session_lock = threading.Lock()
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300


def _new_session(user_id):
    token = secrets.token_urlsafe(32)
    with _session_lock:
        _sessions[token] = {"user_id": user_id,
                            "expires": time.time() + config.API_SESSION_HOURS * 3600}
    return token


def _get_session(token):
    if not token:
        return None
    with _session_lock:
        session = _sessions.get(token)
        if session and session["expires"] < time.time():
            _sessions.pop(token, None)
            return None
        return session


def _is_locked_out(user_id):
    count, since = _failed_logins.get(user_id, (0, 0))
    if count >= MAX_FAILED_LOGINS and time.time() - since < LOCKOUT_SECONDS:
        return True
    if time.time() - since >= LOCKOUT_SECONDS:
        _failed_logins.pop(user_id, None)
    return False


def _record_failure(user_id):
    count, since = _failed_logins.get(user_id, (0, time.time()))
    _failed_logins[user_id] = (count + 1, since)


def _is_local(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return host == "localhost"


def _token_from(authorization, token):
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return token


def require_session(authorization: str = Header(default=None), token: str = Query(default=None)):
    raw = _token_from(authorization, token)
    session = _get_session(raw)
    if not session:
        raise HTTPException(401, "Not logged in")
    return {**session, "token": raw}


def require_active_user(session=Depends(require_session)):
    """The session's user must be the user Tom is currently talking to."""
    if session["user_id"] != _services["user_context"].get_user_id():
        raise HTTPException(409, "Another user is currently active. Log in again.")
    return session


# ---- Models ----

class SignupRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    user_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    password: str = Field(default="", max_length=256)


# ---- Auth endpoints ----

@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    if not _services["user_context"].signup(req.user_id, req.user_name, req.password):
        raise HTTPException(409, "User already exists")
    return {"message": "Signup successful", "user_id": req.user_id}


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    uc = _services["user_context"]
    if _is_locked_out(req.user_id):
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    local = _is_local(request.client.host if request.client else None)
    if not uc.login(req.user_id, req.password, allow_passwordless=local):
        _record_failure(req.user_id)
        raise HTTPException(401, "Invalid credentials")
    _failed_logins.pop(req.user_id, None)
    return {
        "message": "Login successful",
        "token": _new_session(uc.get_user_id()),
        "user_id": uc.get_user_id(),
        "user_name": uc.get_user_name(),
    }


@app.post("/api/auth/logout")
def logout(session=Depends(require_session)):
    with _session_lock:
        _sessions.pop(session["token"], None)
    uc = _services["user_context"]
    if session["user_id"] == uc.get_user_id():
        uc.logout()
    return {"message": "Logged out"}


@app.get("/api/auth/status")
def auth_status(authorization: str = Header(default=None), token: str = Query(default=None)):
    session = _get_session(_token_from(authorization, token))
    uc = _services["user_context"]
    if not session or session["user_id"] != uc.get_user_id():
        return {"logged_in": False}
    return {"logged_in": True, "user_id": uc.get_user_id(), "user_name": uc.get_user_name()}


# ---- Data endpoints ----

def _live_state():
    tom, needs, rel = _services["tom"], _services["needs"], _services["relationship"]
    return {
        "state": {"energy": tom.energy, "friendliness": tom.friendliness, "curiosity": tom.curiosity},
        "needs": {"hunger": needs.hunger, "sleepiness": needs.sleepiness, "social_need": needs.social_need},
        "relationship": {"trust": rel.trust, "friendship": rel.friendship, "attachment": rel.attachment},
    }


@app.get("/api/state")
def get_state(session=Depends(require_active_user)):
    uc = _services["user_context"]
    memory = _services["emotion_memory"]
    return {
        "user": {"user_id": uc.get_user_id(), "user_name": uc.get_user_name()},
        **_live_state(),
        "personality": _services["personality"].get_traits(),
        "recent_emotions": memory.history[-5:] if memory.history else [],
    }


@app.get("/api/memories")
def get_memories(session=Depends(require_active_user)):
    data = _services["profile"].get_profile()
    return {k: data.get(k, []) for k in ("likes", "dislikes", "facts")}


@app.get("/api/conversations")
def get_conversations(session=Depends(require_active_user)):
    history = _services["llm"].history
    return {"messages": history[-50:] if history else []}


def _generate_frames(token):
    face = _services.get("face")
    while face and _get_session(token):
        jpeg = face.get_jpeg()
        if jpeg is not None:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        time.sleep(0.1)  # ~10 FPS


@app.get("/api/camera")
def camera_feed(session=Depends(require_active_user)):
    return StreamingResponse(
        _generate_frames(session["token"]),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ---- WebSocket for real-time state push ----

@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket, token: str = Query(default=None)):
    session = _get_session(token)
    if not session or session["user_id"] != _services["user_context"].get_user_id():
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        while _get_session(token) and session["user_id"] == _services["user_context"].get_user_id():
            await websocket.send_json(_live_state())
            await asyncio.sleep(1)
        await websocket.close(code=4401)
    except WebSocketDisconnect:
        pass


# ---- Built dashboard (npm run build) served from the same origin ----

def _mount_dashboard():
    dist = config.REPO_ROOT / "dashboard" / "dist"
    if dist.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")


# ---- Start API in background thread ----

def start_api(services, host=None, port=None):
    """Start the API in a daemon thread. `services` maps names to live service objects."""
    global _services
    _services = services
    host = host or config.API_HOST
    port = port or config.API_PORT
    if not _is_local(host):
        log.warning("Dashboard API is exposed on %s; passwordless accounts are blocked "
                    "for remote clients, but use a password for every account.", host)
    _mount_dashboard()

    def _run():
        uvicorn.run(app, host=host, port=port, log_level="warning")

    threading.Thread(target=_run, daemon=True, name="dashboard-api").start()
    log.info("Dashboard API running at http://%s:%d", host, port)
