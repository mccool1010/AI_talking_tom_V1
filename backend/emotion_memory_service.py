import logging
# emotion_memory_service.py

from collections import defaultdict, Counter
import config
import db

log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


class EmotionMemoryService:

    def __init__(self, user_context=None):
        self.collection = db.get_db()["emotions"]
        self.switch_user(user_context.get_user_id() if user_context else config.DEFAULT_USER_ID)

    def switch_user(self, user_id):
        self.user_id = user_id
        doc = self.collection.find_one({"conversation_id": user_id})
        if doc:
            self.history = doc.get("emotion_history", [])
        else:
            self.collection.insert_one({"conversation_id": user_id, "emotion_history": []})
            self.history = []

    def get_mood(self, emotion):

        self.history.append(emotion)

        self.history = self.history[-20:]
        self.collection.update_one(
    {
        "conversation_id": self.user_id
    },
    {
        "$set":
        {
            "emotion_history":
            self.history
        }
    }
)

        scores = defaultdict(int)

        for index, emotion in enumerate(self.history):

            weight = index + 1

            scores[emotion] += weight

        mood = max(
            scores,
            key=scores.get
        )
        _debug("Emotion History:", self.history)
        

        return mood