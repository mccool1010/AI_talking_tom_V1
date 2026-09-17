import logging
import re
from datetime import datetime
from difflib import SequenceMatcher

import config
import db

log = logging.getLogger(__name__)

CATEGORIES = ("likes", "dislikes", "facts")
DEFAULT_IMPORTANCE = 5
DUPLICATE_SIMILARITY = 0.88

# Words that carry no topic on their own. Matching on them made almost every
# utterance retrieve unrelated memories ("a", "i", "is", "time", ...).
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing don down during each even ever every
few for from further get gets getting go goes going gone good got had has have having he her
here hers herself him himself his how i if in into is it its itself just know let like liked
likes love loved loves me more most much my myself need no nor not now of off on once only or
other our ours ourselves out over own really same say she should so some such than that the
their theirs them themselves then there these they this those through time to today tomorrow
too under until up us very want wants was way we well were what when where which while who
whom why will with would yeah yes yesterday you your yours yourself yourselves tom hey hi hello
okay ok im ive dont cant thats whats remember think thought feel maybe guess tell please
thing things something anything
""".split())

_WORD = re.compile(r"[a-z0-9]+")


def _stem(word):
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def keywords(text):
    """Content-word stems of `text` (lowercase, stopwords removed)."""
    return {_stem(w) for w in _WORD.findall(text.lower().replace("'", "")) if w not in STOPWORDS}


def normalize(text):
    return " ".join(_WORD.findall(text.lower()))


def is_duplicate(a, b):
    na, nb = normalize(a), normalize(b)
    return na == nb or SequenceMatcher(None, na, nb).ratio() >= DUPLICATE_SIMILARITY


def _now():
    return datetime.now().isoformat()


class ProfileMemoryService:
    def __init__(self, user_context=None):
        self.collection = db.get_db()["profile_memory"]
        self.user_id = user_context.get_user_id() if user_context else config.DEFAULT_USER_ID
        self.switch_user(self.user_id)

    def switch_user(self, user_id):
        self.user_id = user_id
        if not self.collection.find_one({"owner": user_id}):
            self.collection.insert_one({"owner": user_id, "likes": [], "dislikes": [], "facts": []})
            log.info("Created memory profile for %s", user_id)

    # ---- writes ----

    def _add(self, category, value, importance=DEFAULT_IMPORTANCE):
        value = (value or "").strip()
        if not value:
            return
        profile = self.get_profile()
        for existing in profile.get(category, []):
            if is_duplicate(existing["value"], value):
                self.collection.update_one(
                    {"owner": self.user_id, f"{category}.value": existing["value"]},
                    {"$inc": {f"{category}.$.importance": 1},
                     "$set": {f"{category}.$.last_accessed": _now()}},
                )
                log.info("Reinforced %s: %s", category, existing["value"])
                return
        now = _now()
        self.collection.update_one(
            {"owner": self.user_id},
            {"$push": {category: {"value": value, "learned_at": now,
                                  "last_accessed": now, "importance": importance}}},
        )
        log.info("Saved %s: %s", category, value)

    def add_like(self, item):
        self._add("likes", item)

    def add_dislike(self, item):
        self._add("dislikes", item)

    def add_fact(self, fact, importance=DEFAULT_IMPORTANCE):
        self._add("facts", fact, importance)

    def _touch(self, category, value):
        self.collection.update_one(
            {"owner": self.user_id, f"{category}.value": value},
            {"$set": {f"{category}.$.last_accessed": _now()}},
        )

    def touch_like(self, value):
        self._touch("likes", value)

    def touch_dislike(self, value):
        self._touch("dislikes", value)

    def touch_fact(self, value):
        self._touch("facts", value)

    # ---- reads ----

    def get_profile(self):
        doc = self.collection.find_one({"owner": self.user_id}) or {}
        return {"owner": self.user_id, **{c: doc.get(c, []) for c in CATEGORIES}}

    def _values(self, category):
        return [m["value"] for m in self.get_profile()[category]]

    def get_likes(self):
        return self._values("likes")

    def get_dislikes(self):
        return self._values("dislikes")

    def get_facts(self):
        return self._values("facts")

    def _recent(self, category, limit):
        return sorted(self.get_profile()[category], key=lambda x: x["learned_at"], reverse=True)[:limit]

    def get_recent_likes(self, limit=5):
        return self._recent("likes", limit)

    def get_recent_dislikes(self, limit=5):
        return self._recent("dislikes", limit)

    def get_recent_facts(self, limit=5):
        return self._recent("facts", limit)

    def get_important_facts(self):
        return [f["value"] for f in self.get_profile()["facts"] if f["importance"] >= 7]

    def _scored(self, text):
        query = keywords(text)
        if not query:
            return []
        scored = []
        for category in CATEGORIES:
            for memory in self.get_profile()[category]:
                overlap = len(query & keywords(memory["value"]))
                if overlap:
                    scored.append((overlap, memory["importance"], category, memory))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return scored

    def search_memories(self, query):
        return [m["value"] for _, _, _, m in self._scored(query)]

    def retrieve(self, text, limit=3):
        """
        Memories relevant to an utterance, best first: ranked by how many
        content words they share with it, then by importance. Only the
        returned memories are marked as accessed (this slows their decay).
        """
        results = []
        for _, _, category, memory in self._scored(text)[:limit]:
            self._touch(category, memory["value"])
            results.append({"value": memory["value"], "importance": memory["importance"],
                            "category": category})
        return results

    def get_top_memories(self, query, limit=3):
        """Backward-compatible alias for retrieve()."""
        return self.retrieve(query, limit)
