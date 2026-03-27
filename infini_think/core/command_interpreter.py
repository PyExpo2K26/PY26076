"""
infini_think.core.command_interpreter
======================================
Converts a natural-language user utterance into a structured command dict
by prompting the local LLM through :class:`AIEngine`.

The LLM is instructed to reply **only** with valid JSON so the output can be
parsed directly.  If parsing fails a safe fallback command is returned.

Example
-------
Input:  ``"open chrome"``
Output: ``{"tool": "open_app", "args": ["chrome"]}``
"""

from __future__ import annotations

import json
import re
from typing import Any

from infini_think.core.ai_engine import AIEngine, AIEngineError
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are InfiniThink, a powerful desktop AI with full system access.
Your goal is to be a highly precise and autonomous assistant.

Tools:
- open_app(n), close_app(n), get_process_list(), kill_process(t)
- list_directory(p), create_folder(n), rename_item(p, n), delete_file(p)
- copy_item(s, d), move_item(s, d), organize_downloads()
- open_file(p), close_file(p), read_file(p), write_file(p, c)
- search_files(q), open_vscode(p?), open_url(u, b='chrome')
- web_navigate(u), web_extract_text(), web_fill_and_submit(u, e, t)
- get_active_window_info(), analyze_active_window(), summarize_active_window()
- run_terminal_command(c), shutdown_pc(), get_system_info()
- talk(m) (for chat), unknown() (fallback)

Rules:
1. ONLY JSON. No explanation. No markdown.
2. Format: {"tool": "name", "args": [args]}
3. Be precise: Choose the most specific tool for the task.
4. Total Autonomy: You have permission to manage any file or process on this device.
5. If the user asks about their screen, use 'summarize_active_window'.

Examples:
- chrome -> {"tool":"open_app","args":["chrome"]}
- what's on my screen? -> {"tool":"summarize_active_window","args":[]}
- list files in downloads -> {"tool":"list_directory","args":["downloads"]}
- hi -> {"tool":"talk","args":["Hello! I am ready to assist with any task on your device."]}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict[str, Any]:
    """Extract and parse the first JSON object found in *text*.

    Args:
        text: Raw LLM response which may contain surrounding prose.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no valid JSON object can be found.
    """
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

    # Try parsing straight away
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt to extract the first {...} block
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in LLM response: {text[:200]!r}")


_FALLBACK_COMMAND: dict[str, Any] = {
    "tool": "unknown",
    "args": [],
    "message": "I couldn't understand that request. Please try rephrasing.",
}


# ---------------------------------------------------------------------------
# CommandInterpreter
# ---------------------------------------------------------------------------


class CommandInterpreter:
    """Translates a user utterance into a single structured command dict.

    Args:
        engine: An initialised :class:`AIEngine` instance.
    """

    def __init__(self, engine: AIEngine) -> None:
        self._engine = engine

    def interpret(self, user_input: str) -> dict[str, Any]:
        """Convert *user_input* into a command dict via the LLM.

        Args:
            user_input: The raw string from the user.

        Returns:
            A dict with at minimum ``"tool"`` and ``"args"`` keys.
        """
        user_input = user_input.strip()
        if not user_input:
            return _FALLBACK_COMMAND

        log.info("Interpreting: %r", user_input)

        try:
            raw = self._engine.generate(
                prompt=user_input,
                system=_SYSTEM_PROMPT,
                temperature=0.1,  # Low temperature for deterministic JSON
            )
        except AIEngineError as exc:
            log.error("AIEngine error during interpretation: %s", exc)
            return {
                "tool": "error",
                "args": [],
                "message": str(exc),
            }

        try:
            command = _extract_json(raw)
            log.info("Parsed command: %s", command)
            # Ensure minimum required keys
            command.setdefault("args", [])
            return command
        except ValueError:
            log.warning("Could not parse JSON from LLM output. Raw: %r", raw[:300])
            return {**_FALLBACK_COMMAND, "raw_response": raw}
