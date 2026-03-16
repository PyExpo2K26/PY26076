"""
infini_think.interfaces.voice_interface
=========================================
Orchestrates the full voice interaction loop:
  Mic → STT → AI interpreter → Executor → TTS → Speaker

This can be run standalone (headless voice-only mode) or called from the GUI.
"""

from __future__ import annotations

import threading
import time

from infini_think.core.ai_engine import AIEngine
from infini_think.core.command_interpreter import CommandInterpreter
from infini_think.core.planner import TaskPlanner
from infini_think.core.executor import Executor
from infini_think.interfaces.text_interface import AgentResponse
from infini_think.voice.speech_to_text import SpeechToText
from infini_think.voice.text_to_speech import TextToSpeech
from infini_think.utils.logger import get_logger

log = get_logger(__name__)


class VoiceInterface:
    """Standalone voice-only interface for InfiniThink.

    Listens continuously for speech, processes each utterance through
    the AI pipeline, and speaks the result.
    """

    def __init__(self) -> None:
        self._engine = AIEngine()
        self._interpreter = CommandInterpreter(self._engine)
        self._planner = TaskPlanner(self._engine, self._interpreter)
        self._executor = Executor()
        self._tts = TextToSpeech()
        self._stt = SpeechToText(
            on_result=self._on_speech,
            on_error=self._on_error,
        )
        self._running = False

    def run(self) -> None:
        """Start the voice interaction loop (blocking)."""
        print("🎤 InfiniThink Voice Interface — press Ctrl+C to exit")
        self._tts.speak("InfiniThink voice interface is ready. How can I help you?")
        self._running = True
        self._stt.start_listening()
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self._stt.stop_listening()
            self._tts.speak("Goodbye!")
            self._tts.stop()
            print("\nVoice interface stopped.")

    def display_response(self, response: AgentResponse) -> None:
        icon = "✅" if response.success else "❌"
        print(f"{icon}  {response.output}")

    def _on_speech(self, text: str) -> None:
        """Process a recognised speech utterance."""
        print(f"\n👤 You said: {text}")
        self._tts.speak("Processing your request.")

        plan = self._planner.plan(text)
        results = self._executor.execute_plan(plan)

        for result in results:
            resp = AgentResponse.from_result(result)
            self.display_response(resp)
            if resp.success:
                self._tts.speak(resp.output)
            else:
                self._tts.speak(f"I encountered an error: {resp.output}")

        # Restart listening after processing
        self._stt.start_listening()

    def _on_error(self, msg: str) -> None:
        print(f"⚠️  Voice Error: {msg}")
        self._tts.speak("I had trouble hearing you. Please try again.")
