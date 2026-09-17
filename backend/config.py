"""
Central configuration for the backend.

Every setting can be overridden with an environment variable, or with a
`tom.env` file (KEY=VALUE lines) in the repository root. Paths default to
locations inside the repository, so the project works wherever it is cloned.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(REPO_ROOT / "tom.env")


def _str(name, default):
    return os.environ.get(name, str(default))


def _int(name, default):
    return int(os.environ.get(name, default))


def _float(name, default):
    return float(os.environ.get(name, default))


def _bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _path(name, default):
    p = Path(os.environ.get(name, default))
    return p if p.is_absolute() else REPO_ROOT / p


# ---- LLM ----
LLM_MODEL_PATH = _path("TOM_LLM_MODEL", "models/llm/qwen2.5-3b-instruct-q4_k_m.gguf")
LLM_CONTEXT = _int("TOM_LLM_CONTEXT", 4096)
# -1 offloads every layer when llama-cpp-python is built with GPU support;
# CPU-only builds ignore it.
LLM_GPU_LAYERS = _int("TOM_LLM_GPU_LAYERS", -1)
LLM_MAX_REPLY_TOKENS = _int("TOM_LLM_MAX_REPLY_TOKENS", 40)
LLM_HISTORY_MAX = _int("TOM_LLM_HISTORY_MAX", 30)
LLM_HISTORY_KEEP = _int("TOM_LLM_HISTORY_KEEP", 16)
LLM_PROMPT_CACHE_MB = _int("TOM_LLM_PROMPT_CACHE_MB", 256)

# ---- Speech ----
WHISPER_MODEL = _str("TOM_WHISPER_MODEL", "base.en")
WHISPER_DEVICE = _str("TOM_WHISPER_DEVICE", "auto")  # auto | cpu | cuda
STT_SAMPLE_RATE = 16000
STT_ENERGY_THRESHOLD = _int("TOM_STT_ENERGY_THRESHOLD", 500)
STT_SILENCE_SECONDS = _float("TOM_STT_SILENCE_SECONDS", 1.0)
STT_USE_VAD = _bool("TOM_STT_USE_VAD", True)
PIPER_EXE = _path("TOM_PIPER_EXE", "piper/piper.exe")
PIPER_VOICE = _path("TOM_PIPER_VOICE", "models/tts/en_US-lessac-medium.onnx")
YOLO_MODEL = _path("TOM_YOLO_MODEL", "yolov8n.pt")
VOICE_MIN_CONFIDENCE = _float("TOM_VOICE_MIN_CONFIDENCE", 0.70)

# ---- Runtime files ----
RUNTIME_DIR = _path("TOM_RUNTIME_DIR", "runtime")
RECORDING_PATH = RUNTIME_DIR / "recording.wav"
TTS_OUTPUT_PATH = RUNTIME_DIR / "output.wav"
LOG_DIR = RUNTIME_DIR / "logs"
LOG_LEVEL = _str("TOM_LOG_LEVEL", "INFO")

# ---- Database ----
MONGO_URI = _str("TOM_MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = _str("TOM_MONGO_DB", "talking_tom")
MONGO_TIMEOUT_MS = _int("TOM_MONGO_TIMEOUT_MS", 3000)

# ---- Users ----
DEFAULT_USER_ID = _str("TOM_DEFAULT_USER_ID", "default")
DEFAULT_USER_NAME = _str("TOM_DEFAULT_USER_NAME", "Hari")

# ---- Dashboard API ----
# Loopback only by default: the API exposes the camera and personal memories.
API_HOST = _str("TOM_API_HOST", "127.0.0.1")
API_PORT = _int("TOM_API_PORT", 8000)
API_ALLOWED_ORIGINS = [
    o.strip() for o in _str(
        "TOM_API_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",") if o.strip()
]
API_SESSION_HOURS = _int("TOM_API_SESSION_HOURS", 12)

# ---- Godot bridge ----
GODOT_HOST = _str("TOM_GODOT_HOST", "127.0.0.1")
GODOT_PORT = _int("TOM_GODOT_PORT", 9090)


def ensure_runtime_dirs():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
