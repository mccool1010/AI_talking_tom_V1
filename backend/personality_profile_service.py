import logging
import time
import config
import db


log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


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
        self.collection = db.get_db()["personality"]
        self.switch_user(user_context.get_user_id() if user_context else config.DEFAULT_USER_ID)

    def switch_user(self, user_id):
        self.user_id = user_id
        doc = self.collection.find_one({"tom_id": user_id})
        if not doc:
            doc = {"tom_id": user_id, **self.DEFAULTS, "last_updated": time.time()}
            self.collection.insert_one(dict(doc))
        for name, default in self.DEFAULTS.items():
            setattr(self, name, doc.get(name, default))

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
            _debug(
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
