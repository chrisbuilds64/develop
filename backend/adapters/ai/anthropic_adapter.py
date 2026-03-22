"""
Anthropic Claude AI Adapter

Production implementation using the Anthropic API.
Reusable across all projects that need AI text generation.
"""
import os
from typing import List, Optional

import httpx

from .base import AIAdapter, Message, AIResponse


class AnthropicAdapter(AIAdapter):
    """
    Anthropic Claude API implementation.

    Uses httpx for async-capable HTTP calls.
    Default model: claude-sonnet-4-20250514
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var "
                "or pass api_key parameter."
            )

    def _build_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

    def _build_payload(
        self, messages: List[Message], **kwargs
    ) -> dict:
        system_messages = [m for m in messages if m.role == "system"]
        chat_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]

        payload = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": chat_messages,
        }

        if system_messages:
            payload["system"] = system_messages[0].content

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        return payload

    def complete(self, messages: List[Message], **kwargs) -> AIResponse:
        payload = self._build_payload(messages, **kwargs)

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.API_URL,
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data["content"][0]["text"]
        usage = data.get("usage", {})

        return AIResponse(
            content=content,
            model=data.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
            },
        )

    async def complete_async(self, messages: List[Message], **kwargs) -> AIResponse:
        """Async version of complete for use in FastAPI endpoints."""
        payload = self._build_payload(messages, **kwargs)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.API_URL,
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data["content"][0]["text"]
        usage = data.get("usage", {})

        return AIResponse(
            content=content,
            model=data.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
            },
        )

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError(
            "Anthropic does not provide embedding models. "
            "Use a dedicated embedding provider."
        )
