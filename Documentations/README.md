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

## 📦 Project Structure

```
Project/
├── __init__.py             ← Package root
├── pyproject.toml          ← Packaging & entry point
├── requirements.txt        ← Runtime deps
│
├── app/
│   └── launcher.py         ← Entry point: infini-think CLI command
│
├── gui/
│   ├── main_window.py      ← QMainWindow + AI worker thread
│   ├── chat_widget.py      ← Scrollable chat, message bubbles
│   └── voice_controls.py   ← Mic button with animation
│
├── voice/
│   ├── speech_to_text.py   ← SpeechRecognition (background thread)
│   └── text_to_speech.py   ← pyttsx3 async queue
│
├── core/
│   ├── ai_engine.py        ← Ollama REST client
│   ├── command_interpreter.py ← NL → JSON command via LLM
│   ├── planner.py          ← Multi-step task planning
│   └── executor.py         ← Tool registry + dispatch
│
├── tools/
│   ├── app_tools.py        ← open_app(), open_vscode()
│   ├── file_tools.py       ← organize_downloads(), search_files(), ...
│   └── system_tools.py     ← run_terminal_command(), get_system_info(), ...
│
├── interfaces/
│   ├── cli_interface.py    ← Coloured CLI REPL
│   ├── text_interface.py   ← Shared data types & base class
│   └── voice_interface.py  ← Headless voice loop
│
├── config/
│   └── settings.py         ← Central config (env-var overrides)
│
├── utils/
│   └── logger.py           ← Rotating file + colour console logger
│
└── tests/
    └── test_basic.py       ← Unit tests (no Ollama required)
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
cd infini-think/Project
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
- [ ] **Workflow recorder** — record + replay multi-step automations
- [ ] **Light theme** — toggle in menu
- [ ] **Custom hotkey** — global shortcut to open InfiniThink
- [ ] **Windows tray icon** — always-on background mode

---

## 📄 License

MIT — see [LICENSE](LICENSE).
