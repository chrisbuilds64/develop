"""
Mock AI Adapter

Für Tests und Entwicklung.
"""
from typing import List

from .base import AIAdapter, Message, AIResponse


class MockAIAdapter(AIAdapter):
    """
    Mock implementation for testing.

    Gibt vordefinierte Antworten zurück.
    """

    def __init__(self, default_response: str = "This is a mock response."):
        self.default_response = default_response

    def complete(self, messages: List[Message], **kwargs) -> AIResponse:
        """Return mock response"""
        return AIResponse(
            content=self.default_response,
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )

    def embed(self, text: str) -> List[float]:
        """Return mock embedding"""
        # Einfacher deterministischer Mock basierend auf Text-Länge
        return [0.1] * 384  # Typische Embedding-Dimension
