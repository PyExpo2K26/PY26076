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

from PySide6.QtCore import Qt, QPoint, Signal, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QPauseAnimation, QTimer
from PySide6.QtGui import QPixmap, QMouseEvent, QEnterEvent, QColor, QImage
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, QMenu, QPushButton, QApplication

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

class AgentBubble(QWidget):
    """The floating agent 'bubble' icon with premium animations."""
    
    clicked = Signal()
    file_dropped = Signal(str)

    def __init__(self, icon_path: str) -> None:
        super().__init__()
        self._icon_path = icon_path
        self._dragging = False
        self._drag_position = QPoint()
        self._icon_cache: dict[bool, QPixmap] = {}
        
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
        self.setAcceptDrops(True)
        self.setFixedSize(100, 100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # UI Symbol/Logo
        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_icon_content()
        
        # Premium Glow Effect
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(25)
        self._glow.setXOffset(0)
        self._glow.setYOffset(0)
        self._glow.setColor(QColor("#58a6ff")) # Default Blue
        self._icon_label.setGraphicsEffect(self._glow)
        
        layout.addWidget(self._icon_label)

        # Status HUD Label
        self._status_label = QLabel("", self)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.hide() # Hidden by default
        self._update_status_style()
        
        # Pulse Animation for Thinking
        self._pulse_anim = QPropertyAnimation(self._glow, b"blurRadius")
        self._pulse_anim.setDuration(800)
        self._pulse_anim.setStartValue(25)
        self._pulse_anim.setEndValue(45)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)

        # Small Exit Button
        self._exit_btn = QPushButton("✕", self)
        self._exit_btn.setFixedSize(16, 16)
        self._exit_btn.move(self.width() - 20, 4)
        self._exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._exit_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #8b949e; border: none; font-weight: bold; }"
            "QPushButton:hover { color: #f85149; }"
        )
        self._exit_btn.clicked.connect(lambda: QApplication.instance().quit())

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

    def contextMenuEvent(self, event) -> None:
        """Show a right-click context menu to quit the app."""
        from PySide6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        menu.setStyleSheet(
             "QMenu { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; padding: 4px; }"
             "QMenu::item:selected { background: #1f6feb; border-radius: 2px; }"
        )
        quit_action = menu.addAction("Quit InfiniThink")
        action = menu.exec(event.globalPos())
        if action == quit_action:
            QApplication.instance().quit()

    def enterEvent(self, event: QEnterEvent) -> None:
        # Hover interaction
        self._glow.setBlurRadius(45)
        self._glow.setColor(QColor("#a5d6ff")) # Lighter blue on hover
        super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent) -> None:
        if self._pulse_anim.state() == QPropertyAnimation.State.Running:
            self._glow.setColor(QColor("#3fb950"))
        else:
            self._glow.setColor(QColor("#58a6ff"))
        self._glow.setBlurRadius(25)
        super().leaveEvent(event)

    # ------------------------------------------------------------------
    # Drag and Drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._glow.setColor(QColor("#f2cc60")) # Yellow for drop hover
            self.set_status("Drop to process")

    def dragLeaveEvent(self, event) -> None:
        if self._pulse_anim.state() == QPropertyAnimation.State.Running:
            self._glow.setColor(QColor("#3fb950"))
        else:
            self._glow.setColor(QColor("#58a6ff"))
        self.set_status("")
        event.accept()

    def dropEvent(self, event) -> None:
        import os
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if not file_path:
                file_path = urls[0].toString()
            
            # Final cleanup to ensure no file:/// prefixes
            if "file:///" in file_path:
                file_path = file_path.replace("file:///", "")
            
            import urllib.parse
            file_path = urllib.parse.unquote(file_path)
            
            self.file_dropped.emit(file_path)
            # Use os.path.basename to avoid backslashes in f-string expressions
            fname = os.path.basename(file_path)
            self.set_status(f"Dropped: {fname}")
            event.acceptProposedAction()

    def set_thinking(self, thinking: bool) -> None:
        """Visual feedback for AI agent states."""
        if thinking:
            self._glow.setColor(QColor("#3fb950")) # Green Thinking
            self._pulse_anim.setDuration(600)  # Faster pulse
            self._pulse_anim.start()
        else:
            self._glow.setColor(QColor("#58a6ff")) # Idle Blue
            self._pulse_anim.stop()
            self._glow.setBlurRadius(25)
        
        self._set_icon_content(thinking)
        if not thinking:
            self.set_status("")

    def set_status(self, text: str) -> None:
        """Update the HUD text and visibility."""
        if not text:
            self._status_label.hide()
            return
        
        self._status_label.setText(text)
        self._status_label.adjustSize()
        
        # Position the label above or to the left of the bubble
        self._status_label.move(
            (self.width() - self._status_label.width()) // 2,
            -20 # Slightly above the bubble
        )
        self._status_label.show()
        
        # Auto-hide after 3 seconds if not thinking
        if self._pulse_anim.state() != QPropertyAnimation.State.Running:
            QTimer.singleShot(3000, lambda: self._status_label.hide() if self._pulse_anim.state() != QPropertyAnimation.State.Running else None)

    def _update_status_style(self) -> None:
        """Stylize the HUD label with a premium glass look."""
        self._status_label.setStyleSheet(
            "QLabel { "
            "background: rgba(22, 27, 34, 230); "
            "color: #58a6ff; "
            "border-radius: 8px; "
            "padding: 4px 10px; "
            "font-family: 'Segoe UI Variable Text'; "
            "font-size: 10px; "
            "font-weight: 600; "
            "}"
        )

    def _set_icon_content(self, is_thinking: bool = False) -> None:
        """Loads and sets the icon content based on state, with transparency processing and caching."""
        if is_thinking in self._icon_cache:
            self._icon_label.setPixmap(self._icon_cache[is_thinking])
            return

        pm = QPixmap(self._icon_path)
        if not pm.isNull():
            # Dynamically remove solid dark background if it exists (for mask-style icons)
            # We use an 'alpha = brightness' mapping for premium antialiased edges
            img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
            for y in range(img.height()):
                for x in range(img.width()):
                    c = img.pixelColor(x, y)
                    # Use the max of RGB as the new alpha channel for white-on-black icons
                    alpha = max(c.red(), c.green(), c.blue())
                    img.setPixelColor(x, y, QColor(255, 255, 255, alpha))
            processed_pm = QPixmap.fromImage(img)

            # Slightly larger when thinking
            size = 64 if is_thinking else 58
            scaled_pm = processed_pm.scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            
            # Cache the result
            self._icon_cache[is_thinking] = scaled_pm
            self._icon_label.setPixmap(scaled_pm)
            self._icon_label.setStyleSheet("background: transparent;")
        else:
            # Fallback to emoji
            emoji = "⚡" if is_thinking else "🔮"
            self._icon_label.setText(emoji)
            size = "54px" if is_thinking else "48px"
            self._icon_label.setStyleSheet(f"font-size: {size}; background: transparent; color: white;")
