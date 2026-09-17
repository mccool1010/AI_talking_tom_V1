import hashlib
import hmac
import logging
import os
import threading

import config
import db

log = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 100_000


class UserContextService:
    """
    Tracks which user Tom is currently talking to, and handles accounts.

    Passwords are hashed with PBKDF2-SHA256. Services that keep per-user
    state register with `on_user_changed` and reload when the user switches.
    """

    def __init__(self, default_user_id=None, default_user_name=None):
        self.collection = db.get_db()["users"]
        self.default_user_id = default_user_id or config.DEFAULT_USER_ID
        self.default_user_name = default_user_name or config.DEFAULT_USER_NAME
        self.user_id = self.default_user_id
        self.user_name = self.default_user_name
        self.logged_in = False
        self._listeners = []
        self._lock = threading.RLock()

        doc = self.collection.find_one({"user_id": self.user_id})
        if not doc:
            self.collection.insert_one({
                "user_id": self.user_id,
                "user_name": self.user_name,
                "password_hash": None,
                "salt": None,
            })
            log.info("Created default user %s", self.user_name)
        else:
            self.user_name = doc.get("user_name", self.user_name)

    # ------ Listeners ------

    def on_user_changed(self, callback):
        """Register `callback(user_id)`, called after every user switch."""
        self._listeners.append(callback)

    def _switch(self, user_id, user_name, logged_in):
        with self._lock:
            changed = user_id != self.user_id
            self.user_id = user_id
            self.user_name = user_name
            self.logged_in = logged_in
            if changed:
                for callback in self._listeners:
                    try:
                        callback(user_id)
                    except Exception:
                        log.exception("User-change listener %r failed", callback)
                log.info("Switched to user %s (%s)", user_name, user_id)

    # ------ Password hashing ------

    @staticmethod
    def _hash_password(password, salt=None):
        if salt is None:
            salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
        return salt, key

    # ------ Auth ------

    def user_exists(self, user_id):
        return self.collection.find_one({"user_id": user_id}) is not None

    def has_password(self, user_id):
        doc = self.collection.find_one({"user_id": user_id})
        return bool(doc and doc.get("password_hash"))

    def signup(self, user_id, user_name, password):
        """Create a user with a hashed password. Returns False if the id is taken."""
        if self.user_exists(user_id):
            return False
        salt, password_hash = self._hash_password(password)
        self.collection.insert_one({
            "user_id": user_id,
            "user_name": user_name,
            "password_hash": password_hash,
            "salt": salt,
        })
        log.info("Signed up user %s", user_id)
        return True

    def set_password(self, user_id, password):
        salt, password_hash = self._hash_password(password)
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"password_hash": password_hash, "salt": salt}},
        )

    def verify(self, user_id, password, allow_passwordless=False):
        """Check credentials without switching user. Returns the user doc or None."""
        doc = self.collection.find_one({"user_id": user_id})
        if not doc:
            return None
        if doc.get("password_hash") is None:
            return doc if allow_passwordless else None
        _, password_hash = self._hash_password(password or "", doc["salt"])
        if hmac.compare_digest(password_hash, doc["password_hash"]):
            return doc
        return None

    def login(self, user_id, password, allow_passwordless=False):
        """Verify credentials and make this the active user. Returns True on success."""
        doc = self.verify(user_id, password, allow_passwordless)
        if not doc:
            log.warning("Failed login for %s", user_id)
            return False
        self._switch(user_id, doc.get("user_name", "User"), True)
        return True

    def logout(self):
        """Return to the default user."""
        doc = self.collection.find_one({"user_id": self.default_user_id}) or {}
        self._switch(self.default_user_id, doc.get("user_name", self.default_user_name), False)

    # ------ Context ------

    def get_user_id(self):
        return self.user_id

    def get_user_name(self):
        return self.user_name

    def is_logged_in(self):
        return self.logged_in

    def set_user(self, user_id, user_name=None):
        doc = self.collection.find_one({"user_id": user_id})
        if not doc:
            doc = {"user_id": user_id, "user_name": user_name or "User",
                   "password_hash": None, "salt": None}
            self.collection.insert_one(dict(doc))
        self._switch(user_id, doc.get("user_name", user_name or "User"), self.logged_in)

    def list_users(self):
        return list(self.collection.find({}, {"_id": 0, "user_id": 1, "user_name": 1}))
