from face_emotion_service import FaceEmotionService

face = FaceEmotionService()

last_emotion = None

while True:

    emotion = face.get_emotion()

    if emotion != last_emotion:

        print("Current Emotion:", emotion)

        last_emotion = emotion