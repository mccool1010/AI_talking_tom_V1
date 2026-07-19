import hashlib
import os
from pymongo import MongoClient


class UserContextService:
    """
    Central user identity manager with authentication.

    Handles signup, login, logout, and user scoping.
    Passwords are hashed with PBKDF2 (built-in Python, no pip needed).
    All user-scoped services use get_user_id() to scope MongoDB queries.
    """

    def __init__(self, default_user_id="default", default_user_name="Hari"):
        print("Loading User Context Service...")

        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["talking_tom"]
        self.collection = self.db["users"]

        self.user_id = default_user_id
        self.user_name = default_user_name
        self.logged_in = False

        # Ensure default user exists (backward compat)
        doc = self.collection.find_one({"user_id": self.user_id})
        if not doc:
            self.collection.insert_one({
                "user_id": self.user_id,
                "user_name": self.user_name,
                "password_hash": None,
                "salt": None
            })
            print(f"Created default user: {self.user_name}")
        else:
            self.user_name = doc.get("user_name", self.user_name)
            print(f"User loaded: {self.user_name} (id={self.user_id})")

        print("User Context Service Ready")

    # ------ Password hashing (built-in, no dependencies) ------

    def _hash_password(self, password, salt=None):
        if salt is None:
            salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return salt, key

    # ------ Auth methods ------

    def signup(self, user_id, user_name, password):
        """Create a new user with a hashed password."""
        if self.collection.find_one({"user_id": user_id}):
            print(f"[Auth] User already exists: {user_id}")
            return False

        salt, password_hash = self._hash_password(password)
        self.collection.insert_one({
            "user_id": user_id,
            "user_name": user_name,
            "password_hash": password_hash,
            "salt": salt
        })
        print(f"[Auth] Signup successful: {user_name} (id={user_id})")
        return True

    def login(self, user_id, password):
        """Verify password and switch to user. Returns True on success."""
        doc = self.collection.find_one({"user_id": user_id})
        if not doc:
            print(f"[Auth] User not found: {user_id}")
            return False

        # Default user has no password (backward compat)
        if doc.get("password_hash") is None:
            self.user_id = user_id
            self.user_name = doc.get("user_name", "User")
            self.logged_in = True
            print(f"[Auth] Login (no password): {self.user_name}")
            return True

        _, password_hash = self._hash_password(password, doc["salt"])
        if password_hash == doc["password_hash"]:
            self.user_id = user_id
            self.user_name = doc.get("user_name", "User")
            self.logged_in = True
            print(f"[Auth] Login successful: {self.user_name}")
            return True

        print(f"[Auth] Wrong password for: {user_id}")
        return False

    def logout(self):
        """Reset to default user."""
        self.user_id = "default"
        self.user_name = "Hari"
        self.logged_in = False
        print("[Auth] Logged out, back to default user")

    # ------ Context methods (unchanged) ------

    def get_user_id(self):
        return self.user_id

    def get_user_name(self):
        return self.user_name

    def is_logged_in(self):
        return self.logged_in

    def set_user(self, user_id, user_name=None):
        doc = self.collection.find_one({"user_id": user_id})
        if doc:
            self.user_id = user_id
            self.user_name = doc.get("user_name", user_name or "User")
            print(f"[UserContext] Switched to: {self.user_name} (id={self.user_id})")
        else:
            name = user_name or "User"
            self.collection.insert_one({
                "user_id": user_id,
                "user_name": name,
                "password_hash": None,
                "salt": None
            })
            self.user_id = user_id
            self.user_name = name
            print(f"[UserContext] Created new user: {self.user_name} (id={self.user_id})")

    def list_users(self):
        users = self.collection.find({}, {"_id": 0, "user_id": 1, "user_name": 1})
        return list(users)
