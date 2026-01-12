"""
AI Adapter Interface

Basis-Interface für alle AI-Provider.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Message:
    """Chat message"""
    role: str  # system, user, assistant
    content: str


@dataclass
class AIResponse:
    """AI response"""
    content: str
    model: str
    usage: Optional[dict] = None


class AIAdapter(ABC):
    """
    Abstract base class for AI adapters.

    Implementierungen: OpenAI, Anthropic, Mock
    """

    @abstractmethod
    def complete(self, messages: List[Message], **kwargs) -> AIResponse:
        """
        Generate completion from messages.

        Args:
            messages: List of chat messages
            **kwargs: Provider-specific options

        Returns:
            AI response
        """
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        pass
