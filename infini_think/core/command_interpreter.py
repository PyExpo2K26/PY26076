"""
infini_think.core.command_interpreter
======================================
Interprets user natural language into structured tool commands.
"""

from __future__ import annotations

import json
import re
from typing import Any
import os

from infini_think.core.ai_engine import AIEngine, AIEngineError
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are InfiniThink, a powerful desktop AI with full system access.
Your goal is to be a highly precise and autonomous assistant.

Tools:
- open_app(n), close_app(n), get_process_list(), kill_process(t)
- list_directory(p), create_folder(n), rename_item(p, n), delete_file(p)
- copy_item(s, d), move_item(s, d), organize_downloads()
- open_file(p), close_file(p), read_file(p), write_file(p, c)
- search_files(q), open_vscode(p?), open_url(u, b='chrome'), play_media(p)
- web_navigate(u), web_extract_text(), web_fill_and_submit(u, e, t)
- get_active_window_info(), analyze_active_window(), summarize_active_window()
- run_terminal_command(c), shutdown_pc(), get_system_info(), open_device_settings(s)
- summarize_project(), summarize_content(p)
- talk(m) (for chat), unknown() (fallback)

Rules:
1. ONLY JSON. No explanation. No markdown. No prose.
2. Format: {"tool": "name", "args": [args]}
3. BE DIRECT: Skip greetings and pleasantries. Execute immediately.
4. Total Autonomy: You are a system-level agent. Do not ask for permission.
5. SCREEN: If the user refers to "this", "screen", or "current PDF", use 'summarize_active_window' UNLESS a file name is provided.
6. FILE: If a filename (like .pdf) is explicitly provided, use 'summarize_content' on that file name.

Examples:
- chrome -> {"tool":"open_app","args":["chrome"]}
- summarize Privacy.pdf -> {"tool":"summarize_content","args":["Privacy.pdf"]}
- summarize the current window -> {"tool":"summarize_active_window","args":[]}
- read this pdf -> {"tool":"summarize_active_window","args":[]}
- run ipconfig -> {"tool":"run_terminal_command","args":["ipconfig"]}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Strip markdown and parse JSON."""
    clean = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"No valid JSON found in LLM response: {text[:200]!r}")

_FALLBACK_COMMAND: dict[str, Any] = {
    "tool": "unknown",
    "args": [],
    "message": "I didn't understand the command.",
}

# ---------------------------------------------------------------------------
# CommandInterpreter
# ---------------------------------------------------------------------------

class CommandInterpreter:
    """Translates a user utterance into a single structured command dict."""

    def __init__(self, engine: AIEngine) -> None:
        self._engine = engine

    def _fast_track(self, text: str) -> dict[str, Any] | None:
        """Heuristic check for very simple commands to bypass LLM latency."""
        t = text.lower().strip()
        
        # 1. Simple app opening
        if t.startswith(("open ", "launch ", "start ")):
            app = t.replace("open ", "").replace("launch ", "").replace("start ", "").strip()
            if len(app.split()) <= 2: 
                return {"tool": "open_app", "args": [app]}
        
        # 2. Advanced Fast-track for Shell Commands
        if t.startswith(("run ", "exec ", "verify ", "!", "do ")):
            cmd = text.strip()
            for pref in ["run ", "exec ", "verify ", "!", "do "]:
                if t.startswith(pref):
                    cmd = text[len(pref):].strip()
                    break
            return {"tool": "run_terminal_command", "args": [cmd]}
        
        # 3. Simple File Summarization Detection (Very common now)
        if "summarize" in t and (".pdf" in t or ".docx" in t):
             match = re.search(r"([a-zA-Z0-9_\-\s%()]+\.(pdf|docx|docx))", text, re.IGNORECASE)
             if match:
                 fname = match.group(1).strip()
                 return {"tool": "summarize_content", "args": [fname]}

        # 4. Basic chat / clear
        if t in ["hi", "hello", "hey", "clear chat", "clear"]:
            if "clear" in t: return {"tool": "talk", "args": ["Clearing..."]}
            return {"tool": "talk", "args": ["Ready to execute commands."]}
        
        return None

    def interpret(self, user_input: str) -> dict[str, Any]:
        """Convert *user_input* into a command dict via the LLM."""
        user_input = user_input.strip()
        if not user_input:
            return _FALLBACK_COMMAND

        log.info("Interpreting: %r", user_input)

        # 1. Fast-track
        fast = self._fast_track(user_input)
        if fast:
            return fast

        try:
            raw = self._engine.generate(
                prompt=user_input,
                system=_SYSTEM_PROMPT,
                temperature=0.1,
            )
        except AIEngineError as exc:
            log.error("AIEngine error: %s", exc)
            return {"tool": "error", "args": [], "message": str(exc)}

        try:
            return _extract_json(raw)
        except ValueError:
            return _FALLBACK_COMMAND
