"""
infini_think.gui.agent_bubble
===============================
A small, floating, frameless window representing the AI agent.

Features:
- Frameless and transparent background.
- Floating always-on-top.
- Draggable via mouse interaction.
- Clickable to toggle the main sidebar.
- Premium neon glow and thinking pulse animations.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, Signal, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QPauseAnimation
from PySide6.QtGui import QPixmap, QMouseEvent, QEnterEvent, QColor
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

class AgentBubble(QWidget):
    """The floating agent 'bubble' icon with premium animations."""
    
    clicked = Signal()

    def __init__(self, icon_path: str) -> None:
        super().__init__()
        self._icon_path = icon_path
        self._dragging = False
        self._drag_position = QPoint()
        
        self._init_ui()
        log.info("AgentBubble premium initialised.")

    def _init_ui(self) -> None:
        # Window configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(100, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # We use a stylized emoji/icon for the 'Proxy' feel
        # 🔮 or 🤖 or ⚡. Let's go with 🔮 (Orbital AI)
        self._icon_label = QLabel("🔮")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(
            "font-size: 48px; background: transparent; color: white;"
        )
        
        # Premium Glow Effect
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(25)
        self._glow.setXOffset(0)
        self._glow.setYOffset(0)
        self._glow.setColor(QColor("#58a6ff")) # Default Blue
        self._icon_label.setGraphicsEffect(self._glow)
        
        layout.addWidget(self._icon_label)
        
        # Pulse Animation for Thinking
        self._pulse_anim = QPropertyAnimation(self._glow, b"blurRadius")
        self._pulse_anim.setDuration(800)
        self._pulse_anim.setStartValue(25)
        self._pulse_anim.setEndValue(45)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)

        self._reposition_to_default()

    def _reposition_to_default(self) -> None:
        screen = self.screen().geometry()
        margin = 30
        self.move(
            screen.width() - self.width() - margin,
            screen.height() - self.height() - margin - 60
        )

    # ------------------------------------------------------------------
    # Mouse Events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._dragging or (event.globalPosition().toPoint() - (self.frameGeometry().topLeft() + self._drag_position)).manhattanLength() < 5:
                self.clicked.emit()
            self._dragging = False
            event.accept()

    def enterEvent(self, event: QEnterEvent) -> None:
        # Hover interaction
        self._glow.setBlurRadius(45)
        self._glow.setColor(QColor("#a5d6ff")) # Lighter blue on hover
        self._icon_label.setStyleSheet("font-size: 54px; color: white;") # Swell
        super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent) -> None:
        if self._pulse_anim.state() == QPropertyAnimation.State.Running:
            self._glow.setColor(QColor("#3fb950"))
        else:
            self._glow.setColor(QColor("#58a6ff"))
        self._glow.setBlurRadius(25)
        self._icon_label.setStyleSheet("font-size: 48px; color: white;")
        super().leaveEvent(event)

    def set_thinking(self, thinking: bool) -> None:
        """Visual feedback for AI agent states."""
        if thinking:
            self._glow.setColor(QColor("#3fb950")) # Green Thinking
            self._pulse_anim.setDuration(600)  # Faster pulse
            self._pulse_anim.start()
            self._icon_label.setText("⚡")
        else:
            self._glow.setColor(QColor("#58a6ff")) # Idle Blue
            self._pulse_anim.stop()
            self._glow.setBlurRadius(25)
            self._icon_label.setText("🔮")
