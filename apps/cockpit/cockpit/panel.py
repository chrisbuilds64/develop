"""The panel contract: what a module reports, checked before it is shown.

A panel is validated in two passes — shape against `schemas/panel.schema.json`,
then freshness. A panel that fails either is not rendered with its numbers; it
is rendered as a card that says so. An empty card is honest. A wrong number on
a screen in front of a client is not.

The checker covers the schema subset this project uses. It uses the
`jsonschema` package when installed and falls back to the built-in checker
otherwise, so the cockpit has no third-party dependency for its own contract.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

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


# ---------------------------------------------------------------- checker

def _resolve(ref: str, root: dict):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def _check(node, schema, root, path="$", out=None):
    out = out if out is not None else []
    if "$ref" in schema:
        return _check(node, _resolve(schema["$ref"], root), root, path, out)
    t = schema.get("type")
    if t:
        want = t if isinstance(t, list) else [t]
        types = {"object": dict, "array": list, "string": str, "integer": int,
                 "number": (int, float), "boolean": bool, "null": type(None)}
        ok = any(isinstance(node, types[w]) and not (w in ("integer", "number") and isinstance(node, bool))
                 for w in want)
        if not ok:
            out.append(f"{path}: expected {'/'.join(want)}, got {type(node).__name__}")
            return out
    if "enum" in schema and node not in schema["enum"]:
        out.append(f"{path}: {node!r} not in {schema['enum']}")
    if isinstance(node, str):
        if "pattern" in schema and not re.search(schema["pattern"], node):
            out.append(f"{path}: {node!r} does not match the required form")
        if len(node) < schema.get("minLength", 0):
            out.append(f"{path}: empty")
    if isinstance(node, list):
        if len(node) > schema.get("maxItems", 10**9):
            out.append(f"{path}: more than {schema['maxItems']} entries")
        for i, v in enumerate(node):
            if "items" in schema:
                _check(v, schema["items"], root, f"{path}[{i}]", out)
    if isinstance(node, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in node:
                out.append(f"{path}: field '{key}' is missing")
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    out.append(f"{path}: unknown field '{key}' — define it in the schema first")
        for key, val in node.items():
            if key in props:
                _check(val, props[key], root, f"{path}.{key}", out)
    return out


def shape_errors(panel: dict, schema: dict | None = None) -> list[str]:
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        import jsonschema  # type: ignore
        v = jsonschema.Draft202012Validator(schema)
        return [f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in v.iter_errors(panel)]
    except ImportError:
        return _check(panel, schema, schema)


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
