from pymongo import MongoClient
from datetime import datetime

class ProfileMemoryService:

    def __init__(self, user_context=None):

        print("Loading Profile Memory Service...")

        self.user_id = user_context.get_user_id() if user_context else "Hari"

        self.client = MongoClient(
            "mongodb://localhost:27017/"
        )

        self.db = self.client["talking_tom"]

        self.collection = self.db["profile_memory"]

        doc = self.collection.find_one(
            {
                "owner": self.user_id
            }
        )

        if not doc:

            self.collection.insert_one(
                {
                    "owner": self.user_id,

                    "likes": [],

                    "dislikes": [],

                    "facts": []
                }
            )

            print("New Profile Created")

        else:

            print("Profile Loaded")
    def add_like(self, item):
        profile = self.get_profile()

        for like in profile["likes"]:
            if like["value"].lower() == item.lower():
                self.collection.update_one(
            {
                "owner": self.user_id,
                "likes.value": like["value"]
            },
            {
                "$inc":
                {
                    "likes.$.importance": 1
                },
                "$set":
                {
                    "likes.$.last_accessed":
                    datetime.now().isoformat()
                }
            }
        )

        print(
            "Like Importance Increased:",
            item
        )

        return

        self.collection.update_one(
        {
            "owner": self.user_id
        },
        {
            "$push":
            {
                "likes":
                {
                    "value": item,
                    "learned_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "importance": 5
                }
            }
        }
    )
        print("Saved Like:", item)
    def add_fact(self, fact,importance=5):
        profile = self.get_profile()

        for existing_fact in profile["facts"]:
            if existing_fact["value"].lower() == fact.lower():
                self.collection.update_one(
            {
                "owner": self.user_id,
                "facts.value": existing_fact["value"]
            },
            {
                "$inc":
                {
                    "facts.$.importance": 1
                },
                  "$set": {
                      "facts.$.last_accessed": datetime.now().isoformat()
                      }
            }
        )
                print(
            "Fact Importance Increased:",
            fact
        )
                return

        self.collection.update_one(
        {
            "owner": self.user_id
        },
        {
            "$push":
            {
                "facts":
                {
                    "value": fact,
                    "learned_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "importance": importance
                }
            }
        }
    )
        print("Saved Fact:", fact)
    def get_profile(self):
        return self.collection.find_one(
        {
            "owner": self.user_id
        }
    )
    def get_likes(self):
        profile = self.get_profile()
        return [
        like["value"]
        for like in profile["likes"]
    ]


    def get_dislikes(self):
        profile = self.get_profile()
        return [
        dislike["value"]
        for dislike in profile["dislikes"]
    ]


    def get_facts(self):
        profile = self.get_profile()
        return [
        fact["value"]
        for fact in profile["facts"]
    ]
    def add_dislike(self, item):
        profile = self.get_profile()
        for dislike in profile["dislikes"]:
            if dislike["value"].lower() == item.lower():
                self.collection.update_one(
            {
                "owner": self.user_id,
                "dislikes.value": dislike["value"]
            },
            {
                "$inc":
                {
                    "dislikes.$.importance": 1
                },
                "$set":
                {
                    "dislikes.$.last_accessed":
                    datetime.now().isoformat()
                }
            }
        )

        print(
            "Dislike Importance Increased:",
            item
        )

        return

        self.collection.update_one(
        {
            "owner": self.user_id
        },
        {
            "$push":
            {
                "dislikes":
                {
                    "value": item,
                    "learned_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "importance": 5
                }
            }
        }
    )
        print("Saved Dislike:", item)
    def get_recent_likes(self, limit=5):
            profile = self.get_profile()
            likes = sorted(
        profile["likes"],
        key=lambda x: x["learned_at"],
        reverse=True
    )
            return likes[:limit]
    def get_recent_facts(self, limit=5):
            profile = self.get_profile()
            facts = sorted(
        profile["facts"],
        key=lambda x: x["learned_at"],
        reverse=True
    )
            return facts[:limit]
    def get_recent_dislikes(self, limit=5):
        profile = self.get_profile()
        dislikes = sorted(
        profile["dislikes"],
        key=lambda x: x["learned_at"],
        reverse=True
    )
        return dislikes[:limit]
    def get_important_facts(self):
        profile = self.get_profile()

        result = []
        for fact in profile["facts"]:
            if fact["importance"] >= 7:
                result.append(
                fact["value"]
            )

        return result
    def search_memories(self, query):
        query = query.lower()

        results = []

        profile = self.get_profile()

        for like in profile["likes"]:
            if query in like["value"].lower():
                results.append(
                like["value"]
            )
        for dislike in profile["dislikes"]:
            if query in dislike["value"].lower():
                results.append(
                dislike["value"]
            )

        for fact in profile["facts"]:
            if query in fact["value"].lower():
                results.append(
                fact["value"]
            )

        return results
    def get_top_memories(self, query, limit=3):
        query = query.lower()

        results = []

        profile = self.get_profile()
        for like in profile["likes"]:
            if query in like["value"].lower():
                self.touch_like(
            like["value"]
        )
                results.append(
                {
                    "value": like["value"],
                    "importance": like["importance"]
                }
            )

        for dislike in profile["dislikes"]:
            if query in dislike["value"].lower():
                self.touch_dislike(
            dislike["value"]
        )

                results.append(
                {
                    "value": dislike["value"],
                    "importance": dislike["importance"]
                }
            )

        for fact in profile["facts"]:
            if query in fact["value"].lower():
                self.touch_fact(
            fact["value"]
        )

                results.append(
        {
            "value": fact["value"],
            "importance": fact["importance"]
        }
    )
        results.sort(
        key=lambda x: x["importance"],
        reverse=True
    )
        return results[:limit]
    def touch_fact(self, memory_value):
        self.collection.update_one(
        {
            "owner": self.user_id,
            "facts.value": memory_value
        },
        {
            "$set":
            {
                "facts.$.last_accessed":
                datetime.now().isoformat()
            }
        }
    )
    def touch_like(self, memory_value):
        self.collection.update_one(
        {
            "owner": self.user_id,
            "likes.value": memory_value
        },
        {
            "$set":
            {
                "likes.$.last_accessed":
                datetime.now().isoformat()
            }
        }
    )
    def touch_dislike(self, memory_value):
        self.collection.update_one(
        {
            "owner": self.user_id,
            "dislikes.value": memory_value
        },
        {
            "$set":
            {
                "dislikes.$.last_accessed":
                datetime.now().isoformat()
            }
        }
    )