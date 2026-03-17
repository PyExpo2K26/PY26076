"""
infini_think.gui.agent_bubble
===============================
A small, floating, frameless window representing the AI agent.

Features:
- Frameless and transparent background.
- Floating always-on-top.
- Draggable via mouse interaction.
- Clickable to toggle the main sidebar.
- Subtle glow animations.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QMouseEvent, QEnterEvent
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

class AgentBubble(QWidget):
    """The floating agent 'bubble' icon."""
    
    clicked = Signal()

    def __init__(self, icon_path: str) -> None:
        super().__init__()
        self._icon_path = icon_path
        self._dragging = False
        self._drag_position = QPoint()
        
        self._init_ui()
        log.info("AgentBubble initialised with icon: %s", icon_path)

    def _init_ui(self) -> None:
        # Window configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Doesn't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedSize(90, 90)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self._icon_label = QLabel()
        pixmap = QPixmap(self._icon_path)
        if pixmap.isNull():
            log.error("Failed to load agent icon from: %s", self._icon_path)
            # Fallback text if icon fails
            self._icon_label.setText("🚀")
            self._icon_label.setStyleSheet("font-size: 40px;")
        else:
            self._icon_label.setPixmap(pixmap.scaled(75, 75, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add a glow effect
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(20)
        self._glow.setXOffset(0)
        self._glow.setYOffset(0)
        self._glow.setColor("#58a6ff")
        self._icon_label.setGraphicsEffect(self._glow)
        
        layout.addWidget(self._icon_label)
        
        # Initial positioning: bottom right
        self._reposition_to_default()

    def _reposition_to_default(self) -> None:
        """Move the bubble to a default position (bottom right)."""
        screen = self.screen().geometry()
        margin = 30
        self.move(
            screen.width() - self.width() - margin,
            screen.height() - self.height() - margin - 50 # Above taskbar
        )

    # ------------------------------------------------------------------
    # Mouse Events (Drag & Click)
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
            # If the mouse didn't move much, it's a click
            if not self._dragging or (event.globalPosition().toPoint() - (self.frameGeometry().topLeft() + self._drag_position)).manhattanLength() < 5:
                self.clicked.emit()
            self._dragging = False
            event.accept()

    def enterEvent(self, event: QEnterEvent) -> None:
        # Hover effect: increase glow
        self._glow.setBlurRadius(35)
        super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent) -> None:
        # Leave effect: reset glow
        self._glow.setBlurRadius(20)
        super().leaveEvent(event)

    def set_thinking(self, thinking: bool) -> None:
        """Pulse the glow when thinking."""
        if thinking:
            # Simple pulse animation logic could go here
            self._glow.setColor("#3fb950") # Greenish glow for thinking
        else:
            self._glow.setColor("#58a6ff")
