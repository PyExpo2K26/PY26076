"""
infini_think.interfaces.cli_interface
========================================
Interactive command-line REPL for InfiniThink.

Provides a rich terminal interface for development, debugging, or use on
headless systems.  Same AI pipeline as the GUI.

Usage::

    python -m infini_think.interfaces.cli_interface
    # or if installed:
    infini-think --cli
"""

from __future__ import annotations

import sys

from infini_think.config.settings import settings
from infini_think.core.ai_engine import AIEngine
from infini_think.core.command_interpreter import CommandInterpreter
from infini_think.core.planner import TaskPlanner
from infini_think.core.executor import Executor
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# ANSI helpers (no external deps)
# ---------------------------------------------------------------------------

_R = "\033[0m"           # reset
_BOLD = "\033[1m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"
_DIM = "\033[2m"


def _c(text: str, *codes: str) -> str:
    """Apply ANSI colour codes (only when stdout is a TTY)."""
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + _R


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

_BANNER = """
╔══════════════════════════════════════════════════════╗
║          ⚡  InfiniThink  –  Local AI Agent          ║
║         Type 'help' for commands, 'quit' to exit     ║
╚══════════════════════════════════════════════════════╝
"""

_HELP = """
Available commands:
  <any natural language>   — Ask InfiniThink to do something
  help                     — Show this help message
  status                   — Check Ollama connection status
  models                   — List available Ollama models
  clear                    — Clear the terminal screen
  quit / exit / q          — Exit InfiniThink

Examples:
  open chrome
  organize my downloads
  create a folder called Projects
  prepare my research workspace
  what's my system info
"""

_SPECIAL = {"help", "quit", "exit", "q", "status", "models", "clear"}


class CLIInterface:
    """Interactive REPL that uses the full InfiniThink AI pipeline.

    Args:
        verbose: If True, print extra debug information such as the raw plan.
    """

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose
        self._engine = AIEngine()
        self._interpreter = CommandInterpreter(self._engine)
        self._planner = TaskPlanner(self._engine, self._interpreter)
        self._executor = Executor()

    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the interactive REPL loop."""
        print(_c(_BANNER, _CYAN, _BOLD))

        # Ollama status
        if self._engine.is_available():
            print(_c(f"✓  Ollama connected  |  Model: {settings.ollama_model}\n", _GREEN))
        else:
            print(_c(
                "⚠  Ollama is not running. Start with: ollama serve\n"
                f"   Then pull model: ollama pull {settings.ollama_model}\n",
                _YELLOW,
            ))

        print(_c("Type 'help' for usage.\n", _DIM))

        while True:
            try:
                raw = input(_c("You ▶ ", _CYAN, _BOLD)).strip()
            except (KeyboardInterrupt, EOFError):
                print(_c("\n\nBye! 👋", _DIM))
                break

            if not raw:
                continue

            lower = raw.lower()

            # Special commands
            if lower in ("quit", "exit", "q"):
                print(_c("Goodbye! 👋", _DIM))
                break
            elif lower == "help":
                print(_c(_HELP, _DIM))
                continue
            elif lower == "clear":
                print("\033[2J\033[H", end="")
                continue
            elif lower == "status":
                ok = self._engine.is_available()
                status = _c("● Connected", _GREEN) if ok else _c("● Offline", _RED)
                print(f"Ollama: {status}  |  Model: {settings.ollama_model}\n")
                continue
            elif lower == "models":
                models = self._engine.list_models()
                if models:
                    print(_c("Available models:", _BLUE))
                    for m in models:
                        prefix = "  *" if m.startswith(settings.ollama_model) else "   "
                        print(f"{prefix} {m}")
                else:
                    print(_c("  No models found (is Ollama running?)", _YELLOW))
                print()
                continue

            # AI pipeline
            print(_c("  Thinking…", _DIM), end="\r")
            try:
                plan = self._planner.plan(raw)

                if self._verbose:
                    print(_c(f"  Plan: {plan}", _DIM))

                results = self._executor.execute_plan(plan)

                for result in results:
                    icon = _c("✅", _GREEN) if result["success"] else _c("❌", _RED)
                    output = result.get("output", "")
                    elapsed = result.get("elapsed", 0.0)
                    print(f"\n{icon}  {output}")
                    if self._verbose:
                        print(_c(f"   ↳ tool={result['tool']}  elapsed={elapsed:.3f}s", _DIM))

            except Exception as exc:  # noqa: BLE001
                print(_c(f"❌  Error: {exc}", _RED))

            print()
