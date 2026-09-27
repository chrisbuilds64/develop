"""Review entries: the item inside review.md — written once, read back as data.

An entry is a heading `## REV-NNN — <title>`, one head line with its attributes,
and the text below. review.schema.json at the pipeline root says which
attributes exist and which values they take. This module is the one place that
knows the shape; review_append.py writes it, verify.py and the surface read it.

    ## REV-004 — v3 checked against the transcript
    **Date:** 2026-09-24 14:05 · **Author:** Axel · **For:** Akhil · **Status:** open · **Stage:** 30-review-human · **Resolves:** REV-002

    text …
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys

try:
    from cockpit.schema import check as schema_check
except ImportError:                                   # run by hand from the source tree, outside the cockpit's interpreter
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from cockpit.schema import check as schema_check

HEAD = re.compile(r"^## (REV-\d{3}) — (.+?)\s*$", re.M)
ATTR = re.compile(r"\*\*([A-Za-z]+):\*\*\s*([^·\n]+?)(?=\s*·\s*\*\*|\s*$)", re.M)
KEYS = {"date": "Date", "author": "Author", "for": "For", "status": "Status", "stage": "Stage", "resolves": "Resolves"}


def load_schema(root: Path) -> dict | None:
    p = root / "review.schema.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_people(root: Path) -> list[dict] | None:
    """The one list of persons and agent instances, `people.json` at the pipeline root."""
    p = root / "people.json"
    return json.loads(p.read_text(encoding="utf-8")).get("people", []) if p.exists() else None


def person(value: str, people: list[dict] | None) -> str | None:
    """The name of the person `value` names — by id or name, case does not matter — or None."""
    v = (value or "").strip().lower()
    for x in people or []:
        if v in (x["id"].lower(), x["name"].lower()):
            return x["name"]
    return None


def parse(text: str) -> list[dict]:
    """Every REV entry in a review.md, in file order. Older free-form blocks are not entries."""
    out = []
    heads = list(HEAD.finditer(text))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[m.end():end]
        entry = {"id": m.group(1), "title": m.group(2).strip()}
        lines = block.strip("\n").split("\n", 1)
        attrs = dict(ATTR.findall(lines[0])) if lines and lines[0].startswith("**") else {}
        for key, label in KEYS.items():
            if label in attrs and attrs[label].strip() not in ("", "—"):
                entry[key] = attrs[label].strip()
        entry["text"] = (lines[1] if len(lines) > 1 else "").strip()
        out.append(entry)
    return out


def next_id(text: str) -> str:
    nums = [int(m.group(1)[4:]) for m in HEAD.finditer(text)]
    return f"REV-{max(nums, default=0) + 1:03d}"


def canonical(value: str, allowed: list[str]) -> str | None:
    """Match a value to the list, case-insensitively — 'akhil' from a login is 'Akhil' in the list."""
    for a in allowed:
        if a.lower() == str(value).strip().lower():
            return a
    return None


def check(entry: dict, schema: dict | None, people: list[dict] | None = None) -> list[str]:
    """The cockpit's one checker, prefixed with the entry's id; then the persons against people.json."""
    out = [f"{entry.get('id', '?')}: {x}" for x in schema_check(entry, schema)]
    if people is not None:
        for key in ("author", "for"):
            if entry.get(key) and person(entry[key], people) != entry[key]:
                out.append(f"{entry.get('id', '?')}: {key} = {entry[key]!r} is not a name in people.json")
    return out


def render(entry: dict) -> str:
    """One entry as it goes into the file."""
    head = [f"**Date:** {entry['date']}", f"**Author:** {entry['author']}", f"**For:** {entry.get('for') or '—'}",
            f"**Status:** {entry['status']}", f"**Stage:** {entry['stage']}"]
    if entry.get("resolves"):
        head.append(f"**Resolves:** {entry['resolves']}")
    return f"\n## {entry['id']} — {entry['title']}\n{' · '.join(head)}\n\n{entry['text'].strip()}\n"
