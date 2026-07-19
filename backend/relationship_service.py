from pymongo import MongoClient


class RelationshipService:

    def __init__(self, user_context=None):

        print("Loading Relationship Service...")

        self.user_id = user_context.get_user_id() if user_context else "default"

        self.client = MongoClient(
            "mongodb://localhost:27017/"
        )

        self.db = self.client["talking_tom"]

        self.collection = self.db["relationship"]

        doc = self.collection.find_one(
            {
                "tom_id": self.user_id
            }
        )

        if doc:

            self.trust = doc["trust"]
            self.friendship = doc["friendship"]
            self.attachment = doc["attachment"]

            print("Relationship Loaded")

        else:

            self.collection.insert_one(
                {
                    "tom_id": self.user_id,

                    "trust": 50,
                    "friendship": 50,
                    "attachment": 50
                }
            )

            self.trust = 50
            self.friendship = 50
            self.attachment = 50

            print("New Relationship Created")
    def update_trust(self, amount):
        self.trust += amount
        self.trust = max(
        0,
        min(100, self.trust)
    )
        self.collection.update_one(
        {
            "tom_id": self.user_id
        },
        {
            "$set":
            {
                "trust": self.trust
            }
        }
    )
        print(
        "Trust:",
        self.trust
    )
    def update_friendship(self, amount):
            self.friendship += amount
            self.friendship = max(
        0,
        min(100, self.friendship)
    )
            self.collection.update_one(
        {
            "tom_id": self.user_id
        },
        {
            "$set":
            {
                "friendship": self.friendship
            }
        }
    )
            print(
        "Friendship:",
        self.friendship
    )
    def update_attachment(self, amount):
         self.attachment += amount
         
         self.attachment = max(
        0,
        min(100, self.attachment)
    )
         self.collection.update_one(
        {
            "tom_id": self.user_id
        },
        {
            "$set":
            {
                "attachment": self.attachment
            }
        }
    )
         print(
        "Attachment:",
        self.attachment
    )
    def update_from_conversation(self, mood): 
        self.update_attachment(+1)
        if mood == "happy":
            self.update_friendship(+1)
            self.update_trust(+1)
        elif mood == "sad":
            self.update_attachment(+1)
        elif mood == "angry":
            self.update_trust(-1)
       