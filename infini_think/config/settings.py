"""
infini_think.config.settings
============================
Central configuration hub for InfiniThink.

All tuneable parameters live here so any module can import a single
``Settings`` instance rather than scattering constants around the codebase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Root of the installed package / source tree
_PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent

# User-facing data directory (logs, cache, user config)
_USER_DATA_DIR: Path = Path.home() / ".infini_think"


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


@dataclass
class Settings:
    """Immutable-ish configuration object for InfiniThink.

    Attributes are read from environment variables where applicable so that
    CI / Docker / power-users can override without touching code.
    """

    # --- Ollama / LLM -------------------------------------------------------
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("INFINI_OLLAMA_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("INFINI_OLLAMA_MODEL", "llama3")
    )
    ollama_timeout: int = field(
        default_factory=lambda: int(os.getenv("INFINI_OLLAMA_TIMEOUT", "60"))
    )
    ollama_stream: bool = False  # Streaming disabled for simpler integration

    # --- Voice ---------------------------------------------------------------
    voice_enabled: bool = field(
        default_factory=lambda: os.getenv("INFINI_VOICE", "true").lower() == "true"
    )
    tts_rate: int = 175           # Words per minute for pyttsx3
    tts_volume: float = 0.9       # 0.0 – 1.0
    stt_phrase_timeout: float = 5.0   # Seconds of silence before phrase ends
    stt_energy_threshold: int = 300   # Mic sensitivity

    # --- GUI -----------------------------------------------------------------
    window_title: str = "InfiniThink"
    window_width: int = 900
    window_height: int = 680
    theme: str = field(
        default_factory=lambda: os.getenv("INFINI_THEME", "dark")
    )  # "dark" | "light"

    # --- Logging -------------------------------------------------------------
    log_level: str = field(
        default_factory=lambda: os.getenv("INFINI_LOG_LEVEL", "INFO")
    )
    log_to_file: bool = True
    log_dir: Path = field(default_factory=lambda: _USER_DATA_DIR / "logs")

    # --- Paths ---------------------------------------------------------------
    downloads_dir: Path = field(default_factory=lambda: Path.home() / "Downloads")
    user_data_dir: Path = field(default_factory=lambda: _USER_DATA_DIR)
    package_root: Path = field(default_factory=lambda: _PACKAGE_ROOT)

    # --- Executor ------------------------------------------------------------
    max_plan_steps: int = 10       # Safety cap on planner output
    command_timeout: int = 30      # Max seconds per tool execution

    def ensure_dirs(self) -> None:
        """Create user-facing directories if they don't exist."""
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ollama_generate_url(self) -> str:
        """Full URL for the Ollama /api/generate endpoint."""
        return f"{self.ollama_base_url}/api/generate"

    @property
    def ollama_tags_url(self) -> str:
        """Full URL for listing available Ollama models."""
        return f"{self.ollama_base_url}/api/tags"


# ---------------------------------------------------------------------------
# Module-level singleton — import this from anywhere
# ---------------------------------------------------------------------------

settings = Settings()
settings.ensure_dirs()
