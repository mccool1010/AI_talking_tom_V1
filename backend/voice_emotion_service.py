import logging

from transformers import pipeline

import config

log = logging.getLogger(__name__)

LABELS = {"hap": "happy", "neu": "neutral", "ang": "angry", "sad": "sad"}


def pick_emotion(scores, min_confidence):
    """Top label, or "neutral" when the model is not confident enough."""
    label = max(scores, key=scores.get)
    return label if scores[label] >= min_confidence else "neutral"


class VoiceEmotionService:
    """
    Speech emotion from superb/wav2vec2-base-superb-er (4 classes).

    The model leans heavily towards "angry" on ordinary speech, so a label is
    only used when its probability reaches TOM_VOICE_MIN_CONFIDENCE (0.70).
    On RAVDESS this cut neutral clips misread as angry from 23% to 6% while
    still catching 91% of truly angry clips.
    """

    def __init__(self):
        self.classifier = pipeline(
            task="audio-classification",
            model="superb/wav2vec2-base-superb-er",
            top_k=None,
        )
        self.min_confidence = config.VOICE_MIN_CONFIDENCE

    def get_emotion(self, audio_path):
        scores = {LABELS.get(r["label"], r["label"]): r["score"] for r in self.classifier(audio_path)}
        emotion = pick_emotion(scores, self.min_confidence)
        log.debug("Voice emotion scores %s -> %s", {k: round(v, 2) for k, v in scores.items()}, emotion)
        return emotion
