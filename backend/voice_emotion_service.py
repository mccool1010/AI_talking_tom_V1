from transformers import pipeline

class VoiceEmotionService:

    def __init__(self):

        print("Loading Voice Emotion Service...")

        self.classifier = pipeline(
            task="audio-classification",
            model="superb/wav2vec2-base-superb-er"
        )

        print("Voice Emotion Service Ready")

    def get_emotion(self, audio_path):

        result = self.classifier(audio_path)

        emotion = result[0]["label"]

        mapping = {
            "hap": "happy",
            "neu": "neutral",
            "ang": "angry",
            "sad": "sad"
        }

        return mapping.get(emotion, "neutral")