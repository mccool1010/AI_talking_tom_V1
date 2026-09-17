"""
Test setup: backend modules on sys.path, an in-memory MongoDB (mongomock)
and a fake LLM, so the suite runs without models, GPU or a database server.
"""
import sys
from pathlib import Path

import mongomock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import db  # noqa: E402
import llm_provider  # noqa: E402


class FakeLlama:
    """Records every chat call and returns queued replies."""

    def __init__(self):
        self.calls = []
        self.replies = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        content = self.replies.pop(0) if self.replies else "Meow!"
        return {"choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


class FakeUser:
    def __init__(self, user_id="alice"):
        self.user_id = user_id

    def get_user_id(self):
        return self.user_id


@pytest.fixture(autouse=True)
def mongo():
    client = mongomock.MongoClient()
    db.set_client(client)
    yield client
    db.set_client(None)


@pytest.fixture
def fake_llm():
    llm = FakeLlama()
    llm_provider.set_llm(llm)
    yield llm
    llm_provider.set_llm(None)


@pytest.fixture
def user():
    return FakeUser()
