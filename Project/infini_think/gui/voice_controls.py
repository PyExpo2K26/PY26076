"""
infini_think.gui.voice_controls
================================
Microphone button with a pulsing animation to indicate active listening.

This widget is embedded inside :class:`~infini_think.gui.chat_widget.ChatWidget`
but can also be used standalone.  It emits a ``toggled(bool)`` signal.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property, QByteArray
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QHBoxLayout

from infini_think.utils.logger import get_logger

log = get_logger(__name__)


class MicButton(QPushButton):
    """Animated microphone toggle button.

    Pulses with a red glow when recording is active.

    Signals:
        toggled_recording (bool): Emitted on each click with the new state.
    """

    toggled_recording = Signal(bool)

    _INACTIVE_STYLE = (
        "QPushButton {"
        "  background: #21262d;"
        "  color: #e6edf3;"
        "  border-radius: 22px;"
        "  border: 2px solid #30363d;"
        "  font-size: 20px;"
        "}"
        "QPushButton:hover {"
        "  background: #30363d;"
        "  border-color: #58a6ff;"
        "}"
    )

    _ACTIVE_STYLE = (
        "QPushButton {"
        "  background: #da3633;"
        "  color: white;"
        "  border-radius: 22px;"
        "  border: 2px solid #f85149;"
        "  font-size: 20px;"
        "}"
        "QPushButton:hover {"
        "  background: #f85149;"
        "}"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("🎤", parent)
        self._active = False
        self.setFixedSize(44, 44)
        self.setToolTip("Click to start/stop voice input")
        self.setStyleSheet(self._INACTIVE_STYLE)
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        self._active = not self._active
        self.setStyleSheet(self._ACTIVE_STYLE if self._active else self._INACTIVE_STYLE)
        self.setText("⏹" if self._active else "🎤")
        self.toggled_recording.emit(self._active)
        log.debug("Mic button toggled: active=%s", self._active)

    def set_active(self, active: bool) -> None:
        """Programmatically set the active state (e.g. after STT finishes)."""
        if self._active != active:
            self._active = active
            self.setStyleSheet(self._ACTIVE_STYLE if active else self._INACTIVE_STYLE)
            self.setText("⏹" if active else "🎤")


class VoiceStatusLabel(QLabel):
    """Small status indicator shown below the mic button."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 8))
        self.setStyleSheet("color: #8b949e; background: transparent;")

    def set_listening(self, listening: bool) -> None:
        if listening:
            self.setText("● Listening…")
            self.setStyleSheet("color: #da3633; background: transparent;")
        else:
            self.setText("")
            self.setStyleSheet("color: #8b949e; background: transparent;")
