from pymongo import MongoClient
from datetime import date


class MemoryMetadataService:

    def __init__(self):

        self.client = MongoClient(
            "mongodb://localhost:27017/"
        )

        self.db = self.client["talking_tom"]

        self.collection = self.db["memory_metadata"]

        if not self.collection.find_one(
            {"system": "memory"}
        ):
            self.collection.insert_one(
                {
                    "system": "memory",
                    "last_decay_date": ""
                }
            )

    def should_decay(self):

        doc = self.collection.find_one(
            {"system": "memory"}
        )

        today = date.today().isoformat()

        return doc["last_decay_date"] != today

    def mark_decay_done(self):

        today = date.today().isoformat()

        self.collection.update_one(
            {"system": "memory"},
            {
                "$set":
                {
                    "last_decay_date": today
                }
            }
        )