# AI Talking Tom 🐱

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
- **Python 3.10+** 
- **Godot 4.6** — [Download](https://godotengine.org/download)
- **MongoDB** — [Download](https://www.mongodb.com/try/download/community)
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

# Install dependencies
pip install -r requirements.txt
```

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
```bash
# Terminal 1: Start backend
cd backend
python main.py

# Terminal 2: Open Godot project
# Open Godot → Import project from godot/ folder → Press F5
```

### LLM Model Setup

Download a GGUF model and place it in `backend/app/models/llm/`:
- Recommended: Qwen2.5 or similar small model in GGUF format

## Project Structure

```
AI-Talking-Tom/
├── backend/           # Python AI brain
│   ├── main.py        # Main loop
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
