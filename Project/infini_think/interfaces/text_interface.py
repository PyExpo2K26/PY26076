"""
infini_think.interfaces.text_interface
========================================
Shared data types and base class used by all InfiniThink interfaces
(GUI, CLI, Voice).  Defines the interface contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class UserMessage:
    """Represents a message submitted by the user."""
    text: str
    source: str = "text"         # "text" | "voice" | "cli"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResponse:
    """Represents the AI agent's response to a user message."""
    success: bool
    output: str
    tool: str = "unknown"
    args: list = field(default_factory=list)
    elapsed: float = 0.0
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_result(cls, result: dict[str, Any]) -> "AgentResponse":
        """Create an AgentResponse from an executor result dict."""
        return cls(
            success=result.get("success", False),
            output=result.get("output", ""),
            tool=result.get("tool", "unknown"),
            args=result.get("args", []),
            elapsed=result.get("elapsed", 0.0),
            error=result.get("error"),
        )


class BaseInterface(ABC):
    """Abstract base class for all InfiniThink interaction interfaces."""

    @abstractmethod
    def run(self) -> None:
        """Start the interface loop."""
        ...

    @abstractmethod
    def display_response(self, response: AgentResponse) -> None:
        """Display a single agent response to the user."""
        ...
