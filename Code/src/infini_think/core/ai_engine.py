"""
infini_think.core.ai_engine
============================
Low-level interface to the local Ollama LLM.

Sends prompts to the Ollama REST API (``/api/generate``) and returns the
complete text response.  No LangChain or external frameworks required.

Usage::

    from infini_think.core.ai_engine import AIEngine

    engine = AIEngine()
    if engine.is_available():
        response = engine.generate("What is 2 + 2?")
        print(response)
"""

from __future__ import annotations

import json
from typing import Generator

import requests

from infini_think.config.settings import settings
from infini_think.utils.logger import get_logger

log = get_logger(__name__)


class AIEngineError(Exception):
    """Raised when the AI engine encounters an unrecoverable error."""


class AIEngine:
    """Wrapper around the Ollama REST API.

    Attributes:
        model: The Ollama model tag to use (e.g. ``"llama3"``).
        base_url: Base URL for the Ollama server.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.ollama_timeout

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        log.info("AIEngine initialised — model=%s url=%s", self.model, self.base_url)

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check whether the Ollama server is reachable.

        Returns:
            ``True`` if the server responds to a health-check request.
        """
        try:
            resp = self._session.get(
                f"{self.base_url}/api/tags", timeout=5
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException as exc:
            log.warning("Ollama not reachable: %s", exc)
            return False

    def list_models(self) -> list[str]:
        """Return a list of locally available Ollama model names.

        Returns:
            List of model name strings, empty list on failure.
        """
        try:
            resp = self._session.get(
                f"{self.base_url}/api/tags", timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not list models: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a prompt to Ollama and return the complete response text.

        Args:
            prompt: The user-facing prompt string.
            system: An optional system/instruction prompt prepended to context.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            The model's text response as a single string.

        Raises:
            AIEngineError: If Ollama is unavailable or returns an error.
        """
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 512,
            },
        }
        if system:
            payload["system"] = system

        log.debug("Sending prompt to Ollama (len=%d chars)", len(prompt))

        try:
            resp = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise AIEngineError(
                "Cannot connect to Ollama. Make sure it is running: `ollama serve`"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise AIEngineError(
                f"Ollama request timed out after {self.timeout}s."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise AIEngineError(f"Ollama HTTP error: {exc}") from exc

        try:
            data = resp.json()
            response_text: str = data.get("response", "").strip()
        except json.JSONDecodeError as exc:
            raise AIEngineError(f"Ollama returned non-JSON: {resp.text[:200]}") from exc

        log.debug("Received response (len=%d chars)", len(response_text))
        return response_text

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> Generator[str, None, None]:
        """Stream tokens from Ollama as they are generated.

        Args:
            prompt: The user prompt.
            system: Optional system instruction.
            temperature: Sampling temperature.

        Yields:
            Individual token strings as they arrive.

        Raises:
            AIEngineError: On connection or protocol errors.
        """
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        try:
            with self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token: str = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.RequestException as exc:
            raise AIEngineError(f"Streaming error: {exc}") from exc
