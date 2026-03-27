"""
infini_think.gui.chat_widget
==============================
Industry-standard chat interface for InfiniThink.

Features:
- Dual-theme system (Premium Light & Dark).
- High-end glassmorphism and backdrop effects.
- Modern "pill" style message bubbles with Markdown support.
- Stylized avatars and professional typography (Inter/Segoe UI).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QTextCursor, QIcon, QKeyEvent, QPainter, QBrush, QPen
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
    QGraphicsDropShadowEffect,
)

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Unified Theme System
# ---------------------------------------------------------------------------

THEMES = {
    "dark": {
        "bg":             "transparent",
        "sidebar_bg":     "rgba(13, 17, 23, 200)",
        "surface":        "rgba(22, 27, 34, 180)",
        "surface_solid":  "#161b22",
        "border":         "rgba(255, 255, 255, 0.08)",
        "accent":         "#58a6ff",
        "accent_dim":     "#1f6feb",
        "user_bubble":    "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f6feb, stop:1 #388bfd)",
        "ai_bubble":      "rgba(33, 38, 45, 220)",
        "user_text":      "#ffffff",
        "ai_text":        "#e6edf3",
        "timestamp":      "rgba(139, 148, 158, 150)",
        "input_bg":       "rgba(13, 17, 23, 150)",
        "welcome_bg":     "rgba(48, 54, 61, 120)",
        "bubble_border":  "rgba(255, 255, 255, 0.1)",
        "shadow":         "rgba(0, 0, 0, 0.4)",
    },
    "light": {
        "bg":             "transparent",
        "sidebar_bg":     "rgba(255, 255, 255, 245)",
        "surface":        "rgba(246, 248, 250, 200)",
        "surface_solid":  "#ffffff",
        "border":         "rgba(0, 0, 0, 0.08)",
        "accent":         "#0969da",
        "accent_dim":     "#03449d",
        "user_bubble":    "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0969da, stop:1 #218bff)",
        "ai_bubble":      "rgba(255, 255, 255, 255)",
        "user_text":      "#ffffff",
        "ai_text":        "#1f2328",
        "timestamp":      "rgba(87, 96, 106, 150)",
        "input_bg":       "rgba(255, 255, 255, 180)",
        "welcome_bg":     "rgba(234, 238, 242, 120)",
        "bubble_border":  "rgba(0, 0, 0, 0.1)",
        "shadow":         "rgba(0, 0, 0, 0.08)",
    }
}

class ThemeProvider:
    """Static helper to access current theme colors."""
    _current = "dark"

    @classmethod
    def set_theme(cls, theme: Literal["dark", "light"]):
        cls._current = theme

    @classmethod
    def colors(cls):
        return THEMES[cls._current]

# ---------------------------------------------------------------------------
# MessageBubble widget
# ---------------------------------------------------------------------------

class MessageBubble(QFrame):
    """Modern pill-style message bubble with markdown support."""

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
        c = ThemeProvider.colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Bubble frame
        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(6)

        # Message text (with Markdown support)
        text_label = QLabel()
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.TextFormat.MarkdownText)
        text_label.setText(content)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_label.setFont(QFont("Segoe UI Variable Display", 10.5))
        
        # Timestamp
        ts_label = QLabel(ts or "")
        ts_label.setFont(QFont("Segoe UIVariable Text", 8))
        ts_label.setStyleSheet(f"color: {c['timestamp']}; border: none; background: transparent;")

        bubble_layout.addWidget(text_label)
        if ts:
            bubble_layout.addWidget(ts_label)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        bubble.setGraphicsEffect(shadow)
        self._bubble = bubble
        self._text_label = text_label
        self._full_text = content

        if self._role == "user":
            bubble.setStyleSheet(
                f"QFrame#bubble {{ background: {c['user_bubble']}; "
                f"border-radius: 18px; border-bottom-right-radius: 4px; }}"
                f"QLabel {{ color: {c['user_text']}; background: transparent; }}"
            )
            ts_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(bubble)
            row.setContentsMargins(40, 0, 0, 0)
            layout.addLayout(row)
        elif self._role == "ai":
            bubble.setStyleSheet(
                f"QFrame#bubble {{ background: {c['ai_bubble']}; "
                f"border: 1px solid {c['bubble_border']}; "
                f"border-radius: 18px; border-top-left-radius: 4px; }}"
                f"QLabel {{ color: {c['ai_text']}; background: transparent; }}"
            )
            # AI avatar
            avatar = QLabel("🤖")
            avatar.setFixedSize(32, 32)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                f"background: {c['surface']}; border-radius: 16px; "
                f"border: 1px solid {c['border']}; font-size: 14px;"
            )
            row = QHBoxLayout()
            row.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignTop)
            row.addWidget(bubble, stretch=1)
            
            # Copy button (hidden by default, shown on hover/touch)
            self._copy_btn = QPushButton("📋")
            self._copy_btn.setFixedSize(24, 24)
            self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._copy_btn.setToolTip("Copy to clipboard")
            self._copy_btn.setStyleSheet(
                f"QPushButton {{ background: {c['surface']}; border-radius: 6px; font-size: 10px; border: 1px solid {c['border']}; color: {c['timestamp']}; }}"
                f"QPushButton:hover {{ color: {c['accent']}; border-color: {c['accent']}; }}"
            )
            self._copy_btn.clicked.connect(self._on_copy)
            row.addWidget(self._copy_btn, alignment=Qt.AlignmentFlag.AlignBottom)
            
            row.setContentsMargins(0, 0, 10, 0)
            layout.addLayout(row)
        else:
            bubble.setStyleSheet(
                f"QFrame#bubble {{ background: {c['welcome_bg']}; "
                f"border-radius: 16px; border: 1px solid {c['border']}; }}"
                f"QLabel {{ color: {c['ai_text']}; background: transparent; }}"
            )
            bubble.setMaximumWidth(300)
            ts_label.hide()
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(bubble)
            row.addStretch()
            layout.addLayout(row)

        self.setStyleSheet("background: transparent; border: none;")

    def _on_copy(self) -> None:
        """Copy bubble text to clipboard and show feedback."""
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(self._full_text)
        self._copy_btn.setText("✅")
        QTimer.singleShot(2000, lambda: self._copy_btn.setText("📋") if hasattr(self, "_copy_btn") else None)

    def append_text(self, text: str) -> None:
        """Dynamically append text (used for streaming)."""
        self._full_text += text
        self._text_label.setText(self._full_text)
        # Ensure scroll to bottom is handled by the parent

# ---------------------------------------------------------------------------
# MessageArea
# ---------------------------------------------------------------------------

class MessageArea(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.update_styles()

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(12)
        self._layout.addStretch()
        self.setWidget(self._container)

    def update_styles(self) -> None:
        c = ThemeProvider.colors()
        self.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 3px; min-height: 20px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )

    def add_message(self, role: str, content: str, ts: str | None = None) -> None:
        bubble = MessageBubble(role, content, ts)
        count = self._layout.count()
        self._layout.insertWidget(count - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

# ---------------------------------------------------------------------------
# InputBox
# ---------------------------------------------------------------------------

class InputBox(QTextEdit):
    returnPressed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMaximumHeight(120)
        self.setMinimumHeight(45)
        self.setPlaceholderText("Message InfiniThink…")
        self.setFont(QFont("Segoe UI Variable Text", 10.5))
        self.update_styles()

    def update_styles(self) -> None:
        c = ThemeProvider.colors()
        self.setStyleSheet(
            f"QTextEdit {{ background: {c['input_bg']}; color: {c['ai_text']}; "
            f"border: 1px solid {c['border']}; border-radius: 18px; "
            f"padding: 10px 14px; selection-background-color: {c['accent_dim']}; }}"
            f"QTextEdit:focus {{ border: 1.5px solid {c['accent']}; background: {c['surface']}; }}"
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
# ChatWidget
# ---------------------------------------------------------------------------

class ChatWidget(QWidget):
    message_submitted = Signal(str)
    mic_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mic_active: bool = False
        self._action_chips: list[QPushButton] = []
        self._build_ui()
        self._add_welcome_message()
        self._add_quick_actions()

    def _add_quick_actions(self) -> None:
        """Add interactive recommendation chips."""
        actions = [
            ("📝 Summarize", "Summarize the current project structure"),
            ("🔧 Fix Errors", "Check for and fix common linting issues"),
            ("📁 List Files", "List the top-level files in this project"),
            ("⚙️ System", "Check system resource usage"),
        ]
        for label, cmd in actions:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, c=cmd: self.message_submitted.emit(c))
            btn.setStyleSheet(
                f"QPushButton {{ background: {ThemeProvider.colors()['welcome_bg']}; "
                f"color: {ThemeProvider.colors()['ai_text']}; border-radius: 14px; "
                f"padding: 6px 12px; font-size: 10px; border: 1px solid {ThemeProvider.colors()['border']}; }}"
                f"QPushButton:hover {{ background: {ThemeProvider.colors()['surface']}; border-color: {ThemeProvider.colors()['accent']}; }}"
            )
            self._chips_layout.addWidget(btn)
            self._action_chips.append(btn)

    def _build_ui(self) -> None:
        c = ThemeProvider.colors()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Message area
        self._message_area = MessageArea()
        root.addWidget(self._message_area, stretch=1)

        # Input container
        self._input_container = QWidget()
        self._input_container.setObjectName("input_container")
        self.update_input_styles()
        
        input_layout = QVBoxLayout(self._input_container)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._input = InputBox()
        self._input.returnPressed.connect(self._on_send)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(45, 45)
        self._mic_btn.setFont(QFont("Segoe UI", 16))
        self._mic_btn.setToolTip("Voice Input")
        self._mic_btn.clicked.connect(self._on_mic_toggle)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedSize(75, 45)
        self._send_btn.setFont(QFont("Segoe UI Semibold", 10))
        self._send_btn.clicked.connect(self._on_send)

        input_row.addWidget(self._input, stretch=1)
        input_row.addWidget(self._mic_btn)
        input_row.addWidget(self._send_btn)
        
        input_layout.addLayout(input_row)

        # Chips row
        self._chips_container = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 4, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch()
        input_layout.addWidget(self._chips_container)

        root.addWidget(self._input_container)
        
        self.update_styles()

    def update_styles(self) -> None:
        c = ThemeProvider.colors()
        self.setStyleSheet(f"QWidget {{ background: {c['bg']}; border: none; }}")
        self._mic_btn.setStyleSheet(self._mic_style(self._mic_active))
        self._send_btn.setStyleSheet(
            f"QPushButton {{ background: {c['accent']}; color: white; "
            f"border-radius: 16px; border: none; }}"
            f"QPushButton:hover {{ background: {c['accent_dim']}; }}"
            f"QPushButton:disabled {{ background: {c['welcome_bg']}; color: {c['timestamp']}; }}"
        )
        self._message_area.update_styles()
        self._input.update_styles()
        self.update_input_styles()
        for btn in self._action_chips:
            btn.setStyleSheet(
                f"QPushButton {{ background: {c['welcome_bg']}; "
                f"color: {c['ai_text']}; border-radius: 14px; "
                f"padding: 6px 12px; font-size: 10px; border: 1px solid {c['border']}; }}"
                f"QPushButton:hover {{ background: {c['surface']}; border-color: {c['accent']}; }}"
            )

    def update_input_styles(self) -> None:
        c = ThemeProvider.colors()
        self._input_container.setStyleSheet(
            f"QWidget#input_container {{ background: {c['surface']}; "
            f"border-top: 1px solid {c['border']}; }}"
        )

    def _mic_style(self, active: bool) -> str:
        c = ThemeProvider.colors()
        bg = "#da3633" if active else c["surface"]
        color = "white" if active else c["ai_text"]
        border = "none" if active else f"1px solid {c['border']}"
        return (
            f"QPushButton {{ background: {bg}; color: {color}; border-radius: 16px; "
            f"border: {border}; font-size: 16px; }}"
            f"QPushButton:hover {{ background: {'#f85149' if active else c['welcome_bg']}; }}"
        )

    def _add_welcome_message(self) -> None:
        self._message_area.add_message(
            "system",
            "✨  Welcome to **InfiniThink Premium**\n"
            "An industry-standard AI proxy for your desktop.\n\n"
            "*Try asking for multi-step automation or document summaries.*",
        )

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text: return
        self._input.clear()
        self.add_user_message(text)
        self.message_submitted.emit(text)

    def _on_mic_toggle(self) -> None:
        self.set_mic_active(not self._mic_active)
        self.mic_toggled.emit(self._mic_active)

    def set_mic_active(self, active: bool) -> None:
        """Programmatically set the microphone button state."""
        self._mic_active = active
        self._mic_btn.setStyleSheet(self._mic_style(active=active))
        if active:
            self._mic_btn.setText("●") # Recording indicator
        else:
            self._mic_btn.setText("🎤")

    def switch_theme(self, theme: Literal["dark", "light"]) -> None:
        """Dynamically switch the UI theme colors."""
        ThemeProvider.set_theme(theme)
        self.update_styles()
        self._message_area.clear()
        self._add_welcome_message()

    def add_user_message(self, text: str) -> None:
        self._message_area.add_message("user", text)

    def add_ai_message(self, text: str) -> None:
        self._message_area.add_message("ai", text)

    def add_system_message(self, text: str) -> None:
        self._message_area.add_message("system", text)

    def update_last_ai_message(self, chunk: str) -> None:
        """Appends text to the very last AI message bubble."""
        container = self._message_area._container
        layout = self._message_area._layout
        # Find the last MessageBubble that is an AI role
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                bubble = item.widget()
                if bubble._role == "ai":
                    bubble.append_text(chunk)
                    self._message_area._scroll_to_bottom()
                    break

    def set_thinking(self, thinking: bool) -> None:
        self._send_btn.setEnabled(not thinking)
        self._send_btn.setText("Thinking…" if thinking else "Send")
        self._input.setEnabled(not thinking)
