import cv2
from deepface import DeepFace
from collections import Counter
import threading
import time
from object_detection_service import ObjectDetectionService
class FaceEmotionService:
    def __init__(self,environment):
        print("loading face emotion service.......")
        self.environment = environment
        self.cap = cv2.VideoCapture(0)
        self.emotion_history = []
        self.latest_emotion = None
        self.running = False
        self.thread = None
        self.person_present = False
        self.people_count = 0
        self.object_detector = ObjectDetectionService()
        print("Face emotion service ready")
    def get_emotion(self):
        if self.latest_emotion is None:
            return "neutral"

        return self.latest_emotion
   
    def person_detected(self):
        return self.person_present
   
    def get_people_count(self):
        return self.people_count
    def _camera_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.person_present = False
                self.people_count = 0
                self.environment.update_person(False, 0)
                self.latest_emotion = "neutral"
                
                time.sleep(0.2)
                continue
            objects = self.object_detector.detect(frame)
            self.environment.update_objects(objects)
            if self.environment.new_objects:
                print("New:", self.environment.new_objects)
            if self.environment.removed_objects:
                print("Removed:", self.environment.removed_objects)

            try:
                result = DeepFace.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False
            )
                region = result[0]["region"] 
                confidence = result[0]["face_confidence"]

                

                fake_detection = (
    region["x"] == 0 and
    region["y"] == 0 and
    region["w"] >= frame.shape[1] - 5 and
    region["h"] >= frame.shape[0] - 5
)

                if fake_detection or confidence < 0.80:
                    self.person_present = False
                    self.people_count = 0
                    self.environment.update_person(False, 0)
                    emotion = "neutral"
                else:
                    self.person_present = True
                    self.people_count = len(result)
                    self.environment.update_person(
    True,
    len(result)
)
                    emotion = result[0]["dominant_emotion"]
            except Exception as e:
                print("Camera thread:", e)
                self.person_present = False
                self.people_count = 0
                self.latest_emotion = "neutral"
                time.sleep(0.2)
                continue
                
                

            self.emotion_history.append(emotion)
            self.emotion_history = self.emotion_history[-100:]

            counts = Counter(self.emotion_history)

            self.latest_emotion = counts.most_common(1)[0][0]

            time.sleep(0.2)
    def start(self):
        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
        target=self._camera_loop,
        daemon=True
    )

        self.thread.start()


    def stop(self):
        self.running = False

        if self.thread:
            self.thread.join()

        self.cap.release()