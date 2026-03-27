"""
infini_think.gui.main_window
==============================
Top-level application window for InfiniThink.

Orchestrates the :class:`ChatWidget`, connects it to the AI processing
pipeline (interpreter → planner → executor), and manages the voice
assistant lifecycle.

The heavy AI work is offloaded to a :class:`~PySide6.QtCore.QThread`
worker so the GUI stays responsive during LLM inference.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot
from PySide6.QtGui import QFont, QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QPushButton,
    QApplication,
    QSizePolicy,
)

from infini_think.config.settings import settings
from infini_think.core.ai_engine import AIEngine, AIEngineError
from infini_think.core.command_interpreter import CommandInterpreter
from infini_think.core.planner import TaskPlanner
from infini_think.core.executor import Executor
from infini_think.gui.chat_widget import ChatWidget, ThemeProvider
from infini_think.voice.speech_to_text import SpeechToText
from infini_think.voice.text_to_speech import TextToSpeech
from infini_think.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Background worker — runs AI inference off the GUI thread
# ---------------------------------------------------------------------------

class _AIWorker(QObject):
    """Performs AI interpretation + execution in a background thread.

    Signals:
        result_ready (list): Execution results ready to display.
        error (str):         A fatal error occurred.
        finished ():         Worker has completed its task.
    """

    result_ready = Signal(list)   # list[ExecutionResult]
    chunk_ready = Signal(str)    # New: for streaming
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        user_input: str,
        planner: TaskPlanner,
        executor: Executor,
    ) -> None:
        super().__init__()
        self._user_input = user_input
        self._planner = planner
        self._executor = executor

    @Slot()
    def run(self) -> None:
        try:
            self.chunk_ready.emit("Analyzing request...")
            # Plan first
            plan = self._planner.plan(self._user_input)
            
            self.chunk_ready.emit(f"Executing {len(plan)} task(s)...")
            # Execute and emit results
            results = self._executor.execute_plan(plan)
            self.result_ready.emit(results)
        except Exception as exc:  # noqa: BLE001
            log.exception("Worker encountered unexpected error")
            self.error.emit(f"Unexpected error: {exc}")
        finally:
            self.finished.emit()


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dynamic Styles
# ---------------------------------------------------------------------------

def get_window_style():
    c = ThemeProvider.colors()
    return f"""
        QMainWindow, QWidget#central {{
            background: {c['sidebar_bg']};
            border-left: 1px solid {c['border']};
        }}
    """

def get_title_style():
    c = ThemeProvider.colors()
    return f"QLabel {{ color: {c['accent']}; font-size: 17px; font-weight: 700; background: transparent; }}"

_SIDEBAR_WIDTH = 360  # Slightly narrower for a cleaner look


class MainWindow(QMainWindow):
    """InfiniThink main application window.

    Wires together the chat UI, AI backend, voice assistant, and menu bar.
    """

    stt_result_ready = Signal(str)
    stt_error_occurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._threads: list[QThread] = []
        self._stt: SpeechToText | None = None
        self._tts: TextToSpeech | None = None
        self._engine: AIEngine | None = None
        self._interpreter: CommandInterpreter | None = None
        self._planner: TaskPlanner | None = None
        self._executor: Executor | None = None

        self._init_ai()
        self._init_voice()
        self._build_ui()
        self._check_ollama_status()

        log.info("MainWindow initialised as Sidebar")

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_ai(self) -> None:
        """Initialise the AI pipeline components."""
        self._engine = AIEngine()
        self._interpreter = CommandInterpreter(self._engine)
        self._planner = TaskPlanner(self._engine, self._interpreter)
        self._executor = Executor()
        log.info("AI pipeline components initialised")

    def _init_voice(self) -> None:
        """Initialise voice I/O components."""
        self._tts = TextToSpeech()
        
        # Use wake word if continuous listening is enabled
        trigger = settings.stt_wake_word if settings.stt_continuous_listening else None
        
        self._stt = SpeechToText(
            on_result=self._on_stt_result,
            on_error=self._on_stt_error,
            trigger_phrase=trigger
        )
        self.stt_result_ready.connect(self._handle_stt_result)
        self.stt_error_occurred.connect(self._handle_stt_error)

        # Start listening automatically if continuous mode is on
        if settings.stt_continuous_listening and self._stt.is_available:
            self._stt.start_listening()
            log.info("Continuous listening enabled (wake word: %r)", settings.stt_wake_word)

    def _build_ui(self) -> None:
        """Construct the main window layout as a sidebar."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setWindowTitle(settings.window_title)
        self._reposition_sidebar()
        self.update_styles()

        # --- Central widget ---
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Header bar ---
        header = self._build_header()
        root.addWidget(header)

        # --- Chat widget ---
        self._chat = ChatWidget()
        self._chat.message_submitted.connect(self._on_message_submitted)
        self._chat.mic_toggled.connect(self._on_mic_toggled)
        root.addWidget(self._chat, stretch=1)

    def _reposition_sidebar(self) -> None:
        """Position the window as a sidebar on the right."""
        screen = self.screen().geometry()
        self.setGeometry(
            screen.width() - _SIDEBAR_WIDTH,
            0,
            _SIDEBAR_WIDTH,
            screen.height()
        )

    def toggle_visibility(self) -> None:
        """Toggle the sidebar visibility with a simple show/hide."""
        if self.isVisible():
            self.hide()
            log.info("Sidebar hidden")
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            log.info("Sidebar shown")

    def _build_header(self) -> QWidget:
        """Return the styled header bar widget with theme toggle."""
        self._header = QWidget()
        self._header.setFixedHeight(54) # Slimmer header
        self.update_header_styles()
        
        h_layout = QHBoxLayout(self._header)
        h_layout.setContentsMargins(16, 0, 12, 0)
        h_layout.setSpacing(8)

        # Logo + title
        self._title_label = QLabel("⚡ InfiniThink")
        self._title_label.setFont(QFont("Segoe UI Variable Display", 13, QFont.Weight.Bold))
        
        self._subtitle_label = QLabel("v1.4.0 Proxy")
        self._subtitle_label.setStyleSheet("font-size: 10px; opacity: 0.6;")

        h_layout.addWidget(self._title_label)
        h_layout.addWidget(self._subtitle_label)
        h_layout.addStretch()

        # Theme Toggle
        self._theme_btn = QPushButton("☀️") # Show Sun because we are in Dark Mode initially
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setToolTip("Toggle Theme")
        self._theme_btn.clicked.connect(self._on_theme_toggle)
        h_layout.addWidget(self._theme_btn)

        # Ollama status indicator
        self._ollama_indicator = QLabel("●")
        self._ollama_indicator.setToolTip("Ollama Status")
        h_layout.addWidget(self._ollama_indicator)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.hide)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        h_layout.addWidget(close_btn)

        return self._header

    def update_styles(self) -> None:
        """Update window and sub-widget styles based on current theme."""
        c = ThemeProvider.colors()
        self.setStyleSheet(get_window_style())
        if hasattr(self, "_chat"):
            self._chat.update_styles()
        if hasattr(self, "_header"):
            self.update_header_styles()
            self._title_label.setStyleSheet(get_title_style())
            self._subtitle_label.setStyleSheet(f"color: {c['timestamp']}; background: transparent;")
            self._theme_btn.setStyleSheet(
                f"QPushButton {{ background: {c['welcome_bg']}; border-radius: 18px; border: 1px solid {c['border']}; "
                f"font-size: 16px; color: {c['ai_text']}; }}"
                f"QPushButton:hover {{ background: {c['surface']}; }}"
            )

    def update_header_styles(self) -> None:
        c = ThemeProvider.colors()
        self._header.setStyleSheet(
            f"QWidget {{ background: {c['surface']}; border-bottom: 1px solid {c['border']}; }}"
            f"QPushButton {{ background: transparent; color: {c['timestamp']}; font-size: 16px; border: none; }}"
            f"QPushButton:hover {{ color: {c['accent']}; }}"
        )

    @Slot()
    def _on_theme_toggle(self) -> None:
        """Switch between dark and light themes."""
        current = ThemeProvider._current
        new_theme = "light" if current == "dark" else "dark"
        self._theme_btn.setText("☀️" if new_theme == "light" else "🌙")
        self._chat.switch_theme(new_theme)
        self.update_styles()
        log.info("Theme switched to: %s", new_theme)

    def _build_menu(self) -> None:
        """Construct the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        clear_act = QAction("Clear Chat", self)
        clear_act.setShortcut("Ctrl+L")
        clear_act.triggered.connect(lambda: self._chat._message_area.clear())
        file_menu.addAction(clear_act)
        file_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_act)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_act = QAction("About InfiniThink", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ------------------------------------------------------------------
    # Ollama connectivity check
    # ------------------------------------------------------------------

    def _check_ollama_status(self) -> None:
        """Check Ollama availability and update the status indicator."""
        if self._engine and self._engine.is_available():
            self._ollama_indicator.setStyleSheet(
                "color: #3fb950; font-size: 10px; background: transparent;"
            )
        else:
            self._ollama_indicator.setText("● Ollama offline")
            self._ollama_indicator.setStyleSheet(
                "color: #da3633; font-size: 10px; background: transparent;"
            )
            self._chat.add_system_message(
                "⚠️  Ollama is not running.\n"
                "Start it with:  ollama serve\n"
                "Then pull the model:  ollama pull llama3\n\n"
                "You can still explore the interface; AI commands will show an error."
            )

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_message_submitted(self, text: str) -> None:
        """Called when the user sends a message — dispatches AI work to a thread."""
        log.info("User submitted: %r", text)
        self._chat.set_thinking(True)

        # Create worker + thread
        thread = QThread()
        worker = _AIWorker(text, self._planner, self._executor)
        worker.moveToThread(thread)
        
        # Keep a reference to prevent garbage collection
        thread.worker = worker 

        thread.started.connect(worker.run)
        worker.result_ready.connect(self._on_results_ready)
        worker.chunk_ready.connect(self._on_ai_chunk)  # New: connect chunk signal
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)

        self._threads.append(thread)
        thread.start()

    @Slot(list)
    def _on_results_ready(self, results: list[dict]) -> None:
        """Called on the GUI thread when AI execution results arrive."""
        self._chat.set_thinking(False)

        for result in results:
            tool = result.get("tool", "?")
            success = result.get("success", False)
            output = result.get("output", "")
            elapsed = result.get("elapsed", 0.0)

            if tool == "talk":
                # Natural conversation doesn't need status icons
                msg = output
            elif success:
                msg = f"✅  {output}"
                log.info("Executed '%s' in %.3fs", tool, elapsed)
            else:
                msg = f"❌  {output}"
                log.warning("Tool '%s' failed: %s", tool, output)

            self._chat.add_ai_message(msg)
            if self._tts and success:
                self._tts.speak(output)

    @Slot(str)
    def _on_worker_error(self, error_msg: str) -> None:
        """Called when the background worker encounters a fatal error."""
        self._chat.set_thinking(False)
        self._chat.add_ai_message(f"❌  Error: {error_msg}")
        if self._tts:
            self._tts.speak("I encountered an error. Please check if Ollama is running.")

    # ------------------------------------------------------------------
    # Voice
    # ------------------------------------------------------------------

    @Slot(bool)
    def _on_mic_toggled(self, active: bool) -> None:
        """Start or stop the speech recogniser when the mic button is clicked."""
        if not self._stt:
            return
            
        if active:
            # If we are in continuous mode, temporarily disable the trigger for direct input
            if settings.stt_continuous_listening:
                self._stt.set_trigger_phrase(None)
                
            self._stt.start_listening()
            self._chat.add_system_message("🎤 Listening… speak your command.")
        else:
            # If we are in continuous mode, re-enable the trigger instead of stopping
            if settings.stt_continuous_listening:
                self._stt.set_trigger_phrase(settings.stt_wake_word)
                self._chat.add_system_message(f"👂 Continuous listening active (wake word: {settings.stt_wake_word})")
            else:
                self._stt.stop_listening()

    def _on_stt_result(self, text: str) -> None:
        """Called from the STT background thread — schedule GUI update safely."""
        self.stt_result_ready.emit(text)

    @Slot(str)
    def _handle_stt_result(self, text: str) -> None:
        self._chat.add_user_message(f"🎤 {text}")
        
        # If the mic was manually activated (not via continuous wake word), reset it
        if self._chat._mic_active:
            self._chat.set_mic_active(False)
        
        # Only stop listening if we are NOT in continuous mode
        if not settings.stt_continuous_listening:
            self._stt.stop_listening()
            
        self._on_message_submitted(text)

    def _on_stt_error(self, msg: str) -> None:
        self.stt_error_occurred.emit(msg)

    @Slot(str)
    def _on_ai_chunk(self, chunk: str) -> None:
        """Called when a new token chunk arrives from the AI."""
        if self.statusBar():
            self.statusBar().showMessage(f"AI: {chunk}")
        log.debug("AI Chunk: %s", chunk)

    @Slot(str)
    def _handle_stt_error(self, msg: str) -> None:
        """Called on the GUI thread when the STT worker hits a snag."""
        self._chat.add_system_message(f"⚠️ Voice error: {msg}")
        self._chat.set_mic_active(False)

    # ------------------------------------------------------------------
    # About dialog
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About InfiniThink",
            "<h3>⚡ InfiniThink v1.0.0</h3>"
            "<p>A local-first desktop AI agent.<br>"
            "Powered by <b>Ollama</b> + <b>Llama 3</b>.</p>"
            "<p>No cloud APIs. No subscriptions. 100% private.</p>"
            "<p><a href='https://github.com/your-org/infini-think'>GitHub</a></p>",
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """Clean up threads and voice components on close."""
        log.info("Window closing — cleaning up")
        if self._stt:
            self._stt.stop_listening()
        if self._tts:
            self._tts.stop()
        for thread in self._threads:
            thread.quit()
            thread.wait(1000)
        super().closeEvent(event)
