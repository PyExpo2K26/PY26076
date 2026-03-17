"""
infini_think.voice.speech_to_text
===================================
Speech-to-text module using the ``SpeechRecognition`` library.

Recognition runs on a **background thread** so it never blocks the GUI
event loop.  Results are delivered through a callback function.

Usage::

    from infini_think.voice.speech_to_text import SpeechToText

    def on_result(text: str) -> None:
        print("Heard:", text)

    def on_error(msg: str) -> None:
        print("Error:", msg)

    stt = SpeechToText(on_result=on_result, on_error=on_error)
    stt.start_listening()   # non-blocking
    # ... later ...
    stt.stop_listening()
"""

from __future__ import annotations

import threading
from typing import Callable

from infini_think.config.settings import settings
from infini_think.utils.logger import get_logger

log = get_logger(__name__)


class SpeechToText:
    """Wrapper around ``SpeechRecognition`` that runs in a background thread.

    Args:
        on_result: Callback called with the recognised text string.
        on_error:  Callback called with an error description string.
    """

    def __init__(
        self,
        on_result: Callable[[str], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._on_result = on_result
        self._on_error = on_error or (lambda msg: log.warning("STT error: %s", msg))
        self._listening = False
        self._thread: threading.Thread | None = None

        # Lazy import — SpeechRecognition is optional at module-load time
        try:
            import speech_recognition as sr  # noqa: F401
            self._sr_available = True
        except ImportError:
            self._sr_available = False
            log.warning(
                "SpeechRecognition not installed. "
                "Run: pip install SpeechRecognition pyaudio"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Return True if the SpeechRecognition library is importable."""
        return self._sr_available

    def start_listening(self) -> None:
        """Begin microphone capture on a background thread (non-blocking)."""
        if not self._sr_available:
            self._on_error(
                "SpeechRecognition is not installed. "
                "Please run: pip install SpeechRecognition pyaudio"
            )
            return

        if self._listening:
            log.debug("Already listening — ignoring start request")
            return

        self._listening = True
        self._thread = threading.Thread(
            target=self._recognition_loop,
            name="stt-worker",
            daemon=True,
        )
        self._thread.start()
        log.info("STT listening thread started")

    def stop_listening(self) -> None:
        """Signal the background thread to stop after the current phrase."""
        self._listening = False
        log.info("STT stop requested")

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _recognition_loop(self) -> None:
        """Recognition loop executed on the background thread."""
        import speech_recognition as sr  # noqa: PLC0415

        recogniser = sr.Recognizer()
        recogniser.energy_threshold = settings.stt_energy_threshold
        recogniser.pause_threshold = 0.8
        recogniser.dynamic_energy_threshold = True

        try:
            with sr.Microphone() as source:
                log.info("Adjusting for ambient noise …")
                recogniser.adjust_for_ambient_noise(source, duration=1)
                log.info("Listening for speech …")

                while self._listening:
                    try:
                        audio = recogniser.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=settings.stt_phrase_timeout,
                        )
                    except sr.WaitTimeoutError:
                        continue  # No speech detected; keep looping

                    if not self._listening:
                        break

                    try:
                        text: str = recogniser.recognize_google(audio)
                        log.info("Recognised: %r", text)
                        self._on_result(text)
                    except sr.UnknownValueError:
                        self._on_error("Could not understand the audio. Please try again.")
                    except sr.RequestError as exc:
                        self._on_error(
                            f"Google Speech Recognition unavailable: {exc}. "
                            "Check your internet connection."
                        )

        except OSError as exc:
            msg = f"Microphone not found or not accessible: {exc}"
            log.error(msg)
            self._on_error(msg)
        finally:
            self._listening = False
            log.info("STT thread finished")
