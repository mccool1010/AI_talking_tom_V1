from ultralytics import YOLO

class ObjectDetectionService:

    def __init__(self):

        print("Loading YOLO...")

        self.model = YOLO("yolov8n.pt")

        print("YOLO Ready")

    def detect(self, frame):

        results = self.model(frame)

        objects = []

        for result in results:

            for box in result.boxes:

                confidence = float(box.conf[0])

                if confidence < 0.50:
                    continue

                class_id = int(box.cls[0])

                label = self.model.names[class_id]

                objects.append(label)

        return list(set(objects))