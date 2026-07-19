class RelationshipPromptService:

    def build(
        self,
        trust,
        friendship,
        attachment,
        user_name="Hari"
    ):

        context = []

        # Trust

        if trust >= 80:
            context.append(
                f"You trust {user_name} deeply."
            )

        elif trust >= 50:
            context.append(
                f"You generally trust {user_name}."
            )

        else:
            context.append(
                f"You are still learning to trust {user_name}."
            )

        # Friendship

        if friendship >= 80:
            context.append(
                f"{user_name} is one of your closest friends."
            )

        elif friendship >= 50:
            context.append(
                f"You consider {user_name} a friend."
            )

        else:
            context.append(
                f"You are only somewhat friendly with {user_name}."
            )

        # Attachment

        if attachment >= 80:
            context.append(
                f"You feel emotionally attached to {user_name}."
            )

        elif attachment >= 50:
            context.append(
                f"You enjoy spending time with {user_name}."
            )

        else:
            context.append(
                f"You are not strongly attached to {user_name} yet."
            )

        return "\n".join(context)