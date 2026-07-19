class InternalThoughtService:

    def generate(
        self,
        energy,
        hunger,
        sleepiness,
        social_need,
        relationship,
        memories,
        user_name="Hari"
    ):

        thoughts = []

        # Needs
        if hunger > 70:
            thoughts.append(
                "I'm getting hungry."
            )

        if sleepiness > 70:
            thoughts.append(
                "I'm feeling sleepy."
            )

        if social_need > 70:
            thoughts.append(
                f"I want to spend time with {user_name}."
            )

        # Relationship
        if relationship["trust"] > 80:
            thoughts.append(
                f"I really trust {user_name}."
            )

        if relationship["attachment"] > 80:
            thoughts.append(
                f"I enjoy being around {user_name}."
            )

        # Memories
        if memories:

            thoughts.append(
                f"I'm thinking about {memories[0]}."
            )

        # Mood
        if energy < 30:
            thoughts.append(
                "I'm feeling tired."
            )

        return thoughts