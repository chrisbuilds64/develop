"""Any endpoint speaking the OpenAI chat completions shape.

This covers the on-premise case: local runtimes and self-hosted gateways
generally expose this interface, so an air-gapped client is a base_url
change rather than a new adapter.
"""

from __future__ import annotations

import os

import httpx

from . import Model, ModelError, Reply

# Mirrors the Anthropic adapter. See the note there on why this is a
# bound and not a budget.
MAX_TOKENS = 4096


class OpenAICompatModel(Model):
    @property
    def egress(self) -> bool:
        # A self-hosted endpoint inside the client network is not egress.
        # The operator declares this in the config and it is their claim,
        # recorded as such.
        return not self._profile.local

    def _send(self, prompt: str, context: list[str]) -> Reply:
        base_url = self._profile.base_url
        if not base_url:
            raise ModelError(
                f"Profile '{self._profile.name}' uses openai_compat but sets "
                "no base_url."
            )

        headers = {"content-type": "application/json"}
        if self._profile.api_key_env:
            api_key = os.environ.get(self._profile.api_key_env)
            if not api_key:
                raise ModelError(
                    f"Environment variable {self._profile.api_key_env} is not set."
                )
            headers["authorization"] = f"Bearer {api_key}"

        messages = [{"role": "user", "content": part} for part in context]
        messages.append({"role": "user", "content": prompt})

        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json={
                    "model": self._profile.model or "local",
                    "messages": messages,
                    "max_tokens": MAX_TOKENS,
                },
                timeout=120.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelError(f"Anfrage an {base_url} fehlgeschlagen: {exc}") from exc

        body = response.json()
        choices = body.get("choices", [])
        usage = body.get("usage", {})

        if choices and choices[0].get("finish_reason") == "length":
            raise ModelError(
                "Die Antwort des Modells wurde am Token-Limit abgeschnitten "
                "und ist unvollständig."
            )
        return Reply(
            text=choices[0].get("message", {}).get("content", "") if choices else "",
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
