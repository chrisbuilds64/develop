"""A new kind of case from Setup (design hand-back, 2026-11-06): "Add a schema".

A kind of case is two things the configuration already has: an entry in the value list that fills the case's label
(its key starts every case number, its words name it) and a format in artifacts.json (the documents it collects).
A new kind starts from an existing one: the entry is added the way every list entry is (lists.put_entry, logged), and
the format is copied into the tree's own artifacts.json, which the configuration lays over the domain's. Stages and
rules are the workspace's and stay as they are, so a new kind runs the same way its model does from the first case.
"""

from __future__ import annotations

import copy
import json

from . import lists as value_lists


class SchemaError(Exception):
    """A sentence for the person."""


def label_list(config) -> str | None:
    """The list whose entries are the kinds of case: the one that fills the label."""
    return next((lid for lid, l in config.lists.items() if l.get("field") == "label"), None)


def add(store, config, by: str, key: str, word: dict, based_on: str, step_id: str) -> dict:
    lid = label_list(config)
    if lid is None:
        raise SchemaError("This workspace has no list of kinds of case.")
    formats = config.artifacts.get("formats") or {}
    key = (key or "").strip().upper()
    if based_on not in formats:
        raise SchemaError("Pick an existing kind to start from.")
    if key in formats:
        raise SchemaError(f"There is already a kind with the code '{key}'.")
    # A tree's artifacts.json replaces the domain's whole (config.py), it is not laid over it. So a tree without its own
    # file starts from everything it reads today, never from nothing — else the next load knows only the new kind.
    # A tree file that cannot be read is refused, not written over.
    path = store.root / "artifacts.json"
    if path.is_file():
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SchemaError("This workspace's list of documents cannot be read; nothing was changed.") from exc
    try:
        line = value_lists.put_entry(store, config, by, lid, key, word, None, None, "active", step_id)
    except value_lists.ListError as exc:
        raise SchemaError(str(exc)) from exc
    with store.lock("_lists"):
        tree = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else copy.deepcopy(config.artifacts)
        model = copy.deepcopy(formats[based_on])
        tree.setdefault("formats", {})[key] = model
        store.write_json("artifacts.json", tree)
        config.artifacts.setdefault("formats", {})[key] = copy.deepcopy(model)
    return {**line, "schema": key, "based_on": based_on}
