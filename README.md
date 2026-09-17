# AI Talking Tom 🐱

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Godot](https://img.shields.io/badge/Godot-4.6-478CBF?style=for-the-badge&logo=godotengine)
![LLM](https://img.shields.io/badge/AI-Local_LLM-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

<div align="center">
  <img src="https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif" alt="Fun Cat GIF" width="250"/>
</div>

An AI-powered virtual companion built with Godot 4.6, Python, and local LLMs. Tom listens to you, understands emotions, remembers conversations, and responds with personality.

## Features

- **Speech Recognition** — Real-time STT with Faster Whisper
- **Local LLM** — Runs entirely offline using llama.cpp
- **Text-to-Speech** — Natural voice with Piper TTS
- **Emotion Detection** — Face + voice emotion fusion
- **Memory System** — Remembers likes, dislikes, facts about you
- **Personality** — Dynamic traits that evolve over conversations
- **3D Avatar** — Animated Talking Tom model with 62 animations
- **Dashboard** — Web UI for monitoring Tom's internal state

## Screenshots

*(Please save the screenshots you captured to an `assets/` folder in this repository with these names so they show up properly!)*

### The Talking Tom Avatar
![Tom Avatar](./assets/screenshot_avatar.png)

### Web Dashboard & Vitals
![Dashboard Vitals](./assets/screenshot_dashboard.png)

### Dashboard Login
![Login Screen](./assets/screenshot_login.png)

### Memories & Conversation Logs
![Memories and Logs](./assets/screenshot_memory.png)

## Architecture

```
┌──────────────┐     TCP/JSON     ┌──────────────┐
│   Godot 4.6  │◄────────────────►│ Python Brain │
│  (3D Avatar) │   Port 9090      │  (Backend)   │
└──────────────┘                  └──────┬───────┘
                                         │
                              ┌──────────┼──────────┐
                              │          │          │
                         ┌────▼───┐ ┌────▼───┐ ┌───▼────┐
                         │  STT   │ │  LLM   │ │  TTS   │
                         │Whisper │ │llama.cpp│ │ Piper  │
                         └────────┘ └────────┘ └────────┘
```

## Quick Start

### Prerequisites
- **Python 3.12** (the pinned dependencies are tested on 3.12)
- **Godot 4.6** — [Download](https://godotengine.org/download)
- **MongoDB** — [Download](https://www.mongodb.com/try/download/community) *(Note: The database and collections are created automatically on first launch. Just install and start the service!)*
- **Git LFS** — `git lfs install`

### Installation

```bash
# Clone the repo
git clone https://github.com/mccool1010/AI_talking_tom_V1.git
cd AI_talking_tom_V1

# Pull LFS files (3D models, binaries)
git lfs pull

# Create Python virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies (exact, tested versions)
pip install -r requirements.lock

# Build the web dashboard (served by the backend at http://localhost:8000)
cd dashboard && npm ci && npm run build && cd ..

# Download the LLM model (~2GB, too large for GitHub)
python download_models.py
```

> **Note:** If `download_models.py` fails, download the Qwen 2.5 3B GGUF manually from
> [HuggingFace](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF) and place it in `models/llm/`

### Running

**Option 1: Batch launcher**
```bash
run.bat
```

**Option 2: GUI launcher**
```bash
python launcher.py
```

**Option 3: Manual**

The backend logs to the console and to `runtime/logs/tom.log`.
```bash
# Terminal 1: Start backend
cd backend
python main.py

# Terminal 2: Open Godot project
# Open Godot → Import project from godot/ folder → Press F5
```

### AI Models

| Model | Size | How to get |
|---|---|---|
| **Qwen 2.5 3B** (LLM) | 2 GB | `python download_models.py` |
| **Piper TTS voice** | 60 MB | Included in repo |
| **Piper engine** | 20 MB | Included in repo |
| **YOLOv8n** | 6.5 MB | Included in repo |
| **Faster Whisper** | 150 MB | Auto-downloads on first run |
| **DeepFace** | 500 MB | Auto-downloads on first run |
| **wav2vec2 emotion** | 360 MB | Auto-downloads on first run |

## Configuration

Settings live in [backend/config.py](backend/config.py) and can be overridden with
environment variables or a `tom.env` file in the repo root. Copy
[tom.env.example](tom.env.example) to get started. Common settings:

| Variable | Default | Purpose |
|---|---|---|
| `TOM_LLM_GPU_LAYERS` | `-1` | Layers offloaded to the GPU (needs a CUDA build of llama-cpp-python) |
| `TOM_WHISPER_DEVICE` | `auto` | `auto` tries CUDA, then falls back to CPU |
| `TOM_STT_SILENCE_SECONDS` | `1.0` | Silence that ends your turn |
| `TOM_MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection |
| `TOM_API_HOST` | `127.0.0.1` | Dashboard API bind address |

## Security

The dashboard shows the live camera, stored memories and chat history, so:

- The API listens on `127.0.0.1` only. Nothing on your network can reach it unless you change `TOM_API_HOST`.
- Every data endpoint needs a session token from logging in. A session only sees data while its user is the one Tom is talking to.
- The default account has no password and can only log in from the same machine. Give every account a password before exposing the API.
- Repeated failed logins lock the account for 5 minutes.

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest            # unit tests: no models, GPU or MongoDB needed
cd dashboard && npm run lint
```

The `backend/test_*.py` files are manual hardware and model scripts, not part of the test suite.

## Project Structure

```
AI-Talking-Tom/
├── backend/           # Python AI brain
│   ├── main.py        # Service wiring and main loop
│   ├── config.py      # All settings (env / tom.env overridable)
│   ├── llm_service.py # LLM integration
│   ├── stt_service.py # Speech-to-text
│   ├── tts_service.py # Text-to-speech
│   ├── godot_bridge.py# TCP bridge to Godot
│   └── ...            # 20+ service modules
├── godot/             # Godot 4.6 project
│   ├── models/        # 3D models (GLB)
│   ├── scenes/        # Scene files
│   └── scripts/       # GDScript
├── dashboard/         # React/Vite web dashboard
├── piper/             # Piper TTS engine
├── tests/             # pytest suite
├── launcher.py        # GUI launcher
├── run.bat            # Batch launcher
└── requirements.txt   # Python dependencies
```

## Credits

### 3D Models (CC BY License)
- **Talking Tom Cat 3** — Sketchfab
- **Cartoon Sofa** — Sketchfab
- **Stylized Bookshelf** — Sketchfab
- **Cartoon Table** — Sketchfab
- **Floor Lamp** — Sketchfab
- **Stylized Window** — Sketchfab
- **Potted Plant** — Sketchfab
- **TeaScroll Rug** — Sketchfab

## License

See [license.txt](license.txt)
