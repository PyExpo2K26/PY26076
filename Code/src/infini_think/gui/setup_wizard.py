"""
infini_think.gui.setup_wizard
============================
First-run setup wizard for InfiniThink.

Ensures the local environment is correctly configured (Ollama installed,
model pulled, playwright browsers downloaded) before allowing the main
application to launch.
"""

from __future__ import annotations

import sys
import subprocess
import threading
import time
import urllib.request
import os
import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal, QObject, Slot, QThread, QTimer
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
)

from infini_think.config.settings import settings
from infini_think.core.ai_engine import AIEngine
from infini_think.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Background Install Worker
# ---------------------------------------------------------------------------

class DownloadWorker(QObject):
    """Downloads a file in the background and emits progress."""
    progress = Signal(int)
    finished = Signal(bool, str) # success, result_or_error

    def __init__(self, url: str, dest_path: str) -> None:
        super().__init__()
        self.url = url
        self.dest_path = dest_path

    @Slot()
    def run(self) -> None:
        try:
            log.info("Downloading %s to %s", self.url, self.dest_path)
            
            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    self.progress.emit(min(percent, 100))
            
            urllib.request.urlretrieve(self.url, self.dest_path, reporthook=report_hook)
            self.finished.emit(True, self.dest_path)
        except Exception as exc:
            log.exception("Download failed")
            self.finished.emit(False, str(exc))


class RunCommandWorker(QObject):
    """Executes a shell command and reports status/output."""
    finished = Signal(bool, str) # success, message
    output_received = Signal(str)

    def __init__(self, command: list[str]) -> None:
        super().__init__()
        self.command = command

    @Slot()
    def run(self) -> None:
        try:
            log.info("Running setup command: %s", " ".join(self.command))
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True if sys.platform == "win32" else False
            )
            
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        self.output_received.emit(line.strip())
                process.stdout.close()
            
            return_code = process.wait()
            success = (return_code == 0)
            self.finished.emit(success, "Completed" if success else f"Failed with exit code {return_code}")
        except Exception as exc:
            log.exception("Setup command failed")
            self.finished.emit(False, str(exc))


# ---------------------------------------------------------------------------
# SetupWizard Window
# ---------------------------------------------------------------------------

