import logging

from ultralytics import YOLO

import config

log = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.50


class ObjectDetectionService:
    def __init__(self):
        self.model = YOLO(str(config.YOLO_MODEL))

    def detect(self, frame):
        objects = set()
        for result in self.model(frame, verbose=False):
            for box in result.boxes:
                if float(box.conf[0]) >= MIN_CONFIDENCE:
                    objects.add(self.model.names[int(box.cls[0])])
        return list(objects)
