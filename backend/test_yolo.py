import cv2
from ultralytics import YOLO

print("Loading YOLO...")
model = YOLO("yolov8n.pt")
print("YOLO Ready!")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Failed to open camera.")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        break

    results = model(frame)

    detected_objects = set()

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            # Ignore weak detections
            if confidence < 0.50:
                continue

            label = model.names[class_id]
            detected_objects.add(label)

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{label} {confidence:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    print("Detected:", sorted(detected_objects), end="\r")

    cv2.imshow("YOLO Test", frame)

    key = cv2.waitKey(1)

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()