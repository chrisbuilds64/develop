"""Declared fields: what a person may set on a case besides its title — the worklist's assignee, due date, priority, origin.

An application declares them in `theme.json` under `fields`; nothing here names one:

    "fields": {"assignee": {"kind": "person"}, "due": {"kind": "date"}, "priority": {"list": "priority"},
               "origin_ref": {"kind": "text"}}

A field is a value list (`list`: the key must be an offered entry, domain/lists.py), a person of `people.json`
(`kind: person`), a date `YYYY-MM-DD` (`kind: date`) or a line of text (`kind: text`, at most 200 characters). An empty
value clears the field. The step `set_fields` writes them, journaled and in the thread; a new case may carry them too.
"""

from __future__ import annotations

import re

from ..config import DomainConfig
from . import lists as value_lists

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KINDS = ("person", "date", "text")


class FieldError(Exception):
    """A value that is refused; the message is the sentence the person reads."""


def declared(config: DomainConfig) -> dict[str, dict]:
    doc = config.theme.get("fields") or {}
    return {str(k): v for k, v in doc.items() if isinstance(v, dict) and not str(k).startswith("$")}


def validate(config: DomainConfig, values: dict) -> dict:
    """{field: value} cleaned; an empty value stays "" (clear). Refuses an undeclared field and a value that does not fit."""
    fields = declared(config)
    out: dict = {}
    for key, raw in (values or {}).items():
        spec = fields.get(key)
        if spec is None:
            raise FieldError(f"'{key}' is not a field of this application")
        v = "" if raw is None else str(raw).strip()
        if v == "":
            out[key] = ""
            continue
        if spec.get("list"):
            e = value_lists.entry(config.lists, str(spec["list"]), v)
            if e is None:
                raise FieldError(f"'{v}' is not in the list '{spec['list']}'")
            if e["status"] not in value_lists.OFFERED:
                raise FieldError(f"'{v}' is retired and no longer offered")
            out[key] = e["key"]
        elif spec.get("kind") == "person":
            p = config.person(v)
            if p is None:
                raise FieldError(f"'{v}' is nobody here")
            out[key] = p.id
        elif spec.get("kind") == "date":
            if not DATE.match(v):
                raise FieldError(f"'{v}' is not a date (YYYY-MM-DD)")
            out[key] = v
        else:
            if len(v) > 200 or "\n" in v:
                raise FieldError(f"'{key}' takes one line of at most 200 characters")
            out[key] = v
    return out


def split(config: DomainConfig, values: dict) -> tuple[dict, dict]:
    """A new case's values: those the declared fields take, and the rest (for the value lists that ask on creation)."""
    fields = declared(config)
    return ({k: v for k, v in (values or {}).items() if k in fields},
            {k: v for k, v in (values or {}).items() if k not in fields})
