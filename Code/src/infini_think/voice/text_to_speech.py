"""
infini_think.voice.text_to_speech
====================================
Text-to-speech module using ``pyttsx3``.

Speech is queued internally so multiple responses can be enqueued without
blocking the caller.  The speech engine runs on its own background thread.

Usage::

    from infini_think.voice.text_to_speech import TextToSpeech

    tts = TextToSpeech()
    tts.speak("Hello! I am InfiniThink.")
"""

from __future__ import annotations

import queue
import threading

from infini_think.config.settings import settings
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

_STOP_SENTINEL = object()  # Sentinel value to signal shutdown


class TextToSpeech:
    """Async text-to-speech queue backed by ``pyttsx3``.

    Enqueues text items and speaks them in order on a daemon thread so
    the caller never blocks.

    Args:
        rate:   Speech rate in words per minute.
        volume: Volume level from 0.0 to 1.0.
    """

    def __init__(
        self,
        rate: int | None = None,
        volume: float | None = None,
    ) -> None:
        self._rate = rate or settings.tts_rate
        self._volume = volume if volume is not None else settings.tts_volume
        self._queue: queue.Queue = queue.Queue()
        self._engine = None
        self._thread: threading.Thread | None = None
        self._available = False

        try:
            import pyttsx3  # noqa: F401
            self._available = True
        except ImportError:
            log.warning("pyttsx3 not installed. Run: pip install pyttsx3")

        if self._available:
            self._start_worker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Return True if pyttsx3 is importable and the thread is running."""
        return self._available and (self._thread is not None and self._thread.is_alive())

    def speak(self, text: str) -> None:
        """Enqueue *text* for speech output (non-blocking).

        Args:
            text: The string to be spoken aloud.
        """
        if not self._available:
            log.warning("TTS not available — skipping speak('%s')", text[:50])
            return
        if not text.strip():
            return
        log.debug("TTS enqueue: %r", text[:80])
        self._queue.put(text)

    def stop(self) -> None:
        """Gracefully shut down the TTS worker thread."""
        self._queue.put(_STOP_SENTINEL)
        if self._thread:
            self._thread.join(timeout=3)

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _start_worker(self) -> None:
        """Initialise and launch the background TTS thread."""
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="tts-worker",
            daemon=True,
        )
        self._thread.start()
        log.info("TTS worker thread started")

    def _worker_loop(self) -> None:
        """Main loop running on the worker thread."""
        import pyttsx3  # noqa: PLC0415

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)

            # Try to set a pleasant voice (prefer a female voice if available)
            voices = engine.getProperty("voices")
            if voices:
                # Prefer voices with 'female' or 'zira' in their name (Windows)
                preferred = next(
                    (v for v in voices if "female" in v.name.lower() or "zira" in v.name.lower()),
                    voices[0],
                )
                engine.setProperty("voice", preferred.id)

            log.info("TTS engine initialised (rate=%d, volume=%.1f)", self._rate, self._volume)

            while True:
                item = self._queue.get()
                if item is _STOP_SENTINEL:
                    break
                try:
                    engine.say(item)
                    engine.runAndWait()
                except Exception as exc:  # noqa: BLE001
                    log.warning("TTS speak failed: %s", exc)
                finally:
                    self._queue.task_done()

            engine.stop()
            log.info("TTS worker stopped cleanly")

        except Exception as exc:  # noqa: BLE001
            log.error("TTS worker encountered fatal error: %s", exc)
            self._available = False
