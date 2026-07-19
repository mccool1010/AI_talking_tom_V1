from pymongo import MongoClient


class NeedsService:

    def __init__(self, user_context=None):

        print("Loading Needs Service...")

        self.user_id = user_context.get_user_id() if user_context else "default"

        self.client = MongoClient(
            "mongodb://localhost:27017/"
        )

        self.db = self.client["talking_tom"]

        self.collection = self.db["needs"]

        doc = self.collection.find_one(
            {
                "tom_id": self.user_id
            }
        )

        if doc:

            self.hunger = doc["hunger"]
            self.sleepiness = doc["sleepiness"]
            self.social_need = doc["social_need"]

            print("Needs Loaded")

        else:

            self.collection.insert_one(
                {
                    "tom_id": self.user_id,

                    "hunger": 0,
                    "sleepiness": 0,
                    "social_need": 50
                }
            )

            self.hunger = 0
            self.sleepiness = 0
            self.social_need = 50

            print("New Needs Created")
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

        print("Hunger:",self.hunger)
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

        print("Sleepiness:",self.sleepiness)
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

        print("Social Need:",self.social_need )
    def update_from_conversation(self, personality=None):
        if personality is None:
            personality = {"laziness": 30, "affection": 50}
        self.update_hunger(+1)
        # Lazier Tom gets sleepier faster
        sleepiness_gain = 1 + (personality["laziness"] // 50)
        self.update_sleepiness(sleepiness_gain)
        # Affectionate Tom craves more social interaction
        social_drain = -1 if personality["affection"] < 50 else -2
        self.update_social_need(social_drain)