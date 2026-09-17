import logging
import time

import config
import db

# Change per hour while Tom is not talking: he eats and naps on his own and
# slowly gets lonely. Without this the needs only ever rose and got stuck at 100.
RECOVERY_PER_HOUR = {"hunger": -15, "sleepiness": -20, "social_need": +10}


log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


def _clamp(value):
    return round(max(0, min(100, value)), 1)


class NeedsService:

    DEFAULTS = {"hunger": 0, "sleepiness": 0, "social_need": 50}

    def __init__(self, user_context=None):
        self.collection = db.get_db()["needs"]
        self.switch_user(user_context.get_user_id() if user_context else config.DEFAULT_USER_ID)

    def switch_user(self, user_id):
        self.user_id = user_id
        doc = self.collection.find_one({"tom_id": user_id})
        if not doc:
            doc = {"tom_id": user_id, **self.DEFAULTS}
            self.collection.insert_one(dict(doc))
        for key, default in self.DEFAULTS.items():
            setattr(self, key, doc.get(key, default))
        self.updated_at = doc.get("updated_at")
        self.recover()

    def recover(self, now=None):
        """Apply the needs' natural drift for the time since the last update."""
        now = time.time() if now is None else now
        if self.updated_at is not None:
            hours = max(0.0, (now - self.updated_at) / 3600)
            for key, rate in RECOVERY_PER_HOUR.items():
                setattr(self, key, _clamp(getattr(self, key) + rate * hours))
        self.updated_at = now
        self.collection.update_one(
            {"tom_id": self.user_id},
            {"$set": {**{k: getattr(self, k) for k in self.DEFAULTS}, "updated_at": now}},
        )

    def update_hunger(self, amount):
        self.hunger += amount
        self.hunger = max(0,min(100, self.hunger))

        self.collection.update_one(
        {
            "tom_id": self.user_id
        },
        {
            "$set":
            {
                "hunger": self.hunger
            }
        }
    )

        _debug("Hunger:",self.hunger)
    def update_sleepiness(self, amount):
        self.sleepiness += amount

        self.sleepiness = max(0,min(100, self.sleepiness))

        self.collection.update_one(
        {
            "tom_id": self.user_id
        },
        {
            "$set":
            {
                "sleepiness": self.sleepiness
            }
        }
    )

        _debug("Sleepiness:",self.sleepiness)
    def update_social_need(self, amount):
        self.social_need += amount

        self.social_need = max(0, min(100, self.social_need))

        self.collection.update_one(
        {
            "tom_id": self.user_id
        },
        {
            "$set":
            {
                "social_need": self.social_need
            }
        }
    )

        _debug("Social Need:",self.social_need )
    def update_from_conversation(self, personality=None):
        self.recover()
        if personality is None:
            personality = {"laziness": 30, "affection": 50}
        self.update_hunger(+1)
        # Lazier Tom gets sleepier faster
        sleepiness_gain = 1 + (personality["laziness"] // 50)
        self.update_sleepiness(sleepiness_gain)
        # Affectionate Tom craves more social interaction
        social_drain = -1 if personality["affection"] < 50 else -2
        self.update_social_need(social_drain)