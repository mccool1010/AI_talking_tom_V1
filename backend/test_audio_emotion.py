from stt_service import STTService
from voice_emotion_service import VoiceEmotionService

stt = STTService()
voice = VoiceEmotionService()

text, audio = stt.listen()

emotion = voice.get_emotion(audio)

print("Text:", text)
print("Emotion:", emotion)