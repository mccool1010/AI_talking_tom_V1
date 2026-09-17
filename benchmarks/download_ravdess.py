"""
Download the RAVDESS audio-visual speech clips for actors 01-04 (~2.2 GB).

Files come from a Hugging Face mirror (much faster than Zenodo) and are
checked two ways: huggingface_hub verifies each zip's SHA-256, and every
video's CRC32 is compared with the zip index of the official Zenodo release
(fetched with a small range request), so the clips are identical to the
originals.

Usage: python benchmarks/download_ravdess.py [--actors 01 02 03 04]
"""
import argparse
import struct
import sys
import urllib.request
import zipfile

from huggingface_hub import hf_hub_download

from common import RAVDESS_DIR

MIRROR = "HoangPhuc7679/RAVDESS"
ZENODO = "https://zenodo.org/records/1188976/files/{name}?download=1"


def zenodo_crcs(name):
    """CRC32 of every member in the official Zenodo zip, read from its central directory."""
    url = ZENODO.format(name=name)
    total = int(urllib.request.urlopen(
        urllib.request.Request(url, method="HEAD"), timeout=60).headers["Content-Length"])
    tail = urllib.request.urlopen(
        urllib.request.Request(url, headers={"Range": "bytes=-65536"}), timeout=120).read()
    eocd = tail.rfind(b"PK\x05\x06")
    cd_size, cd_offset = struct.unpack("<II", tail[eocd + 12:eocd + 20])
    directory = tail[len(tail) - (total - cd_offset):][:cd_size]
    crcs, i = {}, 0
    while directory[i:i + 4] == b"PK\x01\x02":
        crc, = struct.unpack("<I", directory[i + 16:i + 20])
        name_len, extra_len, comment_len = struct.unpack("<HHH", directory[i + 28:i + 34])
        crcs[directory[i + 46:i + 46 + name_len].decode()] = crc
        i += 46 + name_len + extra_len + comment_len
    return crcs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--actors", nargs="+", default=["01", "02", "03", "04"])
    args = parser.parse_args()

    RAVDESS_DIR.mkdir(parents=True, exist_ok=True)
    for k, actor in enumerate(args.actors, 1):
        name = f"Video_Speech_Actor_{actor}.zip"
        if len(list((RAVDESS_DIR / f"Actor_{actor}").glob("*.mp4"))) >= 120:
            print(f"[{k}/{len(args.actors)}] {name}: already extracted")
            continue
        print(f"\n[{k}/{len(args.actors)}] {name}", flush=True)
        path = hf_hub_download(MIRROR, name, repo_type="dataset", local_dir=RAVDESS_DIR / "_zips")
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                sys.exit(f"Corrupt file {bad} in {name}; delete {path} and retry")
            mine = {i.filename: i.CRC for i in z.infolist()}
            if mine != zenodo_crcs(name):
                sys.exit(f"{name} does not match the official Zenodo release")
            print(f"  {len(mine)} files identical to the Zenodo release; extracting", flush=True)
            z.extractall(RAVDESS_DIR)
    print(f"\nRAVDESS ready in {RAVDESS_DIR}")


if __name__ == "__main__":
    main()
