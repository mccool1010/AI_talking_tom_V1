"""
AI Talking Tom - Model Downloader
Downloads the LLM model that is too large for GitHub (~2GB).
Other models (Whisper, DeepFace, wav2vec2) auto-download on first run.
Run this after installation: python download_models.py
"""

import os
import sys
import urllib.request

MODELS = [
    {
        "name": "Qwen 2.5 3B Instruct (Q4_K_M) — Main LLM Brain",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "dest": "models/llm/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_mb": 2007,
    },
]

# Models NOT in this list because they're handled automatically:
# - Piper TTS voice (en_US-lessac-medium.onnx) — included in repo
# - Piper TTS engine (piper.exe + DLLs) — included in repo
# - YOLOv8n (yolov8n.pt) — included in repo
# - Faster Whisper (base.en) — auto-downloads on first run
# - DeepFace (VGG-Face) — auto-downloads on first run
# - wav2vec2 (superb/wav2vec2-base-superb-er) — auto-downloads on first run


def download_file(url, dest, name, size_mb):
    """Download a file with progress."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if os.path.exists(dest):
        existing_mb = os.path.getsize(dest) / (1024 * 1024)
        if existing_mb > size_mb * 0.9:
            print(f"  [OK] {name} already exists ({existing_mb:.0f} MB)")
            return True

    print(f"  Downloading {name} ({size_mb} MB)...")
    print(f"  URL: {url}")
    print()

    try:
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 / total_size)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
                print(f"\r  [{bar}] {pct:.0f}% ({mb_done:.0f}/{mb_total:.0f} MB)", end="", flush=True)

        urllib.request.urlretrieve(url, dest, reporthook=progress_hook)
        print(f"\n  [OK] {name} downloaded successfully!")
        return True
    except Exception as e:
        print(f"\n  [FAIL] Download failed: {e}")
        print(f"  Download manually from: {url}")
        print(f"  Place the file in: {dest}")
        return False


def main():
    print("=" * 60)
    print("  AI Talking Tom - Model Downloader")
    print("=" * 60)
    print()
    print("  This downloads the Qwen 2.5 3B LLM model (~2 GB).")
    print("  Other models auto-download on first run.")
    print()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    success = 0
    total = len(MODELS)

    for model in MODELS:
        if download_file(model["url"], model["dest"], model["name"], model["size_mb"]):
            success += 1
        print()

    print("=" * 60)
    if success == total:
        print("  All models ready! You can now run AI Talking Tom.")
        print("  Use: run.bat  or  python launcher.py")
    else:
        print("  Some models failed. See links above to download manually.")
    print("=" * 60)


if __name__ == "__main__":
    main()
