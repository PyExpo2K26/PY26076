"""
infini_think.gui.chat_widget
==============================
The core chat interface component for InfiniThink.

Provides a scrollable message history with styled user/AI bubbles,
an input text box, a Send button, and a microphone button.

Signals
-------
- ``message_submitted(str)`` — emitted when the user sends a message
- ``mic_toggled(bool)``      — emitted when the mic button is toggled
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QTextCursor, QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QTextEdit,
    QPushButton,
    QSizePolicy,
    QFrame,
    QApplication,
)

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_DARK = {
    "bg":           "#0d1117",
    "surface":      "#161b22",
    "surface2":     "#21262d",
    "border":       "#30363d",
    "accent":       "#58a6ff",
    "accent_dim":   "#1f6feb",
    "user_bubble":  "#1f6feb",
    "ai_bubble":    "#21262d",
    "user_text":    "#ffffff",
    "ai_text":      "#e6edf3",
    "timestamp":    "#8b949e",
    "input_bg":     "#0d1117",
    "send_btn":     "#1f6feb",
    "send_hover":   "#388bfd",
    "mic_inactive": "#21262d",
    "mic_active":   "#da3633",
    "mic_hover":    "#f85149",
    "placeholder":  "#484f58",
    "welcome":      "#3d444d",
}


# ---------------------------------------------------------------------------
# MessageBubble widget
# ---------------------------------------------------------------------------

class MessageBubble(QFrame):
    """A single chat message bubble.

    Args:
        role:    ``"user"`` or ``"ai"``
        content: The message text.
        ts:      Optional timestamp string.
    """

    def __init__(
        self,
        role: Literal["user", "ai", "system"],
        content: str,
        ts: str | None = None,
    ) -> None:
        super().__init__()
        self._role = role
        self._build_ui(content, ts or datetime.now().strftime("%H:%M"))

    def _build_ui(self, content: str, ts: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)

        # Bubble frame
        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(4)

        # Message text
        text_label = QLabel(content)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_label.setFont(QFont("Segoe UI", 10))

        # Timestamp
        ts_label = QLabel(ts)
        ts_label.setFont(QFont("Segoe UI", 8))
        ts_label.setStyleSheet(f"color: {_DARK['timestamp']};")

        bubble_layout.addWidget(text_label)
        bubble_layout.addWidget(ts_label)

        if self._role == "user":
            bubble.setStyleSheet(
                f"QFrame#bubble {{ background: {_DARK['user_bubble']}; "
                f"border-radius: 16px 4px 16px 16px; }}"
                f"QLabel {{ color: {_DARK['user_text']}; }}"
            )
            ts_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(bubble)
            row.setContentsMargins(60, 0, 0, 0)
            layout.addLayout(row)
        elif self._role == "ai":
            bubble.setStyleSheet(
                f"QFrame#bubble {{ background: {_DARK['ai_bubble']}; "
                f"border: 1px solid {_DARK['border']}; "
                f"border-radius: 4px 16px 16px 16px; }}"
                f"QLabel {{ color: {_DARK['ai_text']}; }}"
            )
            # AI avatar dot
            avatar = QLabel("🤖")
            avatar.setFixedSize(32, 32)
            avatar.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            avatar.setStyleSheet(
                f"background: {_DARK['surface2']}; border-radius: 16px; "
                "font-size: 14px; padding: 4px;"
            )
            row = QHBoxLayout()
            row.addWidget(avatar)
            row.addWidget(bubble)
            row.addStretch()
            row.setContentsMargins(0, 0, 60, 0)
            layout.addLayout(row)
        else:
            # System message (centered)
            bubble.setStyleSheet(
                f"QFrame#bubble {{ background: {_DARK['welcome']}; "
                f"border-radius: 8px; border: 1px dashed {_DARK['border']}; }}"
                f"QLabel {{ color: {_DARK['timestamp']}; }}"
            )
            ts_label.hide()
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(bubble)
            row.addStretch()
            layout.addLayout(row)

        self.setStyleSheet("background: transparent;")


# ---------------------------------------------------------------------------
# MessageArea — scrollable container for bubbles
# ---------------------------------------------------------------------------

class MessageArea(QScrollArea):
    """Scrollable area containing all message bubbles."""

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet(
            f"QScrollArea {{ background: {_DARK['bg']}; border: none; }}"
            f"QScrollBar:vertical {{ background: {_DARK['surface']}; width: 6px; }}"
            f"QScrollBar::handle:vertical {{ background: {_DARK['border']}; border-radius: 3px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )

        self._container = QWidget()
        self._container.setStyleSheet(f"background: {_DARK['bg']};")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)
        self._layout.addStretch()
        self.setWidget(self._container)

    def add_message(
        self,
        role: Literal["user", "ai", "system"],
        content: str,
        ts: str | None = None,
    ) -> None:
        """Append a new message bubble and scroll to bottom."""
        bubble = MessageBubble(role, content, ts)
        # Insert before the trailing stretch
        count = self._layout.count()
        self._layout.insertWidget(count - 1, bubble)
        # Scroll to bottom on next event loop tick
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self) -> None:
        """Remove all messages."""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ---------------------------------------------------------------------------
# InputBox — multi-line input with Enter-to-send
# ---------------------------------------------------------------------------

class InputBox(QTextEdit):
    """Text input that emits ``returnPressed`` on Enter (Shift+Enter = newline)."""

    returnPressed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMaximumHeight(100)
        self.setMinimumHeight(44)
        self.setPlaceholderText("Message InfiniThink…")
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(
            f"QTextEdit {{ background: {_DARK['input_bg']}; color: {_DARK['ai_text']}; "
            f"border: 1px solid {_DARK['border']}; border-radius: 12px; "
            f"padding: 10px 14px; selection-background-color: {_DARK['accent_dim']}; }}"
            f"QTextEdit:focus {{ border: 1px solid {_DARK['accent']}; }}"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.returnPressed.emit()
        else:
            super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# ChatWidget — the full chat panel
# ---------------------------------------------------------------------------

class ChatWidget(QWidget):
    """Full chat interface widget.

    Signals:
        message_submitted (str): Emitted when the user submits a message.
        mic_toggled (bool):      Emitted when the mic button is pressed.
    """

    message_submitted = Signal(str)
    mic_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mic_active: bool = False
        self._build_ui()
        self._add_welcome_message()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Message area
        self._message_area = MessageArea()
        root.addWidget(self._message_area, stretch=1)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_DARK['border']};")
        root.addWidget(sep)

        # Input row
        input_row = QHBoxLayout()
        input_row.setContentsMargins(12, 8, 12, 12)
        input_row.setSpacing(8)

        self._input = InputBox()
        self._input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedSize(80, 44)
        self._send_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._send_btn.setStyleSheet(
            f"QPushButton {{ background: {_DARK['send_btn']}; color: white; "
            f"border-radius: 12px; border: none; }}"
            f"QPushButton:hover {{ background: {_DARK['send_hover']}; }}"
            f"QPushButton:pressed {{ background: {_DARK['accent_dim']}; }}"
        )
        self._send_btn.clicked.connect(self._on_send)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(44, 44)
        self._mic_btn.setFont(QFont("Segoe UI", 16))
        self._mic_btn.setToolTip("Start/stop voice input")
        self._mic_btn.setStyleSheet(self._mic_style(active=False))
        self._mic_btn.clicked.connect(self._on_mic_toggle)

        input_row.addWidget(self._input, stretch=1)
        input_row.addWidget(self._mic_btn)
        input_row.addWidget(self._send_btn)

        input_container = QWidget()
        input_container.setStyleSheet(f"background: {_DARK['surface']};")
        input_container.setLayout(input_row)
        root.addWidget(input_container)

        self.setStyleSheet(f"QWidget {{ background: {_DARK['bg']}; }}")

    def _mic_style(self, active: bool) -> str:
        bg = _DARK["mic_active"] if active else _DARK["mic_inactive"]
        hover = _DARK["mic_hover"] if active else _DARK["surface2"]
        return (
            f"QPushButton {{ background: {bg}; border-radius: 12px; border: none; }}"
            f"QPushButton:hover {{ background: {hover}; }}"
        )

    def _add_welcome_message(self) -> None:
        self._message_area.add_message(
            "system",
            "👋  Welcome to InfiniThink! Type a command or press 🎤 to speak.\n"
            'Try: "open chrome", "organize my downloads", "prepare my research workspace"',
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self.add_user_message(text)
        self.message_submitted.emit(text)

    def _on_mic_toggle(self) -> None:
        self._mic_active = not self._mic_active
        self._mic_btn.setStyleSheet(self._mic_style(active=self._mic_active))
        self.mic_toggled.emit(self._mic_active)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def add_user_message(self, text: str) -> None:
        """Display a user message bubble."""
        self._message_area.add_message("user", text)

    def add_ai_message(self, text: str) -> None:
        """Display an AI response bubble."""
        self._message_area.add_message("ai", text)

    def add_system_message(self, text: str) -> None:
        """Display a system notification bubble."""
        self._message_area.add_message("system", text)

    def set_input_text(self, text: str) -> None:
        """Pre-fill the input box (e.g. from voice recognition)."""
        self._input.setPlainText(text)
        self._input.moveCursor(QTextCursor.MoveOperation.End)

    def set_mic_active(self, active: bool) -> None:
        """Synchronise the mic button visual state from outside."""
        self._mic_active = active
        self._mic_btn.setStyleSheet(self._mic_style(active=active))

    def set_thinking(self, thinking: bool) -> None:
        """Disable/enable send controls while the AI is processing."""
        self._send_btn.setEnabled(not thinking)
        self._send_btn.setText("…" if thinking else "Send")
        self._input.setEnabled(not thinking)
