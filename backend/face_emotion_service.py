import logging
import threading
import time
from collections import Counter

import cv2
from deepface import DeepFace

from object_detection_service import ObjectDetectionService

log = logging.getLogger(__name__)

FRAME_INTERVAL = 0.2
MIN_FACE_CONFIDENCE = 0.80
HISTORY_SIZE = 100


def classify_frame(result, frame_shape):
    """
    Turn a DeepFace result into (person_present, people_count, emotion).
    DeepFace returns a full-frame region when it finds no face; that and
    low-confidence detections count as "no person".
    """
    region = result[0]["region"]
    fake = (region["x"] == 0 and region["y"] == 0
            and region["w"] >= frame_shape[1] - 5
            and region["h"] >= frame_shape[0] - 5)
    if fake or result[0]["face_confidence"] < MIN_FACE_CONFIDENCE:
        return False, 0, "neutral"
    return True, len(result), result[0]["dominant_emotion"]


class FaceEmotionService:
    """
    Owns the camera. A background thread reads frames, runs object detection
    and face-emotion analysis, and keeps the latest frame so the dashboard
    stream never reads the camera itself.
    """

    def __init__(self, environment, camera_index=0):
        self.environment = environment
        self.cap = cv2.VideoCapture(camera_index)
        self.emotion_history = []
        self.latest_emotion = None
        self.person_present = False
        self.people_count = 0
        self.running = False
        self.thread = None
        self._frame = None
        self._frame_lock = threading.Lock()
        self.object_detector = ObjectDetectionService()
        if not self.cap.isOpened():
            log.warning("Camera %s could not be opened; face emotion will stay neutral", camera_index)

    def get_emotion(self):
        return self.latest_emotion or "neutral"

    def person_detected(self):
        return self.person_present

    def get_people_count(self):
        return self.people_count

    def get_jpeg(self, quality=60):
        """Latest camera frame as JPEG bytes, or None."""
        with self._frame_lock:
            frame = self._frame
        if frame is None:
            return None
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buffer.tobytes() if ok else None

    def _set_absent(self):
        self.person_present = False
        self.people_count = 0
        self.environment.update_person(False, 0)

    def _camera_loop(self):
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                self._set_absent()
                self.latest_emotion = "neutral"
                time.sleep(FRAME_INTERVAL)
                continue

            with self._frame_lock:
                self._frame = frame

            try:
                self.environment.update_objects(self.object_detector.detect(frame))
                if self.environment.new_objects:
                    log.debug("New objects: %s", self.environment.new_objects)
                if self.environment.removed_objects:
                    log.debug("Removed objects: %s", self.environment.removed_objects)

                result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
                present, count, emotion = classify_frame(result, frame.shape)
                if present:
                    self.person_present = True
                    self.people_count = count
                    self.environment.update_person(True, count)
                else:
                    self._set_absent()
            except Exception:
                log.exception("Camera analysis failed")
                self._set_absent()
                self.latest_emotion = "neutral"
                time.sleep(FRAME_INTERVAL)
                continue

            self.emotion_history.append(emotion)
            self.emotion_history = self.emotion_history[-HISTORY_SIZE:]
            self.latest_emotion = Counter(self.emotion_history).most_common(1)[0][0]
            time.sleep(FRAME_INTERVAL)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._camera_loop, daemon=True, name="camera")
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.cap.release()
