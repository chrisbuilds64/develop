"""The panel contract: what a module reports, checked before it is shown.

A panel is validated in two passes — shape against `schemas/panel.schema.json`,
then freshness. A panel that fails either is not rendered with its numbers; it
is rendered as a card that says so. An empty card is honest. A wrong number on
a screen in front of a client is not.

The shape check uses the `jsonschema` package when installed and the cockpit's
own checker (`schema.py`) otherwise, so the contract needs no third-party
dependency.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .schema import check

SCHEMA_PATH = Path(__file__).parent / "schemas" / "panel.schema.json"
STATES = ("ok", "attention", "blocked")


@dataclass
class Card:
    """What the template renders: either a valid panel, or the reason it is not."""
    module_id: str
    panel: dict | None
    verdict: str                      # "ok" | "stale" | "denied" | "error" | "invalid"
    reason: str = ""
    problems: list[str] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return self.verdict == "ok"


def shape_errors(panel: dict, schema: dict | None = None) -> list[str]:
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        import jsonschema  # type: ignore
        v = jsonschema.Draft202012Validator(schema)
        return [f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in v.iter_errors(panel)]
    except ImportError:
        return check(panel, schema)


def is_stale(as_of: str, hours: int, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now().astimezone()
    stamp = dt.datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    return (now - stamp) > dt.timedelta(hours=hours)


def evaluate(module_id: str, panel: dict, stale_after_hours: int) -> Card:
    """Shape first, then freshness. Both must pass for the numbers to show."""
    problems = shape_errors(panel)
    if problems:
        return Card(module_id, panel, "invalid", "panel does not match the contract", problems)
    if is_stale(panel["as_of"], stale_after_hours):
        return Card(module_id, panel, "stale", f"older than {stale_after_hours} hours")
    return Card(module_id, panel, "ok")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")
