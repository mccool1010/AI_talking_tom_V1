from faster_whisper import WhisperModel

print("Loading Whisper...")

model = WhisperModel(
    "base.en",
    device="cpu",
    compute_type="int8"
)

print("Whisper Ready")