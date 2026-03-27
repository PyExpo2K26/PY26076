"""
infini_think.config.settings
============================
Central configuration hub for InfiniThink.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent
_USER_DATA_DIR: Path = Path.home() / ".infini_think"


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


@dataclass
class Settings:
    """Immutable-ish configuration object for InfiniThink."""

    # --- AI Engine (Ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout: int = 300  # Increased for long document summaries
    ollama_stream: bool = False

    # --- Voice ---
    voice_enabled: bool = field(
        default_factory=lambda: os.getenv("INFINI_VOICE", "true").lower() == "true"
    )
    tts_rate: int = 175
    tts_volume: float = 0.9
    stt_phrase_timeout: float = 1.5
    stt_energy_threshold: int = 300
    stt_wake_word: str = "hey"
    stt_continuous_listening: bool = True

    # --- GUI ---
    window_title: str = "InfiniThink"
    window_width: int = 900
    window_height: int = 680
    theme: str = field(
        default_factory=lambda: os.getenv("INFINI_THEME", "dark")
    )

    # --- Logging ---
    log_level: str = field(
        default_factory=lambda: os.getenv("INFINI_LOG_LEVEL", "INFO")
    )
    log_to_file: bool = True
    log_dir: Path = field(default_factory=lambda: _USER_DATA_DIR / "logs")

    # --- Paths ---
    downloads_dir: Path = field(default_factory=lambda: Path.home() / "Downloads")
    user_data_dir: Path = field(default_factory=lambda: _USER_DATA_DIR)
    package_root: Path = field(default_factory=lambda: _PACKAGE_ROOT)

    # --- Executor ---
    max_plan_steps: int = 10
    command_timeout: int = 30

    def ensure_dirs(self) -> None:
        """Create user-facing directories."""
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
