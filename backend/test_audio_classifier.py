from transformers import pipeline

classifier = pipeline(
    task="audio-classification",
    model="superb/wav2vec2-base-superb-er"
)

result = classifier("recording.wav")

print(result)