"""
Latency, LLM speed and RAM of the full conversation pipeline.

Loads every model the way backend/main.py does, then replays the spoken test
phrases (benchmarks/data/inputs, see make_inputs.ps1) through the same steps
as TomApp.process_conversation_turn: speech-to-text, memory retrieval, voice
emotion, LLM reply and Piper synthesis. Audio is not played.

End-to-end latency = end-of-turn silence the app waits for + all processing
until Tom's first audio sample is ready.

The turns run twice: without and with the camera thread (face emotion + YOLO)
running in the background, fed from a looped RAVDESS clip instead of the
webcam. The second pass is skipped if RAVDESS is not downloaded.

Usage: python benchmarks/bench_pipeline.py [--turns N]
"""
import argparse
import json
import sys
import re
import shutil
import statistics
import subprocess
import time

import cv2
import numpy as np
import psutil
import soundfile as sf

from common import INPUTS_DIR, RAVDESS_DIR, RESULTS_DIR, Timer, drop_bench_db, peak_mb, progress, rss_mb

CAMERA_CLIP = RAVDESS_DIR / "Actor_01" / "01-01-03-01-01-01-01.mp4"


class LoopedVideo:
    """Stands in for cv2.VideoCapture(0) so no webcam is needed."""

    def __init__(self, *_):
        self.cap = _RealCapture(str(CAMERA_CLIP))

    def isOpened(self):
        return self.cap.isOpened()

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        return ok, frame

    def release(self):
        self.cap.release()


_RealCapture = cv2.VideoCapture
cv2.VideoCapture = LoopedVideo


def word_errors(ref, hyp):
    r = re.findall(r"[a-z']+", ref.lower())
    h = re.findall(r"[a-z']+", hyp.lower())
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
    return d[len(h)], len(r)


