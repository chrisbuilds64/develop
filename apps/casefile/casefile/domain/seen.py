"""Read and unread, per person: `_seen/<person>.json` at the pipeline root holds, per case, the newest thread entry the
person has seen. A case is unread while it has never been opened or somebody else has written in it since; what the
person wrote themselves never makes it unread, and a closed case (out, archive) has nothing new to read.

Not a step: a read marker belongs to one person and changes nothing in the case, so it stays out of the journal, the
thread and the rhythm. It is written under its own lock, atomically, like every file the core writes.
"""

from __future__ import annotations

import re

from ..config import DomainConfig
from ..models import Case
from ..store import FsStore

PERSON = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CLOSED = ("out", "archive")


def _rel(person: str) -> str:
    if not PERSON.match(person or ""):
        raise ValueError(f"'{person}' is not a person id")
    return f"_seen/{person}.json"


def load(store: FsStore, person: str | None) -> dict[str, str]:
    """case id → the newest entry id the person has seen ('' = opened before it had any entry)."""
    if not person or not PERSON.match(person):
        return {}
    rel = _rel(person)
    try:
        doc = store.read_json(rel) if store.exists(rel) else {}
    except (OSError, ValueError):
        return {}
    cases = doc.get("cases") if isinstance(doc, dict) else None
    return {str(k): str(v) for k, v in (cases or {}).items()} if isinstance(cases, dict) else {}


def _newest_by_others(config: DomainConfig, case: Case, person: str) -> str:
    me = config.person(person)
    names = {person.lower()} | ({me.id.lower(), me.name.lower()} if me else set())
    ids = [e.id for e in case.entries if (e.author or "").strip().lower() not in names]
    return max(ids, default="")


def unread(config: DomainConfig, case: Case, person: str | None, seen: dict[str, str]) -> bool:
    if not person:
        return False
    stage = config.stage(case.stage)
    if stage is not None and stage.group in CLOSED:
        return False
    if case.id not in seen:
        return True
    return _newest_by_others(config, case, person) > seen[case.id]


def mark(store: FsStore, config: DomainConfig, case: Case, person: str, is_unread: bool) -> bool:
    """Read: remember the newest entry. Unread: forget the case, so it reads as new again. Returns the new state."""
    rel = _rel(person)
    with store.lock(f"_seen-{person}"):
        doc = store.read_json(rel) if store.exists(rel) else {}
        cases = dict(doc.get("cases") or {}) if isinstance(doc, dict) else {}
        if is_unread:
            cases.pop(case.id, None)
        else:
            cases[case.id] = max((e.id for e in case.entries), default="")
        store.write_json(rel, {"cases": dict(sorted(cases.items()))})
    return unread(config, case, person, load(store, person))
