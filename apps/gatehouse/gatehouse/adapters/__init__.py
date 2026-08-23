"""Model adapters.

One interface, deliberately narrow: text in, text out (ADR-011). Every
call passes through `Model.ask`, which logs before it sends. A new
adapter therefore cannot ship without an audit trail.

Adapters never resolve credentials themselves. That is the environment's
job, and hard-coding one way to authenticate would rule out the others
without anyone deciding to.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..audit import AuditLog
from ..config import Config, ModelProfile


class ModelError(Exception):
    """Raised with a message meant for an operator, not a stack trace."""


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class Model(ABC):
    def __init__(self, profile: ModelProfile, audit: AuditLog) -> None:
        self._profile = profile
        self._audit = audit

    @property
    def egress(self) -> bool:
        """Whether a call actually leaves this machine.

        Logged with every call. Without it an adapter that sends nothing
        produces entries indistinguishable from one that ships client
        answers to a public API, and the log stops answering the only
        question it exists to answer.
        """
        return True

    def ask(self, task: str, prompt: str, context: list[str] | None = None) -> str:
        """Send one prompt, return the reply. Logged before it is sent."""
        payload = list(context or []) + [prompt]
        self._audit.record(
            event="model_call",
            task=task,
            egress=self.egress,
            profile=self._profile.name,
            adapter=self._profile.adapter,
            destination=self._profile.destination,
            local=self._profile.local,
            model=self._profile.model,
            sent=payload,
            chars_sent=sum(len(part) for part in payload),
        )
        reply = self._send(prompt, context or [])
        self._audit.record(
            event="model_reply",
            task=task,
            egress=self.egress,
            profile=self._profile.name,
            adapter=self._profile.adapter,
            model=self._profile.model,
            chars_received=len(reply.text),
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
        )
        return reply.text

    @abstractmethod
    def _send(self, prompt: str, context: list[str]) -> Reply: ...


class Registry:
    """Resolves a task to the model profile configured for it.

    Instances are cached per profile, so two tasks pointing at the same
    profile share one client and one connection pool.
    """

    def __init__(self, config: Config, audit: AuditLog) -> None:
        self._config = config
        self._audit = audit
        self._cache: dict[str, Model] = {}

    def for_task(self, task: str) -> Model:
        profile = self._config.profile_for(task)
        if profile.name not in self._cache:
            self._cache[profile.name] = build(profile, self._audit)
        return self._cache[profile.name]


def build(profile: ModelProfile, audit: AuditLog) -> Model:
    from .anthropic_api import AnthropicModel
    from .echo import EchoModel
    from .openai_compat import OpenAICompatModel

    adapters = {
        "echo": EchoModel,
        "anthropic": AnthropicModel,
        "openai_compat": OpenAICompatModel,
    }
    try:
        return adapters[profile.adapter](profile, audit)
    except KeyError:
        raise ModelError(
            f"Profile '{profile.name}' names adapter '{profile.adapter}', "
            f"which does not exist. Available: {', '.join(sorted(adapters))}."
        ) from None
