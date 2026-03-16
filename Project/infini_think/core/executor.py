"""
infini_think.core.executor
============================
Dispatches structured command dicts to the correct tool functions and
collects their results.

The executor uses a **tool registry** pattern: tool functions are registered
by name so new tools can be added without touching this file.

Usage::

    from infini_think.core.executor import Executor

    executor = Executor()
    result = executor.execute({"tool": "open_app", "args": ["chrome"]})
"""

from __future__ import annotations

import time
import traceback
from typing import Any, Callable

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass (plain dict for simplicity)
# ---------------------------------------------------------------------------

ExecutionResult = dict[str, Any]
"""
Keys:
  - ``success`` (bool)
  - ``tool``    (str)
  - ``args``    (list)
  - ``output``  (str)     — human-readable result message
  - ``elapsed`` (float)   — wall-clock seconds
  - ``error``   (str | None)
"""


def _make_result(
    tool: str,
    args: list,
    success: bool,
    output: str,
    elapsed: float,
    error: str | None = None,
) -> ExecutionResult:
    return {
        "success": success,
        "tool": tool,
        "args": args,
        "output": output,
        "elapsed": round(elapsed, 3),
        "error": error,
    }


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class Executor:
    """Dispatches tool commands and returns structured results.

    Tool functions are imported lazily from the ``infini_think.tools``
    sub-package so the executor itself is free of OS-specific imports.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Callable[..., str]] = {}
        self._register_default_tools()

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def register(self, name: str, func: Callable[..., str]) -> None:
        """Register a callable under *name* in the tool registry.

        Args:
            name: The tool name used in command dicts (e.g. ``"open_app"``).
            func: A callable that accepts positional args and returns a string.
        """
        self._registry[name] = func
        log.debug("Registered tool: %s", name)

    def _register_default_tools(self) -> None:
        """Import and register all built-in tools."""
        # Import here to avoid circular imports at module load time
        from infini_think.tools.app_tools import open_app, open_vscode
        from infini_think.tools.file_tools import (
            organize_downloads,
            create_folder,
            search_files,
            open_folder,
            open_file,
        )
        from infini_think.tools.system_tools import (
            run_terminal_command,
            shutdown_pc,
            get_system_info,
        )

        self.register("open_app", open_app)
        self.register("open_vscode", open_vscode)
        self.register("organize_downloads", organize_downloads)
        self.register("create_folder", create_folder)
        self.register("search_files", search_files)
        self.register("open_folder", open_folder)
        self.register("open_file", open_file)
        self.register("run_terminal_command", run_terminal_command)
        self.register("shutdown_pc", shutdown_pc)
        self.register("get_system_info", get_system_info)
        
        # Built-in lightweight conversational handler
        self.register("talk", lambda msg: msg)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, command: dict[str, Any]) -> ExecutionResult:
        """Execute a single command dict.

        Args:
            command: A dict with ``"tool"`` and ``"args"`` keys.

        Returns:
            An :obj:`ExecutionResult` dict.
        """
        tool_name: str = command.get("tool", "unknown")
        args: list = command.get("args", [])

        log.info("Executing tool=%r args=%r", tool_name, args)
        start = time.monotonic()

        # Handle special/unknown tools
        if tool_name in ("unknown", "error"):
            msg = command.get("message", "I could not understand that request.")
            return _make_result(tool_name, args, False, msg, 0.0, msg)

        func = self._registry.get(tool_name)
        if func is None:
            msg = f"Unknown tool: '{tool_name}'. No handler registered."
            log.warning(msg)
            return _make_result(tool_name, args, False, msg, 0.0, msg)

        try:
            output: str = func(*args)
            elapsed = time.monotonic() - start
            log.info("Tool '%s' succeeded in %.3fs", tool_name, elapsed)
            return _make_result(tool_name, args, True, output, elapsed)
        except TypeError as exc:
            # Wrong number / type of arguments
            elapsed = time.monotonic() - start
            msg = f"Tool '{tool_name}' received wrong arguments: {exc}"
            log.error(msg)
            return _make_result(tool_name, args, False, msg, elapsed, str(exc))
        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - start
            msg = f"Tool '{tool_name}' raised an error: {exc}"
            log.error("%s\n%s", msg, traceback.format_exc())
            return _make_result(tool_name, args, False, msg, elapsed, str(exc))

    def execute_plan(self, plan: list[dict[str, Any]]) -> list[ExecutionResult]:
        """Execute an ordered list of commands, stopping on critical failure.

        Args:
            plan: List of command dicts produced by :class:`TaskPlanner`.

        Returns:
            List of :obj:`ExecutionResult` dicts, one per step.
        """
        results: list[ExecutionResult] = []
        for i, command in enumerate(plan, start=1):
            log.info("Plan step %d/%d", i, len(plan))
            result = self.execute(command)
            results.append(result)
            # Stop early if a step critically fails (tool not found / bad args)
            if not result["success"] and result["error"] and "shutdown" in command.get("tool", ""):
                log.warning("Halting plan after step %d due to failure", i)
                break
        return results
