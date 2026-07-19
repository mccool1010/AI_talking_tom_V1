# emotion_memory_service.py

from collections import defaultdict, Counter
from pymongo import MongoClient

class EmotionMemoryService:

    def __init__(self, user_context=None):

        print("Loading Emotion Memory Service...")

        self.user_id = user_context.get_user_id() if user_context else "default"

        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["talking_tom"]
        self.collection = self.db["emotions"]
        doc = self.collection.find_one({
            "conversation_id": self.user_id

        })
        if doc:
            self.history = doc["emotion_history"]
            print("Emotion History Loaded")
        else:
            self.collection.insert_one({
                "conversation_id":"default",
                "emotion_history": []
            })
            self.history = []
            print("New Emotion History Created")
        print("Emotion Memory Service Ready")

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
        print("Emotion History:", self.history)
        

        return mood