import logging
log = logging.getLogger(__name__)


def _debug(*args):
    log.debug(" ".join(str(a) for a in args))


class PersonalityEvolutionService:
    """
    Computes personality trait changes based on interaction signals.

    Called once per conversation turn. Returns small deltas (±0.5 to ±2)
    to ensure gradual evolution over many interactions.

    Evolution rules:
        confidence: grows with happy moods + high trust, shrinks with anger/low trust
        base_curiosity: grows with varied conversation, shrinks during long idle
        laziness: grows when sleepy for long periods, shrinks when energy stays high
        affection: grows with attachment + happiness, shrinks with repeated anger
        mood_stability: grows with consistent emotions, shrinks with volatility
    """

    def __init__(self):
        _debug("Loading Personality Evolution Service...")
        self._conversation_count = 0
        _debug("Personality Evolution Service Ready")

    def evolve(self, mood, relationship, emotion_history, needs):
        """
        Compute trait deltas based on current interaction signals.

        Args:
            mood: Current mood string (happy, sad, angry, neutral, etc.)
            relationship: dict with trust, friendship, attachment values
            emotion_history: list of recent emotion strings
            needs: dict with hunger, sleepiness, social_need values

        Returns:
            dict of {trait_name: delta} values. Zero deltas are omitted.
        """
        self._conversation_count += 1
        deltas = {}

        trust = relationship.get("trust", 50)
        attachment = relationship.get("attachment", 50)
        sleepiness = needs.get("sleepiness", 0)

        # --- Confidence ---
        # Grows in positive, trusting interactions
        confidence_delta = 0
        if mood == "happy" and trust > 60:
            confidence_delta += 0.5
        if mood == "angry":
            confidence_delta -= 0.5
        if trust < 30:
            confidence_delta -= 0.5
        if confidence_delta != 0:
            deltas["confidence"] = confidence_delta

        # --- Base Curiosity ---
        # Grows with engagement, shrinks with disengagement
        curiosity_delta = 0
        if self._conversation_count % 5 == 0:
            # Every 5th conversation, curiosity gets a small bump
            # (sustained engagement feeds curiosity)
            curiosity_delta += 0.5
        if mood == "neutral" and len(emotion_history) > 5:
            # Long stretches of neutral = less curiosity
            recent = emotion_history[-5:]
            if all(e == "neutral" for e in recent):
                curiosity_delta -= 0.5
        if curiosity_delta != 0:
            deltas["base_curiosity"] = curiosity_delta

        # --- Laziness ---
        # Grows when tired a lot, shrinks when energetic
        laziness_delta = 0
        if sleepiness > 70:
            laziness_delta += 0.5
        if sleepiness < 20:
            laziness_delta -= 0.5
        if laziness_delta != 0:
            deltas["laziness"] = laziness_delta

        # --- Affection ---
        # Grows with positive, attached interactions
        affection_delta = 0
        if attachment > 70 and mood == "happy":
            affection_delta += 1.0
        if mood == "angry":
            affection_delta -= 0.5
        if mood == "sad" and attachment > 50:
            # Empathy builds affection slightly
            affection_delta += 0.5
        if affection_delta != 0:
            deltas["affection"] = affection_delta

        # --- Mood Stability ---
        # Grows with consistent emotions, shrinks with volatility
        stability_delta = 0
        if len(emotion_history) >= 5:
            recent = emotion_history[-5:]
            unique_emotions = len(set(recent))
            if unique_emotions <= 2:
                # Consistent emotions
                stability_delta += 0.5
            elif unique_emotions >= 4:
                # Very volatile
                stability_delta -= 1.0
        if stability_delta != 0:
            deltas["mood_stability"] = stability_delta

        return deltas
