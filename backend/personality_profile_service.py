import time
from pymongo import MongoClient


class PersonalityProfileService:
    """
    Stores and retrieves Tom's persistent personality traits.

    Traits are long-term values that evolve gradually over many
    interactions. They survive restarts via MongoDB persistence.

    Traits:
        confidence (0-100): Assertiveness, willingness to tease
        base_curiosity (0-100): Long-term curiosity baseline
        laziness (0-100): Preference for rest, energy drain rate
        affection (0-100): Warmth, care, attachment growth rate
        mood_stability (0-100): Resistance to emotional swings
    """

    DEFAULTS = {
        "confidence": 50,
        "base_curiosity": 50,
        "laziness": 30,
        "affection": 50,
        "mood_stability": 60
    }

    TRAIT_NAMES = list(DEFAULTS.keys())

    def __init__(self, user_context=None):
        print("Loading Personality Profile Service...")

        self.user_id = user_context.get_user_id() if user_context else "default"

        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["talking_tom"]
        self.collection = self.db["personality"]

        doc = self.collection.find_one({"tom_id": self.user_id})

        if doc:
            self.confidence = doc["confidence"]
            self.base_curiosity = doc["base_curiosity"]
            self.laziness = doc["laziness"]
            self.affection = doc["affection"]
            self.mood_stability = doc["mood_stability"]
            print("Personality Profile Loaded")
        else:
            self.collection.insert_one({
                "tom_id": self.user_id,
                **self.DEFAULTS,
                "last_updated": time.time()
            })
            self.confidence = self.DEFAULTS["confidence"]
            self.base_curiosity = self.DEFAULTS["base_curiosity"]
            self.laziness = self.DEFAULTS["laziness"]
            self.affection = self.DEFAULTS["affection"]
            self.mood_stability = self.DEFAULTS["mood_stability"]
            print("New Personality Profile Created")

        print("Personality Profile Service Ready")

    def get_traits(self):
        """Return all personality traits as a dictionary."""
        return {
            "confidence": self.confidence,
            "base_curiosity": self.base_curiosity,
            "laziness": self.laziness,
            "affection": self.affection,
            "mood_stability": self.mood_stability
        }

    def get_trait(self, name):
        """Return a single trait value by name."""
        return getattr(self, name)

    def update_trait(self, name, amount):
        """
        Update a trait by the given delta amount.

        The value is clamped to [0, 100] and persisted to MongoDB.
        """
        current = getattr(self, name)
        new_value = max(0, min(100, current + amount))
        setattr(self, name, new_value)

        self.collection.update_one(
            {"tom_id": self.user_id},
            {
                "$set": {
                    name: new_value,
                    "last_updated": time.time()
                }
            }
        )

        if abs(amount) >= 0.5:
            print(
                f"[Personality] {name}: "
                f"{current:.1f} -> {new_value:.1f} "
                f"(delta: {amount:+.1f})"
            )

    def apply_deltas(self, deltas):
        """
        Apply a dictionary of {trait_name: delta} updates.

        Args:
            deltas: dict mapping trait names to float deltas.
        """
        for name, amount in deltas.items():
            if name in self.TRAIT_NAMES and amount != 0:
                self.update_trait(name, amount)
