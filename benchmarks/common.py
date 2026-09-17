"""Shared setup for the benchmark scripts.

Benchmarks use a separate MongoDB database (talking_tom_bench) so your real
data is never touched, and write outputs under benchmarks/results/.
"""
import os
import sys
import time
from pathlib import Path

# Always a separate scratch database; it is dropped before and after each run.
BENCH_DB = os.environ.get("TOM_BENCH_DB", "talking_tom_bench")
os.environ["TOM_MONGO_DB"] = BENCH_DB

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
DATA_DIR = BENCH_DIR / "data"
INPUTS_DIR = DATA_DIR / "inputs"
RAVDESS_DIR = DATA_DIR / "ravdess"
RESULTS_DIR = BENCH_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT / "backend"))
import config  # noqa: E402,F401  (sets CPU thread defaults before any model library loads)

import psutil  # noqa: E402

_PROC = psutil.Process()


def rss_mb():
    return _PROC.memory_info().rss / 2**20


def peak_mb():
    """Peak working set of this process (Windows); falls back to current RSS."""
    info = _PROC.memory_info()
    return getattr(info, "peak_wset", info.rss) / 2**20


def drop_bench_db():
    import config
    import db
    if config.MONGO_DB != BENCH_DB or "bench" not in BENCH_DB:
        raise RuntimeError(f"Refusing to drop database {config.MONGO_DB!r}")
    db.get_client().drop_database(BENCH_DB)


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.seconds = time.perf_counter() - self.start


def progress(label, done, total):
    filled = 40 * done // total
    print(f">>> {label} [{'#' * filled:<40}] {done}/{total}", flush=True)
