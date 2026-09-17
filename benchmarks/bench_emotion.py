"""
Face + voice emotion accuracy on RAVDESS audio-visual speech clips.

Uses the app's own code:
- face:   DeepFace every 0.2 s, classify_frame() from face_emotion_service,
          majority vote (as the camera thread does)
- voice:  VoiceEmotionService (wav2vec2, label used only above the
          configured confidence)
- fusion: EmotionFusionService

The main score covers the clips whose emotion the voice model can output
(neutral, happy, sad, angry). Progress is saved, so an interrupted run
resumes where it stopped. Needs ffmpeg on PATH and the dataset from
download_ravdess.py.

Usage: python benchmarks/bench_emotion.py [--limit N]
"""
import argparse
import json
import subprocess
from collections import Counter, defaultdict

from common import DATA_DIR, RAVDESS_DIR, RESULTS_DIR, progress

RAVDESS_LABELS = {"01": "neutral", "02": "calm", "03": "happy", "04": "sad",
                  "05": "angry", "06": "fear", "07": "disgust", "08": "surprise"}
VOICE_CLASSES = ["neutral", "happy", "sad", "angry"]
PARTIAL = RESULTS_DIR / "emotion_clips.jsonl"


def face_emotion(path):
    import cv2
    from deepface import DeepFace
    from face_emotion_service import FRAME_INTERVAL, HISTORY_SIZE, classify_frame

    cap = cv2.VideoCapture(str(path))
    step = max(1, round((cap.get(cv2.CAP_PROP_FPS) or 30) * FRAME_INTERVAL))
    history, i = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
            history.append(classify_frame(result, frame.shape)[2])
        i += 1
    cap.release()
    return Counter(history[-HISTORY_SIZE:]).most_common(1)[0][0]


def accuracy(rows, key, classes=None, calm_is_neutral=False):
    def truth(r):
        return "neutral" if calm_is_neutral and r["truth"] == "calm" else r["truth"]
    rows = [r for r in rows if classes is None or r["truth"] in classes]
    correct = sum(r[key] == truth(r) for r in rows)
    return {"accuracy": correct / len(rows), "correct": correct, "clips": len(rows)}


def recall(rows, key):
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["truth"] in VOICE_CLASSES:
            by[r["truth"]][0] += r[key] == r["truth"]
            by[r["truth"]][1] += 1
    return {c: f"{hit}/{n}" for c, (hit, n) in by.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only the first N clips (quick check)")
    args = parser.parse_args()

    clips = sorted(RAVDESS_DIR.glob("Actor_*/01-01-*.mp4"))[: args.limit]
    if not clips:
        raise SystemExit("No RAVDESS clips found. Run: python benchmarks/download_ravdess.py")

    import config
    from emotion_fusion_service import EmotionFusionService
    from voice_emotion_service import LABELS, VoiceEmotionService, pick_emotion

    voice = VoiceEmotionService()
    fusion = EmotionFusionService()
    wav = DATA_DIR / "emotion_clip.wav"

    done = {}
    if PARTIAL.exists():
        for line in PARTIAL.read_text().splitlines():
            row = json.loads(line)
            done[row["clip"]] = row

    for k, clip in enumerate(clips, 1):
        progress("clips", k, len(clips))
        if clip.name in done:
            continue
        parts = clip.stem.split("-")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-ac", "1", "-ar", "16000",
                        str(wav)], check=True)
        scores = {LABELS.get(r["label"], r["label"]): r["score"] for r in voice.classifier(str(wav))}
        row = {"clip": clip.name, "actor": parts[6], "intensity": parts[3],
               "truth": RAVDESS_LABELS[parts[2]], "face": face_emotion(clip), "voice_scores": scores}
        done[clip.name] = row
        with PARTIAL.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"    {row['truth']:8s} face={row['face']:8s} voice={max(scores, key=scores.get)}", flush=True)

    rows = [done[c.name] for c in clips]
    for r in rows:
        r["voice"] = pick_emotion(r["voice_scores"], config.VOICE_MIN_CONFIDENCE)
        r["voice_top"] = max(r["voice_scores"], key=r["voice_scores"].get)
        r["fusion"] = fusion.get_emotion(r["face"], r["voice"])

    four = [r for r in rows if r["truth"] in VOICE_CLASSES]
    results = {
        "clips": len(rows),
        "clips_4_emotions": len(four),
        "actors": sorted({r["actor"] for r in rows}),
        "voice_min_confidence": config.VOICE_MIN_CONFIDENCE,
        "most_common_emotion_baseline": max(Counter(r["truth"] for r in four).values()) / len(four),
    }
    for key in ["face", "voice", "voice_top", "fusion"]:
        results[key] = {
            "4_emotions": accuracy(rows, key, VOICE_CLASSES),
            "all_clips_calm_as_neutral": accuracy(rows, key, calm_is_neutral=True),
            "recall": recall(rows, key),
        }
    neutral_like = [r for r in rows if r["truth"] in ("neutral", "calm")]
    results["neutral_or_calm_called_angry"] = sum(r["fusion"] == "angry" for r in neutral_like) / len(neutral_like)
    results["rows"] = rows

    out = RESULTS_DIR / "emotion.json"
    out.write_text(json.dumps(results, indent=2))
    print()
    for key in ["face", "voice", "fusion"]:
        a = results[key]["4_emotions"]
        print(f"{key:7s} {a['accuracy']:.1%} ({a['correct']}/{a['clips']})  "
              f"all clips {results[key]['all_clips_calm_as_neutral']['accuracy']:.1%}  "
              f"recall {results[key]['recall']}")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
