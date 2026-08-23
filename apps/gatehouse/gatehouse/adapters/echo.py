"""No model at all.

Walks a pack end to end without sending anything anywhere. This is the
adapter to use when demonstrating the flow to a client before their data
protection question is settled, and the one the tests run against.
"""

from __future__ import annotations

from . import Model, Reply


class EchoModel(Model):
    @property
    def egress(self) -> bool:
        return False

    def _send(self, prompt: str, context: list[str]) -> Reply:
        return Reply(text="")
