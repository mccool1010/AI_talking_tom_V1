import cv2
from deepface import DeepFace
from collections import Counter

cap = cv2.VideoCapture(0)

emotion_history = []
last_emotion = None
while True :
    ret, frame = cap.read()
    if not ret :
        break
    try :
        result = DeepFace.analyze(frame,actions=["emotion"],enforce_detection = False)
        emotion = result[0]["dominant_emotion"]
        emotion_history.append(emotion)
        emotion_history = emotion_history[-100:]#keep  the last latest emotions
        counts = Counter(emotion_history)
        stable_emotion = counts.most_common(1)[0][0]
        cv2.putText(
    frame,
    f"Emotion: {stable_emotion}",
    (20, 40),
    cv2.FONT_HERSHEY_SIMPLEX,
    1,
    (0, 255, 0),
    2
)# this lis lines shows the emotion on the camera window  itself 
        
        # counts the emotions encountered and 
        # the return the dominant with 
        # most highest number  and takes the first element from the first tuple within the list basically 
        # mostt_common gives the tuple with the highest count in the dictonary into a list
        #then by counts.most_common(1)[0] chooses the tuple from the list
        #thenn by counts.most_common(1)[0][0] the first element from the tuple chosen

        if stable_emotion != last_emotion:
             print("Current Emotion:", stable_emotion)
             last_emotion = stable_emotion
    except Exception as e:
        print("Error :" , e)
    cv2.imshow("Emotion Test", frame)# label at the window to show the camera 
    if cv2.waitKey(1) & 0xFF ==ord("q"): #waits every one second for the key   and  if we press q it matches with the ordinal value
            break#and break the loop and drops the feed 
cap.release()
cv2.destroyAllWindows()


