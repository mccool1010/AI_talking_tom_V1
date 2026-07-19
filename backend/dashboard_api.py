"""
Dashboard API — FastAPI server running as a background thread.

Exposes live Tom state via REST endpoints and WebSocket.
Started from main.py with access to all live service instances.
"""

import threading
import asyncio
import time
import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn


app = FastAPI(title="AI Talking Tom Dashboard API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service references (set by start_api)
_services = {}


# ---- Auth models ----

class SignupRequest(BaseModel):
    user_id: str
    user_name: str
    password: str

class LoginRequest(BaseModel):
    user_id: str
    password: str


# ---- Auth endpoints ----

@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    uc = _services["user_context"]
    ok = uc.signup(req.user_id, req.user_name, req.password)
    if not ok:
        return JSONResponse({"error": "User already exists"}, 409)
    return {"message": "Signup successful", "user_id": req.user_id}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    uc = _services["user_context"]
    ok = uc.login(req.user_id, req.password)
    if not ok:
        return JSONResponse({"error": "Invalid credentials"}, 401)
    return {
        "message": "Login successful",
        "user_id": uc.get_user_id(),
        "user_name": uc.get_user_name()
    }


@app.post("/api/auth/logout")
def logout():
    uc = _services["user_context"]
    uc.logout()
    return {"message": "Logged out"}


@app.get("/api/auth/status")
def auth_status():
    uc = _services["user_context"]
    return {
        "logged_in": uc.is_logged_in(),
        "user_id": uc.get_user_id(),
        "user_name": uc.get_user_name()
    }


# ---- State endpoint (full snapshot) ----

@app.get("/api/state")
def get_state():
    tom = _services["tom"]
    needs = _services["needs"]
    rel = _services["relationship"]
    personality = _services["personality"]
    memory = _services["emotion_memory"]

    return {
        "user": {
            "user_id": _services["user_context"].get_user_id(),
            "user_name": _services["user_context"].get_user_name()
        },
        "state": {
            "energy": tom.energy,
            "friendliness": tom.friendliness,
            "curiosity": tom.curiosity
        },
        "needs": {
            "hunger": needs.hunger,
            "sleepiness": needs.sleepiness,
            "social_need": needs.social_need
        },
        "relationship": {
            "trust": rel.trust,
            "friendship": rel.friendship,
            "attachment": rel.attachment
        },
        "personality": {
            "confidence": personality.confidence,
            "base_curiosity": personality.base_curiosity,
            "laziness": personality.laziness,
            "affection": personality.affection,
            "mood_stability": personality.mood_stability
        },
        "recent_emotions": memory.history[-5:] if memory.history else []
    }


# ---- Memories endpoint ----

@app.get("/api/memories")
def get_memories():
    profile = _services["profile"]
    data = profile.get_profile()
    if not data:
        return {"likes": [], "dislikes": [], "facts": []}
    return {
        "likes": data.get("likes", []),
        "dislikes": data.get("dislikes", []),
        "facts": data.get("facts", [])
    }


# ---- Conversation log endpoint ----

@app.get("/api/conversations")
def get_conversations():
    llm = _services["llm"]
    return {"messages": llm.history[-50:] if llm.history else []}


# ---- Camera feed (MJPEG stream) ----

def _generate_frames():
    face = _services.get("face")
    if not face or not face.cap.isOpened():
        return
    while True:
        ret, frame = face.cap.read()
        if not ret:
            break
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )
        time.sleep(0.1)  # ~10 FPS


@app.get("/api/camera")
def camera_feed():
    return StreamingResponse(
        _generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ---- WebSocket for real-time state push ----

@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            tom = _services["tom"]
            needs = _services["needs"]
            rel = _services["relationship"]

            await websocket.send_json({
                "state": {
                    "energy": tom.energy,
                    "friendliness": tom.friendliness,
                    "curiosity": tom.curiosity
                },
                "needs": {
                    "hunger": needs.hunger,
                    "sleepiness": needs.sleepiness,
                    "social_need": needs.social_need
                },
                "relationship": {
                    "trust": rel.trust,
                    "friendship": rel.friendship,
                    "attachment": rel.attachment
                }
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


# ---- Start API in background thread ----

def start_api(services, host="0.0.0.0", port=8000):
    """
    Start the FastAPI server in a background daemon thread.
    `services` is a dict of live service instances from main.py.
    """
    global _services
    _services = services

    def _run():
        uvicorn.run(app, host=host, port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    print(f"[Dashboard API] Running at http://localhost:{port}")
    print(f"[Dashboard API] Docs at http://localhost:{port}/docs")
