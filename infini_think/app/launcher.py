"""
infini_think.app.launcher
============================
Application entry point for InfiniThink.

This module is registered as the ``infini-think`` console script in
``pyproject.toml``.  It:

1. Parses CLI flags (``--cli``, ``--voice``, ``--model``, ``--verbose``).
2. Validates the Ollama connection (with a friendly warning if absent).
3. Launches the appropriate interface (GUI by default).

Usage::

    infini-think                  # Launches GUI
    infini-think --cli            # Launches CLI REPL
    infini-think --voice          # Launches voice-only interface
    infini-think --model mistral  # Override the Ollama model
"""

from __future__ import annotations

import argparse
import sys

from infini_think.utils.logger import get_logger
from infini_think.config.settings import settings

log = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="infini-think",
        description="⚡ InfiniThink — Local AI Desktop Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  infini-think              # Launch GUI (default)\n"
            "  infini-think --cli        # Interactive CLI REPL\n"
            "  infini-think --voice      # Voice-only interface\n"
            "  infini-think --model llama3.1\n"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cli",   action="store_true", help="Launch CLI REPL instead of GUI")
    mode.add_argument("--voice", action="store_true", help="Launch voice-only interface")

    parser.add_argument(
        "--model",
        metavar="NAME",
        default=None,
        help=f"Ollama model to use (default: {settings.ollama_model})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose / debug output",
    )
    return parser.parse_args()


def _check_ollama(warn_only: bool = True) -> bool:
    """Check Ollama availability and print a user-friendly warning."""
    from infini_think.core.ai_engine import AIEngine
    engine = AIEngine()
    ok = engine.is_available()
    if not ok:
        msg = (
            "\n⚠  Warning: Ollama is not running or not installed.\n"
            "   InfiniThink requires a local Ollama server.\n"
            "   Install:  https://ollama.com\n"
            f"  Start:   ollama serve\n"
            f"  Model:   ollama pull {settings.ollama_model}\n"
        )
        print(msg, file=sys.stderr)
        if not warn_only:
            sys.exit(1)
    return ok


def _launch_gui() -> None:
    """Start the PySide6 GUI application."""
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont
        from infini_think.gui.main_window import MainWindow
        from infini_think.gui.agent_bubble import AgentBubble
        from pathlib import Path
    except ImportError as exc:
        print(
            f"❌  PySide6 is not installed: {exc}\n"
            "   Install with: pip install PySide6",
            file=sys.stderr,
        )
        sys.exit(1)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("InfiniThink")
    app.setOrganizationName("InfiniThink")

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply dark palette for native widgets
    _apply_dark_palette(app)

    # Path to the agent icon
    project_root = Path(__file__).parent.parent.parent
    icon_path = str(project_root / "assets" / "infini_think_icon.png")

    sidebar = MainWindow()
    bubble = AgentBubble(icon_path)
    
    # Connect bubble click to toggle sidebar
    bubble.clicked.connect(sidebar.toggle_visibility)
    
    # Connect AI activity signals for interactivity
    sidebar.ai_thinking_started.connect(lambda: bubble.set_thinking(True))
    sidebar.ai_thinking_finished.connect(lambda: bubble.set_thinking(False))
    sidebar.ai_status_update.connect(bubble.set_status)
    
    # Handle file drops on the agent bubble
    bubble.file_dropped.connect(lambda path: sidebar._on_message_submitted(f"Summarize this file: {path}"))
    
    bubble.show()
    # sidebar is hidden by default
    
    log.info("Agent Bubble launched")
    sys.exit(app.exec())


def _apply_dark_palette(app) -> None:
    """Apply a dark colour palette to the QApplication."""
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Base,            QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Text,            QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Button,          QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link,            QColor("#58a6ff"))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def _launch_cli(verbose: bool = False) -> None:
    """Start the interactive CLI REPL."""
    from infini_think.interfaces.cli_interface import CLIInterface
    CLIInterface(verbose=verbose).run()


def _launch_voice() -> None:
    """Start the voice-only interface."""
    from infini_think.interfaces.voice_interface import VoiceInterface
    VoiceInterface().run()


def main() -> None:
    """Primary entry point registered in pyproject.toml."""
    args = _parse_args()

    # Override model if flag provided
    if args.model:
        settings.ollama_model = args.model
        log.info("Model overridden to: %s", args.model)

    # Override log level if verbose
    if args.verbose:
        import logging
        logging.getLogger("infini_think").setLevel(logging.DEBUG)

    log.info("InfiniThink starting — mode=%s", "cli" if args.cli else "voice" if args.voice else "gui")

    if args.cli:
        _check_ollama(warn_only=True)
        _launch_cli(verbose=args.verbose)
    elif args.voice:
        _check_ollama(warn_only=True)
        _launch_voice()
    else:
        # GUI is the default — Ollama check happens inside MainWindow
        _launch_gui()


if __name__ == "__main__":
    main()
