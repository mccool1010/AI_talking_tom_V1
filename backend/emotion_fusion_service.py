
# emotion_fusion_service.py

class EmotionFusionService:

    def __init__(self):
        print("Loading Emotion Fusion Service...")
        print("Emotion Fusion Service Ready")

    def get_emotion(self, face_emotion, voice_emotion):

        if face_emotion == voice_emotion:
            return face_emotion

        if voice_emotion != "neutral":
            return voice_emotion

        return face_emotion