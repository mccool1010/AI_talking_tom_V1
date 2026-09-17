import logging
import time

import config
import db

ENERGY_RECOVERY_PER_HOUR = 20  # Tom rests while nobody is talking to him

log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


class TomStateService:

    DEFAULTS = {"energy": 100, "friendliness": 50, "curiosity": 50}

    def __init__(self, user_context=None):
        self.collection = db.get_db()["state"]
        self.switch_user(user_context.get_user_id() if user_context else config.DEFAULT_USER_ID)

    def switch_user(self, user_id):
        self.user_id = user_id
        doc = self.collection.find_one({"tom_id": user_id})
        if not doc:
            doc = {"tom_id": user_id, **self.DEFAULTS}
            self.collection.insert_one(dict(doc))
        self.energy = doc["energy"]
        self.friendliness = doc["friendliness"]
        self.curiosity = doc["curiosity"]
        self.updated_at = doc.get("updated_at")
        self.recover()

    def recover(self, now=None):
        """Restore energy for the time since the last update."""
        now = time.time() if now is None else now
        if self.updated_at is not None:
            hours = max(0.0, (now - self.updated_at) / 3600)
            self.energy = round(min(100, self.energy + ENERGY_RECOVERY_PER_HOUR * hours), 1)
        self.updated_at = now
        self.collection.update_one(
            {"tom_id": self.user_id},
            {"$set": {"energy": self.energy, "updated_at": now}},
        )

    def update_energy(self, amount):
        self.energy += amount
        self.energy = max(0, min(100, self.energy))
        self.collection.update_one(
             {
             "tom_id": self.user_id
              },
             {
             "$set":
                {
                "energy": self.energy
                }
             }
             )
        _debug("Energy:", self.energy)
    def update_friendliness(self, amount):
        self.friendliness += amount

        self.friendliness = max(0, min(100, self.friendliness) )

        self.collection.update_one(
         {
            "tom_id": self.user_id
         },
         {
            "$set":
            {
                "friendliness": self.friendliness
            }
          }
         )
        _debug("Friendliness:",self.friendliness)
    def update_curiosity(self, amount):
        self.curiosity += amount
        self.curiosity = max(0,min(100, self.curiosity))

        self.collection.update_one(
         {
            "tom_id": self.user_id
         },
         {
            "$set":
            {
                "curiosity": self.curiosity
            }
         }
         )
        _debug("Curiosity:",self.curiosity)
    def update_from_conversation(self, mood, personality=None):
        self.recover()
        if personality is None:
            personality = {"laziness": 30, "base_curiosity": 50, "affection": 50}
        # Lazier Tom loses energy faster
        energy_drain = -1 - (personality["laziness"] // 50)
        self.update_energy(energy_drain)
        if mood == "happy":
            # Affectionate Tom gains friendliness faster
            gain = 1 + (personality["affection"] // 70)
            self.update_friendliness(gain)
        elif mood == "sad":
            self.update_friendliness(+2)
        elif mood == "angry":
            self.update_friendliness(-1)
        # Curious Tom gains curiosity faster
        curiosity_gain = 1 + (personality["base_curiosity"] // 50)
        self.update_curiosity(curiosity_gain)