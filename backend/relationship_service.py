import logging
import config
import db


log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


class RelationshipService:

    DEFAULTS = {"trust": 50, "friendship": 50, "attachment": 50}

    def __init__(self, user_context=None):
        self.collection = db.get_db()["relationship"]
        self.switch_user(user_context.get_user_id() if user_context else config.DEFAULT_USER_ID)

    def switch_user(self, user_id):
        self.user_id = user_id
        doc = self.collection.find_one({"tom_id": user_id})
        if not doc:
            doc = {"tom_id": user_id, **self.DEFAULTS}
            self.collection.insert_one(dict(doc))
        for key, default in self.DEFAULTS.items():
            setattr(self, key, doc.get(key, default))

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
        _debug(
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
            _debug(
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
         _debug(
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
       