# ⚡ InfiniThink

<div align="center">

**A local-first desktop AI agent — no cloud, no subscriptions, 100% private.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green?logo=qt)](https://doc.qt.io/qtforpython/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-orange)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

</div>

---

## 📖 Overview

InfiniThink lets you control your computer using **plain English**. Type a message or speak a command, and the AI interprets it, plans the steps, and executes them — all on your machine.

```
You: "prepare my research workspace"
InfiniThink: ✅ Launched Chrome
             ✅ Launched Notion  
             ✅ Opened research folder
```

Everything runs locally through **[Ollama](https://ollama.com)** (e.g. Llama 3). No API keys, no internet required for AI inference.

---

## 🏗️ Architecture

```
User (GUI / Voice / CLI)
        │
        ▼
┌──────────────────────┐
│  Input Processor     │  — Chat widget, STT, CLI readline
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Command Interpreter  │  — LLM via Ollama REST API → JSON command
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│   Task Planner       │  — Multi-step plans for complex requests
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  Execution Engine    │  — Tool registry dispatch + error handling
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│    Tool System       │  — app_tools · file_tools · system_tools
└──────────────────────┘
         │
         ▼
   System Actions
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full layer-by-layer breakdown.

---

## 📂 Project Structure

```
.
├── infini_think/           ← Core package (gui, core, tools, voice)
├── assets/                 ← Application icons and media
├── tests/                  ← Unit testing suite
├── .gitignore              ← GitHub exclusion rules
├── requirements.txt        ← Standard runtime dependencies
├── README.md               ← Main documentation
├── LICENSE                 ← MIT License (Private/Internal)
├── ARCHITECTURE.md         ← Technical architecture breakdown
└── pyproject.toml          ← Python packaging and entry points
```

---

## 🚀 Installation

### Prerequisites

| Requirement | Install / Notes |
|-------------|-----------------|
| Python 3.10+ | [python.org](https://python.org) |
| Ollama | [ollama.com](https://ollama.com) |
| Llama 3 model | `ollama pull llama3` |

### 1 — Clone and install

```bash
git clone https://github.com/your-org/infini-think.git
cd infini-think
pip install -r requirements.txt
```

> **Windows PyAudio note:** If `pip install pyaudio` fails, install the pre-built wheel:
> ```
> pip install pipwin && pipwin install pyaudio
> ```

### 2 — Start Ollama

```bash
ollama serve           # start the server (new terminal)
ollama pull llama3     # download the model (first time only)
```

### 3 — Launch InfiniThink

```bash
# GUI (default)
python -m infini_think.app.launcher

# Or install as a package and use the CLI command
pip install -e .
infini-think
```

---

## 💬 Usage

### GUI Mode (default)

Launch the chat window and type or speak your commands:

| Command | What happens |
|---------|--------------|
| `open chrome` | Launches Google Chrome |
| `organize my downloads` | Sorts Downloads folder by type |
| `open my project folder` | Opens user's project directory |
| `prepare my research workspace` | Opens Chrome + Notion + research folder |
| `create a folder called Work` | Creates `~/Work` |
| `what's my system info` | Returns CPU, RAM, OS details |
| `run ipconfig` | Executes shell command and shows output |

### CLI Mode

```bash
infini-think --cli
# or
infini-think --cli --verbose   # show plan details
```

### Voice Mode

```bash
infini-think --voice
```

### Override Model

```bash
infini-think --model mistral
infini-think --model llama3.1
```

---

## 🛠️ Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/ -v

# Type checking
mypy Project/

# Linting
ruff check Project/

# Format
black Project/
```

---

## 🔧 Configuration

All settings in `config/settings.py` can be overridden via environment variables:

| Variable | Default | Description |
|---|---|---|
| `INFINI_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `INFINI_OLLAMA_MODEL` | `llama3` | Model to use |
| `INFINI_OLLAMA_TIMEOUT` | `60` | Request timeout (seconds) |
| `INFINI_VOICE` | `true` | Enable voice I/O |
| `INFINI_THEME` | `dark` | UI theme (`dark`/`light`) |
| `INFINI_LOG_LEVEL` | `INFO` | Log level |

---

## 🔭 Roadmap

- [ ] **Plugin system** — drop-in tools via Python entry points
- [ ] **Contextual memory** — conversation history across sessions
- [ ] **Background agents** — scheduled and event-triggered automation
- [x] **Premium UI & Themes** — dynamic Dark/Light mode toggle
- [ ] **Custom hotkey** — global shortcut to open InfiniThink
- [ ] **Windows tray icon** — always-on background mode

---

## 📄 License

MIT — see [LICENSE](LICENSE).

<video controls src="Screen Recording 2026-03-19 111224.mp4" title="Title"></video>