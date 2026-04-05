"""
infini_think.utils.logger
=========================
Centralised logging configuration for InfiniThink.

Usage::

    from infini_think.utils.logger import get_logger

    log = get_logger(__name__)
    log.info("Hello from InfiniThink")
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from infini_think.config.settings import settings

# ---------------------------------------------------------------------------
# ANSI colour codes for terminal output
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"

_LEVEL_COLOURS: dict[str, str] = {
    "DEBUG":    "\033[36m",   # Cyan
    "INFO":     "\033[32m",   # Green
    "WARNING":  "\033[33m",   # Yellow
    "ERROR":    "\033[31m",   # Red
    "CRITICAL": "\033[35m",   # Magenta
}


class _ColourFormatter(logging.Formatter):
    """Custom formatter that adds ANSI colours to console log records."""

    _FMT = "%(asctime)s  {colour}{bold}%(levelname)-8s{reset}  %(name)s  %(message)s"
    _DATE_FMT = "%H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, "")
        fmt = self._FMT.format(colour=colour, bold=_BOLD, reset=_RESET)
        formatter = logging.Formatter(fmt, datefmt=self._DATE_FMT)
        return formatter.format(record)


class _PlainFormatter(logging.Formatter):
    """Plain formatter for file output (no ANSI sequences)."""

    _FMT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    _DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATE_FMT)


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_configured: bool = False
_root_logger_name: str = "infini_think"


def _configure() -> None:
    """One-time setup of the root InfiniThink logger (idempotent)."""
    global _configured
    if _configured:
        return

    root = logging.getLogger(_root_logger_name)
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)

    # --- Console handler ---------------------------------------------------
    if sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        # Only colourise if the terminal supports it
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            console_handler.setFormatter(_ColourFormatter())
        else:
            console_handler.setFormatter(_PlainFormatter())
        root.addHandler(console_handler)

    # --- Rotating file handler ---------------------------------------------
    if settings.log_to_file:
        log_path: Path = settings.log_dir / "infini_think.log"
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(_PlainFormatter())
        root.addHandler(file_handler)

    # Prevent propagation to the root Python logger (avoids duplicate lines)
    root.propagate = False

    _configured = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``infini_think`` namespace.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` configured with colour console + file output.
    """
    _configure()
    # Strip any leading package name so module paths stay relative
    if name.startswith("infini_think."):
        short_name = name
    else:
        short_name = f"{_root_logger_name}.{name}"
    return logging.getLogger(short_name)