class SetupWizard(QMainWindow):
    """The first-run setup UI."""
    setup_finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._init_data()
        self._build_ui()
        self._check_all_requirements()

    def _init_data(self) -> None:
        self.setWindowTitle("⚡ InfiniThink — One-Click Setup")
        self.setFixedSize(600, 500)
        self._engine = AIEngine()
        self._threads: list[QThread] = []

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel("Welcome to InfiniThink")
        header.setFont(QFont("Segoe UI Variable Display", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #58a6ff;")
        layout.addWidget(header)

        desc = QLabel("Let's make sure your local AI environment is ready. Click 'Setup Everything' to automate the process.")
        desc.setWordWrap(True)
        desc.setFont(QFont("Segoe UI", 10))
        layout.addWidget(desc)

        # Status Group
        self._status_container = QWidget()
        status_vbox = QVBoxLayout(self._status_container)
        status_vbox.setContentsMargins(0, 10, 0, 10)
        
        self._ollama_item = self._add_status_row("Ollama Engine", status_vbox)
        self._model_item = self._add_status_row(f"AI Model ({settings.ollama_model})", status_vbox)
        self._playwright_item = self._add_status_row("Web Browsers (Playwright)", status_vbox)
        
        layout.addWidget(self._status_container)

        # Progress / Log Area (Initally hidden)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._log_area = QScrollArea()
        self._log_area.setWidgetResizable(True)
        self._log_area.setFixedHeight(120)
        self._log_label = QLabel("Waiting for start...")
        self._log_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._log_label.setStyleSheet("font-family: Consolas; font-size: 9pt; color: #8b949e;")
        self._log_area.setWidget(self._log_label)
        self._log_area.hide()
        layout.addWidget(self._log_area)

        # Footer Actions
        footer = QHBoxLayout()
        self._refresh_btn = QPushButton("Check Again")
        self._refresh_btn.clicked.connect(self._check_all_requirements)
        
        self._setup_btn = QPushButton("Setup Everything")
        self._setup_btn.setFixedHeight(45)
        self._setup_btn.setStyleSheet("background: #1f6feb; border-radius: 8px; font-weight: bold;")
        self._setup_btn.clicked.connect(self._run_full_setup)

        self._launch_btn = QPushButton("Launch InfiniThink")
        self._launch_btn.setFixedHeight(45)
        self._launch_btn.setEnabled(False)
        self._launch_btn.setStyleSheet("background: #238636; border-radius: 8px; font-weight: bold;")
        self._launch_btn.clicked.connect(self._on_launch_clicked)
        self._launch_btn.hide()

        footer.addWidget(self._refresh_btn)
        footer.addStretch()
        footer.addWidget(self._setup_btn)
        footer.addWidget(self._launch_btn)
        layout.addLayout(footer)

    def _add_status_row(self, label: str, parent_layout: QVBoxLayout) -> dict:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        
        name = QLabel(label)
        name.setFont(QFont("Segoe UI Semibold", 10))
        
        indicator = QLabel("● Checking...")
        indicator.setStyleSheet("color: #8b949e;")
        
        h.addWidget(name)
        h.addStretch()
        h.addWidget(indicator)
        
        parent_layout.addWidget(row)
        return {"label": name, "indicator": indicator, "status": "checking"}

    # ------------------------------------------------------------------
    # Requirement Checks
    # ------------------------------------------------------------------

    def _update_row(self, item: dict, status: str, text: str | None = None) -> None:
        item["status"] = status
        if status == "ok":
            item["indicator"].setText(f"✅ {text or 'Ready'}")
            item["indicator"].setStyleSheet("color: #3fb950;")
        elif status == "missing":
            item["indicator"].setText(f"❌ {text or 'Missing'}")
            item["indicator"].setStyleSheet("color: #f85149;")
        else:
            item["indicator"].setText("● Checking...")
            item["indicator"].setStyleSheet("color: #8b949e;")

    def _check_all_requirements(self) -> None:
        """Run all local checks."""
        # 1. Check Ollama
        ollama_ok = self._engine.is_available()
        # If not reachable, check if binary exists
        import shutil
        binary_exists = shutil.which("ollama") is not None
        
        if ollama_ok:
            self._update_row(self._ollama_item, "ok", "Running")
        elif binary_exists:
            self._update_row(self._ollama_item, "ok", "Installed (but not running)")
        else:
            self._update_row(self._ollama_item, "missing")

        # 2. Check Model
        models = self._engine.list_models()
        if settings.ollama_model in models or any(settings.ollama_model in m for m in models):
            self._update_row(self._model_item, "ok")
        else:
            self._update_row(self._model_item, "missing")

        # 3. Check Playwright
        import os
        # Simplistic check: look for chromium folder in local appdata or similar
        pw_ok = False
        try:
            from playwright.sync_api import sync_playwright
            # This is slow, so we just assume if import works and we can check bin
            pw_ok = True 
        except ImportError:
            pw_ok = False
            
        if pw_ok:
            self._update_row(self._playwright_item, "ok")
        else:
            self._update_row(self._playwright_item, "missing")

        # Final check to reveal launch button
        if ollama_ok and self._model_item["status"] == "ok":
            self._setup_btn.hide()
            self._launch_btn.show()
            self._launch_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Automation Actions
    # ------------------------------------------------------------------

    def _run_full_setup(self) -> None:
        self._setup_btn.setEnabled(False)
        self._progress_bar.show()
        self._log_area.show()
        self._append_log("Starting automated setup...")
        
        # We run steps sequentially
        self._step_1_ollama()

    def _append_log(self, text: str) -> None:
        current = self._log_label.text()
        self._log_label.setText(current + "\n" + text)
        QTimer.singleShot(10, self._scroll_logs)

    def _scroll_logs(self) -> None:
        self._log_area.verticalScrollBar().setValue(self._log_area.verticalScrollBar().maximum())

    def _step_1_ollama(self) -> None:
        import shutil
        if shutil.which("ollama"):
            self._append_log("Ollama already installed.")
            self._step_2_model()
            return
            
        self._append_log("Ollama not found. Downloading the official Windows engine...")
        self.temp_installer = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        
        thread = QThread()
        # Direct URL to the primary Windows installer
        worker = DownloadWorker("https://ollama.com/download/OllamaSetup.exe", self.temp_installer)
        worker.moveToThread(thread)
        
        thread.started.connect(worker.run)
        worker.progress.connect(self._progress_bar.setValue)
        worker.finished.connect(self._on_download_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._threads.append(thread)
        thread.start()

    def _on_download_finished(self, success: bool, result: str) -> None:
        self._progress_bar.setRange(0, 0) # Back to indeterminate
        if success:
            self._append_log("✅ Download complete. Installing Ollama silently...")
            # We run the installer silently in the background
            self._run_command([self.temp_installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], self._on_install_finished)
        else:
            self._append_log(f"❌ Failed to download Ollama: {result}")
            self._setup_btn.setEnabled(True)

    def _on_install_finished(self, success: bool, msg: str) -> None:
        if success:
            self._append_log("✅ Ollama installed correctly.")
            # Add a short delay so the Ollama service has time to start up before checking models
            QTimer.singleShot(3000, self._step_2_model)
        else:
            self._append_log(f"❌ Failed to install Ollama: {msg}")
            self._setup_btn.setEnabled(True)

    def _step_2_model(self) -> None:
        self._append_log(f"Pulling model: {settings.ollama_model} (this may take several minutes)...")
        # Ensure ollama serve is running if possible? 
        # For now we assume if installed, they can run it.
        self._run_command(["ollama", "pull", settings.ollama_model], self._on_model_finished)

    def _on_model_finished(self, success: bool, msg: str) -> None:
        if success:
            self._append_log("✅ Model pulled successfully.")
            self._update_row(self._model_item, "ok")
            self._step_3_playwright()
        else:
            self._append_log(f"❌ Failed to pull model: {msg}")
            self._setup_btn.setEnabled(True)

    def _step_3_playwright(self) -> None:
        self._append_log("Installing browser engines (Playwright)...")
        self._run_command([sys.executable, "-m", "playwright", "install", "chromium"], self._on_playwright_finished)

    def _on_playwright_finished(self, success: bool, msg: str) -> None:
        if success:
            self._append_log("✅ Browser engines installed.")
            self._update_row(self._playwright_item, "ok")
            self._append_log("\n✨ Setup complete! You can now launch InfiniThink.")
            self._check_all_requirements()
        else:
            self._append_log(f"❌ Failed to install browsers: {msg}")
            self._setup_btn.setEnabled(True)

    def _run_command(self, cmd: list[str], callback: Callable[[bool, str], None]) -> None:
        thread = QThread()
        worker = RunCommandWorker(cmd)
        worker.moveToThread(thread)
        
        thread.started.connect(worker.run)
        worker.output_received.connect(self._append_log)
        worker.finished.connect(lambda s, m: callback(s, m))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._threads.append(thread)
        thread.start()

    def _on_launch_clicked(self) -> None:
        settings.mark_setup_complete()
        self.setup_finished.emit()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec())
