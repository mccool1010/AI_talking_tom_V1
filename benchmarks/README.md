# Benchmarks

These scripts produce the numbers in the main README's [Performance & Evaluation](../README.md#performance--evaluation) section. They load the real models and backend services, use a separate MongoDB database (`talking_tom_bench`, which is dropped before and after each run), and never touch your own data, webcam or speakers.

| Script | Measures | Output | Time |
|---|---|---|---|
| [`bench_pipeline.py`](bench_pipeline.py) | End-to-end latency, time per stage, LLM tokens/s, peak RAM | [`results/pipeline.json`](results/pipeline.json) | ~8 min |
| [`bench_emotion.py`](bench_emotion.py) | Face, voice and fusion emotion accuracy on RAVDESS | [`results/emotion.json`](results/emotion.json) | ~25 min (240 clips) |
| [`bench_memory.py`](bench_memory.py) | Memory extraction, retention, retrieval hit rate, forgetting | [`results/memory.json`](results/memory.json) | ~1 min |

Helper scripts:

| Script | Purpose |
|---|---|
| [`make_inputs.ps1`](make_inputs.ps1) | Generates the 12 spoken test phrases (Windows voices, 16 kHz WAV + transcript) |
| [`download_ravdess.py`](download_ravdess.py) | Downloads RAVDESS actors 01–04 (~2.2 GB) and checks every clip against the official Zenodo release |
| [`common.py`](common.py) | Shared paths, scratch database and timing helpers |

The committed files in [`results/`](results/) come from the runs reported in the main README. [`results/emotion_clips.jsonl`](results/emotion_clips.jsonl) holds the per-clip face label and voice scores, so `bench_emotion.py` can recompute the metrics (for example with a different `TOM_VOICE_MIN_CONFIDENCE`) without re-running the models. Delete it to measure from scratch.

## Running

From the repository root, with the virtual environment active, MongoDB running and the models installed (see the main README):

```bash
# 1. Test data (saved under benchmarks/data/, which git ignores)
powershell -ExecutionPolicy Bypass -File benchmarks\make_inputs.ps1
python benchmarks\download_ravdess.py

# 2. Benchmarks (close the app first; it competes for CPU)
python benchmarks\bench_pipeline.py     # --turns N for a quicker run
python benchmarks\bench_memory.py
python benchmarks\bench_emotion.py      # --limit N for a quick check; needs ffmpeg on PATH
```

Each script prints a progress bar and a summary, and saves its JSON to `benchmarks/results/`.

## Method

**Pipeline.** Each test phrase goes through the same steps as `TomApp.process_conversation_turn`: Whisper speech-to-text, memory retrieval, voice emotion, the Qwen reply and Piper synthesis. Audio is not played.
- *End-to-end latency* is the end-of-turn silence the app waits for (`TOM_STT_SILENCE_SECONDS`), plus all processing up to Tom's first audio sample.
- The turns run twice: once without and once with the camera thread (face emotion and YOLO) running in the background. The camera thread reads a looped RAVDESS clip instead of the webcam.
- *LLM tokens/s* is measured separately, from 5 streamed 128-token generations.
- *Peak RAM* is the peak working set of the benchmark process, which loads every model the app loads. Piper's peak is measured separately.

**Emotion.** The test set is 240 RAVDESS audio-visual speech clips from 4 actors (2 male, 2 female).
- The face result comes from the app's DeepFace logic: one frame every 0.2 s, then a majority vote.
- The voice result is the wav2vec2 label, used only at the configured confidence or higher.
- Fusion is `EmotionFusionService`.
- The main score covers the 112 clips labelled neutral, happy, sad or angry, the emotions the voice model can output. All 240 clips are also reported, with "calm" counted as neutral.
- The fusion rule and the 0.70 confidence cutoff were chosen on this same set, so the scores are optimistic.

**Memory.** 30 labelled statements (9 likes, 7 dislikes, 14 facts) go through the real extraction model into a profile.
- *Retained*: the statement's keyword is stored in the profile.
- *Hit rate*: the matching memory is among the top 3 results of `ProfileMemoryService.retrieve()` for a follow-up question.
- *Unrelated questions*: 10 questions that should retrieve nothing.
- *Forgetting*: simulated daily decay runs until an unused memory is removed.
