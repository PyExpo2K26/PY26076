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

_SYSTEM_PROMPT = """You are InfiniThink, a desktop AI assistant.
Your job is to convert a user's natural-language request into a JSON command.

Available tools:
- open_app(app_name: str)           — Launch an application by name
- open_folder(path: str)            — Open a folder in the file explorer
- open_file(path: str)              — Open a file with the default system application
- open_vscode(path: str = "")       — Open VS Code (optionally at a path)
- search_files(query: str)          — Search the filesystem for files matching the query
- create_folder(name: str)          — Create a new folder
- organize_downloads()              — Sort the Downloads folder into subfolders by type
- run_terminal_command(command: str)— Run a shell command
- shutdown_pc()                     — Shut down the computer
- get_system_info()                 — Return basic system information
- talk(message: str)                — Conversational reply to the user (e.g. answering a question or greeting)
- unknown()                         — Use this ONLY when the request makes no sense whatsoever

Rules:
1. Reply ONLY with a single JSON object. No explanation, no markdown, no code fence.
2. JSON format: {"tool": "<tool_name>", "args": [<arg1>, <arg2>, ...]}
3. If no arguments are needed, use an empty list: []
4. Choose the MOST appropriate tool. If unsure, use "unknown".
5. Never include comments in the JSON.

Examples:
  User: open chrome             → {"tool": "open_app", "args": ["chrome"]}
  User: open my downloads folder→ {"tool": "open_folder", "args": ["downloads"]}
  User: open desktop/report.pdf → {"tool": "open_file", "args": ["desktop/report.pdf"]}
  User: create a folder named Work → {"tool": "create_folder", "args": ["Work"]}
  User: what is my CPU model    → {"tool": "get_system_info", "args": []}
  User: how are you doing today → {"tool": "talk", "args": ["I am functioning normally. How can I assist you?"]}
  User: open vscode             → {"tool": "open_vscode", "args": []}
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
