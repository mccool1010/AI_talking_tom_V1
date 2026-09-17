from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import dashboard_api
from user_context_service import UserContextService


class FakeFace:
    def get_jpeg(self):
        return b"jpeg"


@pytest.fixture
def services(monkeypatch):
    uc = UserContextService()
    uc.signup("bob", "Bob", "hunter22!")
    stats = SimpleNamespace(energy=1, friendliness=2, curiosity=3, hunger=4, sleepiness=5,
                            social_need=6, trust=7, friendship=8, attachment=9)
    svc = {
        "user_context": uc,
        "tom": stats, "needs": stats, "relationship": stats,
        "personality": SimpleNamespace(get_traits=lambda: {"confidence": 50}),
        "emotion_memory": SimpleNamespace(history=["happy"]),
        "profile": SimpleNamespace(get_profile=lambda: {"likes": [{"value": "secret"}]}),
        "llm": SimpleNamespace(history=[{"role": "user", "content": "private"}]),
        "face": FakeFace(),
    }
    monkeypatch.setattr(dashboard_api, "_services", svc)
    dashboard_api._sessions.clear()
    dashboard_api._failed_logins.clear()
    return svc


def local_client():
    return TestClient(dashboard_api.app, client=("127.0.0.1", 50000))


def remote_client():
    return TestClient(dashboard_api.app, client=("192.168.1.50", 50000))


def login(client, user_id="bob", password="hunter22!"):
    res = client.post("/api/auth/login", json={"user_id": user_id, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.mark.parametrize("path", ["/api/state", "/api/memories", "/api/conversations", "/api/camera"])
def test_data_endpoints_require_login(services, path):
    assert local_client().get(path).status_code == 401
    assert local_client().get(path, headers={"Authorization": "Bearer forged"}).status_code == 401


def test_logged_in_user_sees_data(services):
    client = local_client()
    headers = login(client)
    assert client.get("/api/memories", headers=headers).json()["likes"] == [{"value": "secret"}]
    assert client.get("/api/state", headers=headers).json()["state"]["energy"] == 1
    assert client.get("/api/auth/status", headers=headers).json()["user_id"] == "bob"


def test_session_loses_access_when_another_user_logs_in(services):
    client = local_client()
    bob = login(client)
    services["user_context"].signup("carol", "Carol", "password123")
    login(client, "carol", "password123")
    assert client.get("/api/memories", headers=bob).status_code == 409
    assert client.get("/api/auth/status", headers=bob).json() == {"logged_in": False}


def test_passwordless_default_account_is_local_only(services):
    assert local_client().post("/api/auth/login", json={"user_id": "default"}).status_code == 200
    assert remote_client().post("/api/auth/login", json={"user_id": "default"}).status_code == 401


def test_logout_invalidates_token(services):
    client = local_client()
    headers = login(client)
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/memories", headers=headers).status_code == 401
    assert services["user_context"].get_user_id() == "default"


def test_lockout_after_repeated_failures(services):
    client = local_client()
    for _ in range(dashboard_api.MAX_FAILED_LOGINS):
        assert client.post("/api/auth/login",
                           json={"user_id": "bob", "password": "nope"}).status_code == 401
    res = client.post("/api/auth/login", json={"user_id": "bob", "password": "hunter22!"})
    assert res.status_code == 429


def test_signup_validates_input(services):
    client = local_client()
    assert client.post("/api/auth/signup", json={
        "user_id": "x y", "user_name": "X", "password": "longenough"}).status_code == 422
    assert client.post("/api/auth/signup", json={
        "user_id": "dave", "user_name": "Dave", "password": "short"}).status_code == 422
    assert client.post("/api/auth/signup", json={
        "user_id": "bob", "user_name": "Bob", "password": "longenough"}).status_code == 409


def test_camera_stream_yields_frames_until_session_ends(services):
    # TestClient buffers whole responses, so drive the MJPEG generator directly.
    token = login(local_client())["Authorization"].split()[1]
    frames = dashboard_api._generate_frames(token)
    assert b"Content-Type: image/jpeg" in next(frames) and b"jpeg" in next(frames)
    dashboard_api._sessions.clear()
    assert list(frames) == []


def test_camera_rejects_other_users_token(services):
    client = local_client()
    bob = login(client)
    services["user_context"].logout()
    assert client.get("/api/camera", headers=bob).status_code == 409


def test_websocket_rejects_missing_token(services):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with local_client().websocket_connect("/ws/state") as ws:
            ws.receive_json()


def test_websocket_streams_with_token(services):
    client = local_client()
    token = login(client)["Authorization"].split()[1]
    with client.websocket_connect(f"/ws/state?token={token}") as ws:
        assert ws.receive_json()["needs"]["hunger"] == 4


def test_cors_blocks_unknown_origins(services):
    res = local_client().options("/api/state", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in res.headers
    res = local_client().options("/api/state", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
