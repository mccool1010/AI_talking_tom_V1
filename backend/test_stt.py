import queue #(to store the audio chunks cntinuosly in a fifo)
import sounddevice as sd #(it is use to use the microphone to take the audio as input device basically lieke opencv where the data from the camera is take as input as frames but in this case its just the data as audio chunks for processing  which later stored in que as an audio buffer  )
from vosk import Model , KaldiRecognizer #model to recognise the vocabukary and acoustic data  then we have KaldiRecognizer to to convert audio chunks (data) to text data
 
audio_queue = queue.Queue() # intialize the audio buffer to store audio chunks
model = Model("models/vosk/vosk-model-small-en-us-0.15")#loading the speech recognition model The model contains:vocabulary acoustic patterns recognition logic

#now for the recognizer  since model its isnt the recognizer it has the knowledge or lets say the data to recognize speech
recognizer = KaldiRecognizer(model,16000) # this the recognizer object for the KaldiRecognizer  function uses the model for the knowledge and cantake 16,000 audio samples per second that is its basically the sample rate in Hz
print("Vosk model loaded successfully!")

#now we create a callback function
#A callback is:

#a function automatically called by another system

#In this case:sounddevice calls this function
#every time microphone audio arrives 
#The audio system calls it automatically.
#basically audio recieved as input by sounddevice it calls 
#this function automatically 

def audio_callback(indata, frames, time, status):
    if status:
        print(status)  
# status is used to check for any kind of microphone errors overflow warning or evening streaming issues in the microphone or the system itself 
    audio_queue.put(bytes(indata)) #takes incoming microphone audio and stores it inside the queue

#indata: Raw audio chunk from microphone.
#bytes(indata): Converts NumPy audio buffer into raw bytes.
#               Vosk expects: byte audio data NOT NumPy arrays.
#audio_queue.put(...): Adds audio chunk into queue.

print("Starting microphone stream...")
with sd.RawInputStream(samplerate=16000, blocksize=8000,dtype="int16",channels=1,callback=audio_callback):
        
    # with is basically used as a context manager files, audio video streams, data from databases connections , any kinda of resources basiacllly its a loop that opens automatically and closes safely 
    # 16000 now audio chunks  per second 
    #blocksize is 8000 size of an audio chunk stored in queue 
    # dtype int16 : 16-bit signed integer audio format common for microphine input 
    #channel = 1 , mono input basiaclly says u have only one microphne to use for input
    # to connect the microphone stream to the audio callback function to store the audio  chunk in the queue that parameneter 
    #     callback=audio_callback is used  
    #now same with opencv we need a continuus listening loop so 
         print("listening.........")
         while True:
             data = audio_queue.get()# to take the oldest audio chuck in the queue
             #also this blocks execution ontil audio chuck exist in the queue basically waitsfor input from microphone , bloacks until audio is available 
             if recognizer.AcceptWaveform(data):#AcceptWaveform():feeds audio into Vosk checks if a complete phrase was detected
                 #True → speech phrase complete ie  if the person has finished speaking 
                 #False → still listening
                 result = recognizer.Result()# it gets the final recognized speech to text  that too in json format
                 #{"text":"hello tom"}
                 print(result)




              