import torch
from transformers import pipeline

print("CUDA Available:", torch.cuda.is_available())

classifier = pipeline(
    task="audio-classification",
    model="superb/wav2vec2-base-superb-er"
)

print("Pipeline Loaded")