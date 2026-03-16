"""
infini_think.core.planner
==========================
Breaks complex, multi-step natural-language requests into an ordered list
of discrete tool commands by prompting the local LLM.

For simple single-action requests the planner delegates directly to
:class:`CommandInterpreter`.  For compound requests (e.g. "prepare my
research workspace") it produces an ordered plan list.

Output format::

    [
        {"tool": "open_app", "args": ["chrome"]},
        {"tool": "open_app", "args": ["notion"]},
        {"tool": "open_folder", "args": ["research"]},
    ]
"""

from __future__ import annotations

import json
import re
from typing import Any

from infini_think.core.ai_engine import AIEngine, AIEngineError
from infini_think.core.command_interpreter import CommandInterpreter
from infini_think.config.settings import settings
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PLANNER_SYSTEM = """You are InfiniThink's task planner.

Given a user request, output a JSON array of tool commands to fulfill it.
Each element must have "tool" and "args" keys.

Available tools:
- open_app(app_name: str)
- open_folder(path: str)
- open_vscode(path: str = "")
- search_files(query: str)
- create_folder(name: str)
- organize_downloads()
- run_terminal_command(command: str)
- get_system_info()

Rules:
1. Reply ONLY with a JSON array. No explanation. No markdown. No code fence.
2. Order actions logically (e.g. create folder before placing files inside).
3. Maximum {max_steps} actions.
4. For simple requests with a single action output an array with one element.

Examples:
  "prepare my research workspace"
  → [{"tool":"open_app","args":["chrome"]},{"tool":"open_app","args":["notion"]},{"tool":"open_folder","args":["research"]}]

  "open notepad"
  → [{"tool":"open_app","args":["notepad"]}]

  "organize downloads and open explorer"
  → [{"tool":"organize_downloads","args":[]},{"tool":"open_folder","args":["downloads"]}]
""".format(max_steps=settings.max_plan_steps)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SINGLE_STEP_KEYWORDS = re.compile(
    r"^(open|launch|start|run|show|display|search|find|create|make|shutdown|restart)\s",
    re.IGNORECASE,
)


def _looks_complex(text: str) -> bool:
    """Heuristic: return True if the request is likely multi-step."""
    conjunctions = ("and", "then", "after that", "also", "plus", "next")
    lower = text.lower()
    return any(f" {c} " in lower for c in conjunctions) or (
        lower.startswith("prepare ")
        or lower.startswith("set up ")
        or lower.startswith("setup ")
        or lower.startswith("organize ")
    )


def _extract_plan(text: str) -> list[dict[str, Any]]:
    """Extract and parse a JSON array from *text*.

    Args:
        text: Raw LLM response.

    Returns:
        List of command dicts.

    Raises:
        ValueError: If no valid JSON array is found.
    """
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

    # Try direct parse first
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting [...] block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON array in: {text[:200]!r}")


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class TaskPlanner:
    """Produces an ordered execution plan from a user utterance.

    For simple, single-action requests the interpreter is used directly.
    For multi-step requests the LLM is prompted with a planning system prompt.

    Args:
        engine: An initialised :class:`AIEngine`.
        interpreter: An initialised :class:`CommandInterpreter`.
    """

    def __init__(self, engine: AIEngine, interpreter: CommandInterpreter) -> None:
        self._engine = engine
        self._interpreter = interpreter

    def plan(self, user_input: str) -> list[dict[str, Any]]:
        """Convert *user_input* into an ordered list of tool commands.

        Args:
            user_input: The raw user utterance.

        Returns:
            A list of ``{"tool": ..., "args": [...]}`` dicts, at minimum one.
        """
        user_input = user_input.strip()

        # Fast-path: single-action requests
        if not _looks_complex(user_input):
            log.debug("Simple request — using interpreter directly")
            command = self._interpreter.interpret(user_input)
            return [command]

        log.info("Complex request detected — invoking planner LLM")
        try:
            raw = self._engine.generate(
                prompt=user_input,
                system=_PLANNER_SYSTEM,
                temperature=0.2,
            )
        except AIEngineError as exc:
            log.error("Planner LLM error: %s", exc)
            # Gracefully fall back to interpreter for a single best-effort command
            return [self._interpreter.interpret(user_input)]

        try:
            plan = _extract_plan(raw)
            # Clamp to max steps
            plan = plan[: settings.max_plan_steps]
            # Ensure each step has the right shape
            for step in plan:
                step.setdefault("args", [])
            log.info("Plan produced: %d step(s)", len(plan))
            return plan
        except ValueError:
            log.warning("Could not parse plan. Falling back to interpreter.")
            return [self._interpreter.interpret(user_input)]
