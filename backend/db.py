"""Shared MongoDB connection. One client for the whole process, with timeouts."""
import logging
import threading

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config

log = logging.getLogger(__name__)

_client = None
_lock = threading.Lock()


class DatabaseUnavailable(RuntimeError):
    pass


def get_client():
    global _client
    with _lock:
        if _client is None:
            _client = MongoClient(
                config.MONGO_URI,
                serverSelectionTimeoutMS=config.MONGO_TIMEOUT_MS,
                connectTimeoutMS=config.MONGO_TIMEOUT_MS,
            )
        return _client


def get_db():
    return get_client()[config.MONGO_DB]


def set_client(client):
    """Replace the shared client (used by tests to inject mongomock)."""
    global _client
    with _lock:
        _client = client


def check_connection():
    """Fail fast with a readable message when MongoDB is not reachable."""
    try:
        get_client().admin.command("ping")
    except PyMongoError as e:
        raise DatabaseUnavailable(
            f"Cannot reach MongoDB at {config.MONGO_URI}. "
            "Install MongoDB Community Server and make sure the service is running."
        ) from e
    log.info("Connected to MongoDB at %s (db=%s)", config.MONGO_URI, config.MONGO_DB)
