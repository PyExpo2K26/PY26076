"""infini_think.interfaces – package init."""
from infini_think.interfaces.text_interface import UserMessage, AgentResponse, BaseInterface
from infini_think.interfaces.cli_interface import CLIInterface

__all__ = ["UserMessage", "AgentResponse", "BaseInterface", "CLIInterface"]
