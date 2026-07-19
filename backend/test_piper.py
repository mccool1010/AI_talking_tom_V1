import subprocess

text = "Hello, I am Talking Tom"

subprocess.run(
    [
        "C:/tom/AI-Talking-Tom/piper/piper.exe",
        "--model",
        "C:/tom/AI-Talking-Tom/models/tts/en_US-lessac-medium.onnx",
        "--output_file",
        "output.wav"
    ],
    input=text,
    text=True
)

print("Done")