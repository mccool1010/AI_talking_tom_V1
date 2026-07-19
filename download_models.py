"""
AI Talking Tom - Model Downloader
Downloads required AI models that are too large for GitHub.
Run this after installation: python download_models.py
"""

import os
import sys
import urllib.request
import hashlib

MODELS = [
    {
        "name": "Qwen 2.5 3B Instruct (Q4_K_M)",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "dest": "models/llm/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_mb": 2007,
    },
    {
        "name": "Piper TTS Voice (en_US-lessac-medium)",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "dest": "models/tts/en_US-lessac-medium.onnx",
        "size_mb": 60,
    },
]


def download_file(url, dest, name, size_mb):
    """Download a file with progress."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if os.path.exists(dest):
        existing_mb = os.path.getsize(dest) / (1024 * 1024)
        if existing_mb > size_mb * 0.9:
            print(f"  ✓ {name} already exists ({existing_mb:.0f} MB)")
            return True

    print(f"  ↓ Downloading {name} ({size_mb} MB)...")
    print(f"    URL: {url}")

    try:
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 / total_size)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
                print(f"\r    [{bar}] {pct:.0f}% ({mb_done:.0f}/{mb_total:.0f} MB)", end="", flush=True)

        urllib.request.urlretrieve(url, dest, reporthook=progress_hook)
        print(f"\n  ✓ {name} downloaded!")
        return True
    except Exception as e:
        print(f"\n  ✗ Failed: {e}")
        print(f"    Download manually from: {url}")
        return False


def main():
    print("=" * 55)
    print("  AI Talking Tom - Model Downloader")
    print("=" * 55)
    print()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    success = 0
    total = len(MODELS)

    for model in MODELS:
        if download_file(model["url"], model["dest"], model["name"], model["size_mb"]):
            success += 1
        print()

    print("=" * 55)
    print(f"  Done: {success}/{total} models ready")
    if success == total:
        print("  You can now run AI Talking Tom!")
    else:
        print("  Some models failed — see links above to download manually.")
    print("=" * 55)


if __name__ == "__main__":
    main()
