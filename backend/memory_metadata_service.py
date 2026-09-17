from datetime import date

import db


class MemoryMetadataService:
    """Remembers when the daily memory decay last ran."""

    def __init__(self):
        self.collection = db.get_db()["memory_metadata"]
        if not self.collection.find_one({"system": "memory"}):
            self.collection.insert_one({"system": "memory", "last_decay_date": ""})

    def should_decay(self):
        doc = self.collection.find_one({"system": "memory"}) or {}
        return doc.get("last_decay_date") != date.today().isoformat()

    def mark_decay_done(self):
        self.collection.update_one(
            {"system": "memory"},
            {"$set": {"last_decay_date": date.today().isoformat()}},
        )
