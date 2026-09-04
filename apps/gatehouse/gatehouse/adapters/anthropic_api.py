"""Claude through the official Anthropic SDK.

The module is named anthropic_api rather than anthropic so that
`import anthropic` inside it reaches the SDK and not this file.

Credentials are never touched here. A bare `Anthropic()` resolves, in
order: ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, a signed-in profile on
disk, workload identity. Which of those a client uses is a question for
their IT department, and Gatehouse has no business pre-empting it.

An explicit api_key_env in the profile overrides that resolution, for
the case where a client keeps several accounts apart on one machine.
"""

from __future__ import annotations

import os

from . import Model, ModelError, Reply

DEFAULT_MODEL = "claude-opus-5"

# A follow-up is two lines. A reading over a whole run is a page or two.
# The cap is an upper bound and not a spend: a short reply is billed
# short. It exists so a runaway reply cannot run away far.
MAX_TOKENS = 4096

_TRUNCATED = (
    "Die Antwort des Modells wurde am Token-Limit abgeschnitten und ist "
    "unvollständig. Ein abgeschnittener Text sieht fertig aus, ist es aber "
    "nicht, und darf niemandem als Ergebnis gezeigt werden."
)

_NO_CREDENTIALS = (
    "Keine Anmeldung gefunden. Gatehouse setzt selbst keine Zugangsdaten; "
    "es benutzt, was auf dem Rechner eingerichtet ist. Entweder eine "
    "Anmeldung einrichten, oder im Profil api_key_env auf eine gesetzte "
    "Umgebungsvariable zeigen lassen. Ein Claude-Code-Login zählt nicht: "
    "das ist eine getrennte Anmeldung, die dieses Programm nicht sieht."
)


class AnthropicModel(Model):
    def __init__(self, profile, audit) -> None:
        super().__init__(profile, audit)
        try:
            import anthropic
        except ImportError as exc:
            raise ModelError(
                "The 'anthropic' package is not installed. "
                "Run: pip install -r requirements.txt"
            ) from exc

        kwargs = {}
        if profile.api_key_env:
            api_key = os.environ.get(profile.api_key_env)
            if not api_key:
                raise ModelError(
                    f"Profile '{profile.name}' names api_key_env "
                    f"'{profile.api_key_env}', but that variable is not set. "
                    "Remove the setting to use the machine's own sign-in, or "
                    "export the variable."
                )
            kwargs["api_key"] = api_key
        if profile.base_url:
            kwargs["base_url"] = profile.base_url

        try:
            self._client = anthropic.Anthropic(**kwargs)
        except TypeError as exc:
            # The SDK raises a bare TypeError when it can resolve no
            # credentials at all. That is the single most likely failure
            # on a fresh machine, and it must not reach an operator as a
            # stack trace.
            raise ModelError(_NO_CREDENTIALS) from exc

        # AnthropicError is the SDK's base class; APIError alone misses
        # connection and authentication failures.
        self._errors = anthropic.AnthropicError

    def _send(self, prompt: str, context: list[str]) -> Reply:
        messages = [{"role": "user", "content": part} for part in context]
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.messages.create(
                model=self._profile.model or DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                messages=messages,
            )
        except self._errors as exc:
            raise ModelError(f"Anfrage an Anthropic fehlgeschlagen: {exc}") from exc
        except TypeError as exc:
            raise ModelError(_NO_CREDENTIALS) from exc

        # Truncation is the one failure that arrives looking like a
        # success. Without this check a reading stops mid-sentence and the
        # page presents it as finished.
        if response.stop_reason == "max_tokens":
            raise ModelError(_TRUNCATED)

        text = "".join(b.text for b in response.content if b.type == "text")
        return Reply(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
