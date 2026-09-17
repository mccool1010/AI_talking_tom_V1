from datetime import datetime


class MemoryDecayService:

    def decay(self, profile):

        changed = False

        now = datetime.now()

        for category in [
            profile["likes"],
            profile["dislikes"],
            profile["facts"]
        ]:

            for memory in category:

                if "last_accessed" not in memory:
                    memory["last_accessed"] = (
        memory["learned_at"]
    )

                last_accessed = datetime.fromisoformat(
                    memory["last_accessed"]
                )

                days_unused = (
                    now - last_accessed
                ).days

                # Important memories decay slower
                if memory["importance"] >= 10:
                     if days_unused < 30:
                          continue
                     if memory["importance"] > 0:
                          memory["importance"] -= 1
                          changed = True

                     continue

                # Recently used memories stay fresh
                if days_unused < 7:
                    continue

                if memory["importance"] > 0:
                    memory["importance"] -= 1
                    changed = True

        return changed
    def remove_forgotten_memories(self, profile):
        profile["likes"] = [
        x for x in profile["likes"]
        if x["importance"] > 0
    ]
        profile["dislikes"] = [
        x for x in profile["dislikes"]
        if x["importance"] > 0
    ]
        profile["facts"] = [
        x for x in profile["facts"]
        if x["importance"] > 0
    ]
    def save_profile(self, profile, collection, user_id):
        collection.update_one(
            {"owner": user_id},
            {"$set": {c: profile[c] for c in ("likes", "dislikes", "facts")}},
        )

    def run_for_all(self, collection):
        """Decay every user's profile. Returns the number of profiles changed."""
        changed = 0
        for profile in collection.find({}):
            for category in ("likes", "dislikes", "facts"):
                profile.setdefault(category, [])
            before = sum(len(profile[c]) for c in ("likes", "dislikes", "facts"))
            modified = self.decay(profile)
            self.remove_forgotten_memories(profile)
            after = sum(len(profile[c]) for c in ("likes", "dislikes", "facts"))
            if modified or after != before:
                self.save_profile(profile, collection, profile["owner"])
                changed += 1
        return changed
