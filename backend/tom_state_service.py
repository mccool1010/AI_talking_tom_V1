from pymongo import MongoClient

class TomStateService:

    def __init__(self, user_context=None):

        print("Loading Tom State Service...")
        self.user_id = user_context.get_user_id() if user_context else "default"
        self.client = MongoClient(
    "mongodb://localhost:27017/"
)
        self.db = self.client["talking_tom"]
        self.collection = self.db["state"]
        doc = self.collection.find_one({
            "tom_id" : self.user_id

        })
        if doc :
            self.energy = doc["energy"]
            self.friendliness = doc["friendliness"]
            self.curiosity = doc["curiosity"]
            print("Tom State Loaded")
        else:
            self.collection.insert_one(
        {
            "tom_id": self.user_id,

            "energy": 100,

            "friendliness": 50,

            "curiosity": 50
        }
    )
            self.energy = 100
            self.friendliness = 50
            self.curiosity = 50
            print("New Tom State Created")
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
        print("Energy:", self.energy)
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
        print("Friendliness:",self.friendliness)
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
        print("Curiosity:",self.curiosity)
    def update_from_conversation(self, mood, personality=None):
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