def summarize(values):
    ordered = sorted(values)
    return {"mean": statistics.mean(values), "median": statistics.median(values),
            "p90": ordered[int(0.9 * (len(ordered) - 1))], "min": ordered[0], "max": ordered[-1]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=12)
    args = parser.parse_args()

    wavs = sorted(INPUTS_DIR.glob("*.wav"))[: args.turns]
    if not wavs:
        raise SystemExit("No test phrases found. Run: powershell -File benchmarks\\make_inputs.ps1")

    import config
    import llm_provider
    import stt_service
    from emotion_fusion_service import EmotionFusionService
    from environment_service import EnvironmentService
    from face_emotion_service import FaceEmotionService
    from interaction_state import InteractionState
    from internal_thought_service import InternalThoughtService
    from llm_service import LLMService
    from memory_extraction_service import MemoryExtractionService
    from profile_memory_service import ProfileMemoryService
    from tts_service import TTSService
    from user_context_service import UserContextService
    from voice_emotion_service import VoiceEmotionService

    drop_bench_db()
    memory = {"baseline": rss_mb()}
    load = {}
    state = InteractionState()
    user = UserContextService()
    env = EnvironmentService()

    with Timer() as t:
        stt = stt_service.STTService(env, state)
    load["whisper"], memory["after_whisper"] = t.seconds, rss_mb()
    with Timer() as t:
        llm = LLMService(user)
    load["qwen"], memory["after_llm"] = t.seconds, rss_mb()
    tts = TTSService(state)
    with Timer() as t:
        face = FaceEmotionService(env)
        from deepface import DeepFace
        DeepFace.analyze(np.zeros((224, 224, 3), np.uint8), actions=["emotion"], enforce_detection=False)
    load["yolo_deepface"], memory["after_face"] = t.seconds, rss_mb()
    with Timer() as t:
        voice = VoiceEmotionService()
    load["wav2vec2"], memory["after_voice"] = t.seconds, rss_mb()
    fusion = EmotionFusionService()
    profile = ProfileMemoryService(user)
    thoughts = InternalThoughtService()
    with Timer() as t:
        extractor = MemoryExtractionService()   # shares the Qwen instance
    load["extractor"], memory["after_all_models"] = t.seconds, rss_mb()

    model = llm_provider.get_llm()
    raw_chat = model.create_chat_completion
    usage = []

    def recording_chat(*a, **k):
        response = raw_chat(*a, **k)
        usage.append(response["usage"])
        return response

    model.create_chat_completion = recording_chat

    chunk = stt_service.CHUNK_SIZE
    endpoint_s = (int(stt.silence_duration * stt.sample_rate / chunk) + 1) * chunk / stt.sample_rate

    def piper(text):
        start = time.perf_counter()
        proc = subprocess.Popen([tts.piper_path, "--model", tts.model_path, "--output_file", tts.output_file],
                                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, text=True)
        ps = psutil.Process(proc.pid)
        proc.stdin.write(text)
        proc.stdin.close()
        peak = 0
        while proc.poll() is None:
            try:
                info = ps.memory_info()
                peak = max(peak, getattr(info, "peak_wset", info.rss))
            except psutil.Error:
                pass
            time.sleep(0.01)
        return time.perf_counter() - start, sf.info(tts.output_file).duration, peak / 2**20

    def turn(wav):
        reference = wav.with_suffix(".txt").read_text().strip()
        shutil.copy(wav, config.RECORDING_PATH)
        row = {}
        with Timer() as t:
            audio, _ = sf.read(str(config.RECORDING_PATH), dtype="float32")
            segments, _ = stt.model.transcribe(audio, language="en", condition_on_previous_text=False)
            text = "".join(s.text for s in segments).strip()
        row["stt"] = t.seconds
        row["word_errors"], row["words"] = word_errors(reference, text)
        with Timer() as t:
            retrieved = [m["value"] for m in profile.retrieve(text, limit=3)]
        row["retrieval"] = t.seconds
        with Timer() as t:
            emotion = fusion.get_emotion(face.get_emotion(), voice.get_emotion(str(config.RECORDING_PATH)))
        row["voice_emotion"] = t.seconds
        calls = len(usage)
        with Timer() as t:
            reply = llm.generate(
                text, emotion, 70, 50, 50, 20, 20, 50, profile.get_likes(), profile.get_dislikes(),
                profile.get_facts(), 50, 50, 50, "You trust Hari.", retrieved,
                thoughts.generate(70, 20, 20, 50, {"trust": 50, "attachment": 50}, retrieved, "Hari"),
                env.objects, None, user_name="Hari")
        row["llm"] = t.seconds
        row["prompt_tokens"] = sum(u["prompt_tokens"] for u in usage[calls:])
        row["completion_tokens"] = sum(u["completion_tokens"] for u in usage[calls:])
        row["tts"], row["audio_seconds"], row["piper_peak_mb"] = piper(reply)
        row["processing"] = row["stt"] + row["retrieval"] + row["voice_emotion"] + row["llm"] + row["tts"]
        row["end_to_end"] = endpoint_s + row["processing"]
        with Timer() as t:
            for fact in extractor.extract(text)["facts"]:
                profile.add_fact(fact)
        row["extraction_after_speech"] = t.seconds
        row["heard"], row["reply"] = text, reply
        return row

    def run_pass(label):
        rows = []
        for k, wav in enumerate(wavs, 1):
            progress(label, k, len(wavs))
            rows.append(turn(wav))
            r = rows[-1]
            print(f"    stt {r['stt']:.2f}s | llm {r['llm']:.2f}s ({r['completion_tokens']} tok) | "
                  f"tts {r['tts']:.2f}s | end-to-end {r['end_to_end']:.2f}s | Tom: {r['reply']}", flush=True)
        return rows

    turn(wavs[0])   # warm-up, not counted

    print(">>> LLM generation speed (5 x 128 tokens)", flush=True)
    decode = []
    for _ in range(5):
        model.reset()
        start = time.perf_counter()
        first, tokens = None, 0
        for part in raw_chat(messages=[{"role": "user", "content": "Tell me a long story about a cat."}],
                             max_tokens=128, temperature=0.7, stream=True):
            if part["choices"][0]["delta"].get("content"):
                tokens += 1
                first = first or time.perf_counter()
        decode.append({"first_token_s": first - start,
                       "tokens_per_s": (tokens - 1) / (time.perf_counter() - first)})
    llm.history = []

    passes = {"camera_off": run_pass("camera off")}
    if CAMERA_CLIP.is_file():
        face.start()
        time.sleep(5)
        passes["camera_on"] = run_pass("camera on ")
        face.running = False
        time.sleep(1)
    else:
        print("RAVDESS not downloaded: skipping the camera-on pass")

    memory["peak"] = peak_mb()
    keys = ["stt", "retrieval", "voice_emotion", "llm", "tts", "processing", "end_to_end",
            "audio_seconds", "prompt_tokens", "completion_tokens", "extraction_after_speech"]
    results = {
        "end_of_turn_silence_s": endpoint_s,
        "load_seconds": load,
        "memory_mb": memory,
        "piper_peak_mb": max(r["piper_peak_mb"] for rows in passes.values() for r in rows),
        "llm_generation_tokens_per_s": statistics.mean(d["tokens_per_s"] for d in decode),
        "llm_generation_runs": decode,
    }
    for name, rows in passes.items():
        results[name] = {k: summarize([r[k] for r in rows]) for k in keys}
        results[name]["word_error_rate"] = sum(r["word_errors"] for r in rows) / sum(r["words"] for r in rows)
        results[name]["llm_reply_tokens_per_s"] = (
            sum(r["completion_tokens"] for r in rows) / sum(r["llm"] for r in rows))
        results[name]["turns"] = rows

    out = RESULTS_DIR / "pipeline.json"
    out.write_text(json.dumps(results, indent=2))
    drop_bench_db()

    print(f"\nPeak RAM {memory['peak']:.0f} MB (models loaded: {memory['after_all_models']:.0f} MB), "
          f"LLM generation {results['llm_generation_tokens_per_s']:.1f} tok/s")
    for name in passes:
        p = results[name]
        print(f"{name}: end-to-end {p['end_to_end']['mean']:.2f}s (p90 {p['end_to_end']['p90']:.2f}s) | "
              f"stt {p['stt']['mean']:.2f}s | llm {p['llm']['mean']:.2f}s | tts {p['tts']['mean']:.2f}s | "
              f"WER {p['word_error_rate']:.1%}")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
    import os
    sys.stdout.flush()
    os._exit(0)  # background model threads would otherwise keep the process alive
