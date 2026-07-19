import random


class IdleBehaviorService:

    def __init__(self):

        print("Loading Idle Behavior Service...")
        
        self.last_action = None

        print("Idle Behavior Service Ready")

    def get_action(
        self,
        energy,
        sleepiness,
        hunger,
        social_need,
        curiosity,
        personality=None
    ):
        if personality is None:
            personality = {"confidence": 50, "base_curiosity": 50, "laziness": 30, "affection": 50}

        actions = [ "blink",
    "blink",
    "blink",
    "blink"]

        if sleepiness > 70:
            actions.extend([
                "yawn",
                "sleep"
            ])

        if hunger > 70:
            actions.append("look_for_food")

        if curiosity > 70:
            actions.extend([
                "look_left",
                "look_right",
                "look_around"
            ])

        if social_need > 70:
            actions.append("look_at_user")

        if energy > 70:
            actions.extend([
                "stretch",
                "scratch"
            ])

        # Personality-driven action weighting
        if personality["confidence"] > 70:
            actions.extend(["stretch", "look_at_user"])

        if personality["laziness"] > 60:
            actions.extend(["yawn", "sleep"])

        if personality["base_curiosity"] > 60:
            actions.extend(["look_left", "look_right", "look_around"])

        if personality["affection"] > 60:
            actions.extend(["look_at_user", "look_at_user"])

        actions.append("blink")

        action = random.choice(actions)
        while action == self.last_action and len(set(actions)) > 1:
            action = random.choice(actions)

        self.last_action = action

        return action