class PersonalityBalancingService:
    """
    Prevents extreme personality drift by applying soft constraints.

    Called after evolution to ensure traits remain in a healthy,
    coherent range. Does not force traits to specific values —
    it applies gentle nudges to prevent degenerate states.

    Rules:
        1. Soft clamp: traits at 0 or 100 nudge back toward center
        2. Anti-correlation: conflicting traits cannot both be extreme
        3. Stability floor: mood_stability cannot drop below 20
        4. Sum balance: prevents "maxed out everything" personality
    """

    def __init__(self):
        print("Loading Personality Balancing Service...")
        print("Personality Balancing Service Ready")

    def balance(self, traits):
        """
        Apply balancing rules to a traits dictionary.

        Args:
            traits: dict of {trait_name: value}

        Returns:
            dict of {trait_name: adjusted_value}
        """
        adjusted = dict(traits)

        # Rule 1: Soft clamp — nudge extremes back toward center
        for name, value in adjusted.items():
            if value >= 100:
                adjusted[name] = 99
            elif value <= 0:
                adjusted[name] = 1

        # Rule 2: Anti-correlation — laziness and curiosity conflict
        if adjusted["laziness"] > 80 and adjusted["base_curiosity"] > 80:
            adjusted["laziness"] = min(adjusted["laziness"], 75)
            adjusted["base_curiosity"] = min(
                adjusted["base_curiosity"], 75
            )
            print(
                "[Personality Balance] Laziness/curiosity conflict "
                "— both capped at 75"
            )

        # Rule 3: Stability floor
        if adjusted["mood_stability"] < 20:
            adjusted["mood_stability"] = 20

        # Rule 4: Sum balance — prevent maxed-out personality
        total = sum(adjusted.values())
        max_total = 400  # out of theoretical 500

        if total > max_total:
            # Find the highest trait and reduce it
            highest = max(adjusted, key=adjusted.get)
            overshoot = total - max_total
            reduction = min(overshoot, adjusted[highest] - 50)
            if reduction > 0:
                adjusted[highest] -= reduction
                print(
                    f"[Personality Balance] Sum exceeded {max_total} "
                    f"— reduced {highest} by {reduction:.1f}"
                )

        return adjusted
