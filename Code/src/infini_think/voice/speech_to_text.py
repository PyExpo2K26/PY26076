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
        trigger_phrase: str | None = None,
    ) -> None:
        self._on_result = on_result
        self._on_error = on_error or (lambda msg: log.warning("STT error: %s", msg))
        self._trigger_phrase = trigger_phrase
        self._is_listening = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Check for dependencies
        try:
            import speech_recognition as sr  # noqa: F401
            import pyaudio  # noqa: F401
            self._available = True
        except ImportError as exc:
            self._available = False
            missing = "pyaudio" if "pyaudio" in str(exc) else "SpeechRecognition"
            log.warning(f"{missing} not installed. Speech recognition unavailable.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Return True if SpeechRecognition and PyAudio are both present."""
        return self._available

    def start_listening(self) -> None:
        """Begin microphone capture on a background thread (non-blocking)."""
        if not self._available:
            self._on_error(
                "Speech recognition dependencies (SpeechRecognition, PyAudio) are missing.\n\n"
                "On Python 3.14, you may need to install PyAudio from a wheel or use a stable Python version (3.11/3.12).\n"
                "Try: pip install pipwin && pipwin install pyaudio"
            )
            return

        if self._is_listening:
            log.debug("Already listening — ignoring start request")
            return

        self._is_listening = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._recognition_loop,
            name="stt-worker",
            daemon=True,
        )
        self._thread.start()
        log.info("STT listening thread started (Trigger: %r)", self._trigger_phrase)

    def set_trigger_phrase(self, phrase: str | None) -> None:
        """Update the trigger phrase dynamically."""
        self._trigger_phrase = phrase
        log.debug("STT trigger phrase updated to: %r", phrase)

    def stop_listening(self) -> None:
        """Signal the background thread to stop after the current phrase."""
        if self._is_listening:
            self._stop_event.set()
            log.info("STT stop requested. Waiting for thread...")
            
            # Wait for the thread to finish if it's still running
            thread = self._thread
            if thread and thread.is_alive():
                thread.join(timeout=5)  # Increased from 2 to avoid warnings on slow I/O
                if thread.is_alive():
                    log.warning("STT thread did not terminate gracefully within 5s.")
            
            self._is_listening = False
            self._thread = None
        else:
            log.debug("Not listening — ignoring stop request")

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _recognition_loop(self) -> None:
        """Recognition loop executed on the background thread."""
        import speech_recognition as sr  # noqa: PLC0415

        recogniser = sr.Recognizer()
        recogniser.energy_threshold = 300 # More sensitive baseline (default is often higher)
        recogniser.pause_threshold = 0.8 # Don't cut off instantly if user inhales (was 0.6)
        recogniser.phrase_threshold = 0.2 # Faster trigger on small sounds 
        recogniser.non_speaking_duration = 0.5 # Keeps recording running through micro-pauses
        recogniser.dynamic_energy_threshold = True
        recogniser.dynamic_energy_adjustment_damping = 0.15
        recogniser.dynamic_energy_ratio = 1.5

        try:
            with sr.Microphone() as source:
                log.info("Adjusting for ambient noise (1.0s) …")
                recogniser.adjust_for_ambient_noise(source, duration=1.0) # Longer calibration for better noise floor
                log.info("Listening for speech (Energy Threshold: %d) …", recogniser.energy_threshold)

                while not self._stop_event.is_set():
                    try:
                        audio = recogniser.listen(
                            source,
                            timeout=2.0, # Check exit flag every 2 seconds
                            phrase_time_limit=15, # Allow users to say much longer, complex commands
                        )
                        log.debug("Audio captured, sending to recognizer …")
                    except sr.WaitTimeoutError:
                        continue  # No speech; keep checking stop event

                    if self._stop_event.is_set():
                        break

                    try:
                        raw_text: str = recogniser.recognize_google(audio)
                        log.info("Recognised: %r", raw_text)
                        
                        text = raw_text.strip()
                        if not text:
                            continue

                        trigger = self._trigger_phrase
                        if trigger:
                            lower_text = text.lower()
                            lower_trigger = trigger.lower()
                            
                            if lower_trigger in lower_text:
                                # Found the trigger!
                                # Extract whatever follows it
                                parts = lower_text.split(lower_trigger, 1)
                                command = parts[1].strip()
                                
                                # Clean up common punctuation that recognize_google might add
                                if command.startswith(",") or command.startswith(":"):
                                    command = command[1:].strip()
                                
                                if command:
                                    log.info("Trigger word heard! Command: %r", command)
                                    self._on_result(command)
                                else:
                                    # Just the wake word was heard.
                                    log.info("Trigger word heard but no command followed. Waiting for next phrase...")
                                    self.set_trigger_phrase(None) # Allow any text next
                                    self._on_result("__WAKE__")
                            else:
                                log.debug("Speech ignored (did not contain trigger phrase)")
                        else:
                            # Direct mode — send everything
                            self._on_result(text)

                    except sr.UnknownValueError:
                        pass # Silently ignore unrecognised speech to keep loop alive
                    except sr.RequestError as exc:
                        self._on_error(f"STT Service error: {exc}")
                        # Don't break on API error, maybe connection was just flaky
                        # but wait a bit to avoid hammering
                        import time
                        time.sleep(2)

        except (OSError, AttributeError) as exc:
            missing_pyaudio = isinstance(exc, AttributeError) and "PyAudio" in str(exc)
            msg = (
                "PyAudio not found. Please install it to use voice features."
                if missing_pyaudio else f"Microphone error: {exc}"
            )
            log.error(msg)
            self._on_error(msg)
        finally:
            self._is_listening = False
            log.info("STT thread finished")
