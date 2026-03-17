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
from infini_think.gui.chat_widget import ChatWidget
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
            plan = self._planner.plan(self._user_input)
            results = self._executor.execute_plan(plan)
            self.result_ready.emit(results)
        except AIEngineError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("Worker encountered unexpected error")
            self.error.emit(f"Unexpected error: {exc}")
        finally:
            self.finished.emit()


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

_TITLE_STYLE = (
    "QLabel { color: #58a6ff; font-size: 18px; font-weight: 700; "
    "background: transparent; padding: 0 8px; }"
)

_STATUS_STYLE = "QStatusBar { background: #0d1117; color: #8b949e; font-size: 9px; }"

_WINDOW_STYLE = """
QMainWindow, QWidget#central {
    background: rgba(13, 17, 23, 180);
    border-left: 1px solid #30363d;
}
"""

_SIDEBAR_WIDTH = 350


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
        self._stt = SpeechToText(
            on_result=self._on_stt_result,
            on_error=self._on_stt_error,
        )
        self.stt_result_ready.connect(self._handle_stt_result)
        self.stt_error_occurred.connect(self._handle_stt_error)

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
        self.setStyleSheet(_WINDOW_STYLE)

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
        """Return the styled header bar widget."""
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(
            "background: #161b22; border-bottom: 1px solid #30363d;"
        )
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)

        # Logo + title
        title = QLabel("⚡ InfiniThink")
        title.setStyleSheet(_TITLE_STYLE)
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))

        subtitle = QLabel("Local AI Agent")
        subtitle.setStyleSheet(
            "color: #8b949e; font-size: 10px; background: transparent; padding: 0 4px;"
        )

        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        h_layout.addStretch()

        # Ollama status indicator
        self._ollama_indicator = QLabel("●")
        self._ollama_indicator.setStyleSheet(
            "color: #d29922; font-size: 10px; background: transparent;"
        )
        h_layout.addWidget(self._ollama_indicator)

        # Close button for the sidebar
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.hide)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #8b949e; font-size: 16px; border: none; }"
            "QPushButton:hover { color: #da3633; }"
        )
        h_layout.addWidget(close_btn)

        return header

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

            if success:
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
            self._stt.start_listening()
            self._chat.add_system_message("🎤 Listening… speak your command.")
        else:
            self._stt.stop_listening()

    def _on_stt_result(self, text: str) -> None:
        """Called from the STT background thread — schedule GUI update safely."""
        self.stt_result_ready.emit(text)

    @Slot(str)
    def _handle_stt_result(self, text: str) -> None:
        self._chat.add_user_message(f"🎤 {text}")
        self._chat.set_mic_active(False)
        self._stt.stop_listening()
        self._on_message_submitted(text)

    def _on_stt_error(self, msg: str) -> None:
        self.stt_error_occurred.emit(msg)

    @Slot(str)
    def _handle_stt_error(self, msg: str) -> None:
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
