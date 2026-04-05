# InfiniThink — Architecture Reference

This document describes the internal architecture of InfiniThink in detail.

---

## Layer Overview

InfiniThink is structured as a **layered AI agent pipeline**. Each layer has
a single responsibility and communicates only with adjacent layers.

```
┌─────────────────────────────────────────────┐
│           User Interface Layer              │
│  GUI (PySide6) │ Voice (STT/TTS) │ CLI REPL │
└────────────────────┬────────────────────────┘
                     │ user_input: str
                     ▼
┌─────────────────────────────────────────────┐
│           AI Interpretation Layer           │
│  CommandInterpreter → LLM → JSON command    │
└────────────────────┬────────────────────────┘
                     │ {"tool":"…","args":[…]}
                     ▼
┌─────────────────────────────────────────────┐
│           Task Planning Layer               │
│  TaskPlanner → multi-step plan list         │
└────────────────────┬────────────────────────┘
                     │ [cmd1, cmd2, …]
                     ▼
┌─────────────────────────────────────────────┐
│           Execution Layer                   │
│  Executor → tool registry dispatch          │
└────────────────────┬────────────────────────┘
                     │ ExecutionResult[]
                     ▼
┌─────────────────────────────────────────────┐
│               Tool Layer                    │
│  app_tools │ file_tools │ system_tools      │
└────────────────────┬────────────────────────┘
                     │
                     ▼
              OS / File System
```

---

## Module-by-Module Breakdown

### `config/settings.py` — Central Configuration

A single `Settings` dataclass is instantiated at module-import time and
shared across the entire application via `from infini_think.config.settings import settings`.

Key design choices:
- Reads environment variables for every tuneable parameter
- Ensures log/data directories exist on startup
- No mutable global state — all attributes are set at `__init__` time

---

### `utils/logger.py` — Logging Infrastructure

- One-time initialisation guarded by `_configured: bool`
- Console handler uses ANSI colour codes when stdout is a TTY
- Rotating file handler writes to `~/.infini_think/logs/infini_think.log` (5 MB × 3 backups)
- All loggers are children of the `infini_think` namespace

---

### `core/ai_engine.py` — Ollama Client

Communicates with the **Ollama REST API** at `http://localhost:11434/api/generate`.

Key design choices:
- Uses `requests.Session` for connection pooling
- `stream=False` for simple, complete responses (streaming variant also available)
- `generate()` raises `AIEngineError` (not generic exceptions) so callers can handle cleanly
- `is_available()` does a cheap GET to `/api/tags` instead of an LLM call

---

### `core/command_interpreter.py` — NL → JSON

Uses a **large, detailed system prompt** to coerce the LLM into responding
with *only* a JSON object (no markdown, no prose).

Fallback strategy:
1. Try `json.loads(response)` directly
2. Strip markdown fences and retry
3. Extract first `{…}` block via regex
4. Return `{"tool": "unknown", …}` if all fail

Temperature is set to `0.1` for maximum determinism.

---

### `core/planner.py` — Task Planning

The planner uses a **heuristic fast-path** for simple requests:
- Checks for conjunction words (`and`, `then`, `also`, `next`) and compound verbs (`prepare`, `set up`)
- Simple requests → delegate directly to `CommandInterpreter` (saves one LLM call)
- Complex requests → call LLM with a planning-specific system prompt that returns a JSON array

---

### `core/executor.py` — Command Dispatch

The **tool registry pattern** stores `{name: callable}` mappings.  No `if/elif`
chains — new tools are added with a single `executor.register("name", func)` call.

Each `execute()` call:
1. Looks up the tool in the registry
2. Calls `func(*args)` inside a try/except
3. Returns a typed `ExecutionResult` dict with `success`, `output`, `elapsed`, `error`

`execute_plan()` iterates steps in order, stopping early only on `shutdown_pc` failure.

---

### `tools/` — Tool Functions

All tool functions are pure Python functions that:
- Accept only basic Python types (str, int, list)
- Return a human-readable string (displayed in chat + optionally spoken)
- Never raise — catch all exceptions and return error strings

**app_tools.py** — `open_app()` resolves friendly names (`"chrome"` → `"chrome"`)
through a dictionary alias map and uses `subprocess.Popen` with `shell=True start`
on Windows for compatibility with both `.exe` names and `ms-` URI schemes.

**file_tools.py** — `organize_downloads()` iterates `Downloads/` and moves each
file into a category subfolder determined by extension.  Naming conflicts append
a counter suffix rather than overwriting.

**system_tools.py** — `get_system_info()` uses only stdlib (platform, os, ctypes)
so `psutil` is not required.

---

### `gui/` — PySide6 Interface

#### Threading model

AI inference is **always executed on a `QThread` worker** (`_AIWorker`) so the
GUI event loop never blocks.  Results are delivered back to the GUI thread via
Qt signals (`result_ready`, `error`, `finished`).

STT callbacks arrive on a non-GUI background thread.  They are marshalled
safely to the GUI thread using `QMetaObject.invokeMethod(..., QueuedConnection)`.

#### Widget hierarchy

```
MainWindow (QMainWindow)
├── Header bar (QWidget)
│   ├── Title label
│   └── Ollama status indicator
├── ChatWidget (QWidget)               ← central content
│   ├── MessageArea (QScrollArea)
│   │   └── QWidget (container)
│   │       └── MessageBubble × N     ← one per message
│   └── Input row (QHBoxLayout)
│       ├── InputBox (QTextEdit)       ← Enter-to-send
│       ├── MicButton (QPushButton)
│       └── SendButton (QPushButton)
└── QStatusBar
```

---

### `voice/` — Audio I/O

**SpeechToText** runs a `SpeechRecognition` recognition loop on a daemon thread.
The thread adjusts for ambient noise on startup and uses `listen()` with a 5-second
`timeout` so it can check `self._listening` periodically rather than blocking
indefinitely.

**TextToSpeech** manages a `queue.Queue`.  The worker thread pulls text items
and calls `engine.say()` / `engine.runAndWait()` serially.  A sentinel object
signals clean shutdown.

---

## Data Flow Example — "open chrome"

```
1. User types "open chrome" in ChatWidget
2. ChatWidget emits message_submitted("open chrome")
3. MainWindow creates _AIWorker (QThread)
4. Worker: planner.plan("open chrome")
   → _looks_complex() → False (single action)
   → interpreter.interpret("open chrome")
   → engine.generate(prompt, system=SYSTEM_PROMPT)  [Ollama API call]
   → LLM returns '{"tool":"open_app","args":["chrome"]}'
   → plan = [{"tool":"open_app","args":["chrome"]}]
5. Worker: executor.execute_plan(plan)
   → executor.execute({"tool":"open_app","args":["chrome"]})
   → registry["open_app"]("chrome")
   → open_app("chrome") → subprocess.Popen("start chrome", shell=True)
   → returns "Launched: chrome"
6. Worker emits result_ready([{success:True, output:"Launched: chrome"}])
7. MainWindow._on_results_ready() runs on GUI thread
8. chat.add_ai_message("✅ Launched: chrome")
9. tts.speak("Launched: chrome")
```

---

## Extension Points

| What to add | Where to add it |
|-------------|----------------|
| New tool function | `tools/`  any file, register in `executor._register_default_tools()` |
| New app alias | `tools/app_tools._WIN_APP_MAP` |
| New file category | `tools/file_tools._CATEGORY_MAP` |
| New interface | Subclass `interfaces.text_interface.BaseInterface` |
| New settings | `config/settings.py` `Settings` dataclass |

