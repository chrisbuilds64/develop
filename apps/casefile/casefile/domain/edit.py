"""Editing a text file of a case (REQ-001 S-14 – S-16): the editor's draft becomes the next version, never a replacement.

A free note (`notes/<slug>.md`, REQ-001 S-17) is editable without being declared, while the application offers notes.
Which other files may be edited is the application's word (`"editable": true` in artifacts.json); the core adds what no
configuration can override (cases.editable). The preview goes through the reader's own renderer, so a draft looks as it
will be read; in the file that carries the acceptance criteria, the lines the gate could not read come with it.
"""

from __future__ import annotations

from ..config import DomainConfig
from ..store import FsStore, StoreError
from . import assets, criteria, notes
from .cases import editable


class NotEditable(Exception):
    """The file is not one the application lets a person edit."""


def _deliverable(store: FsStore, config: DomainConfig, case_id: str, file: str):
    stage = store.find(case_id)
    if stage is None:
        raise StoreError(f"case '{case_id}' not found")
    if file.startswith(f"{notes.FOLDER}/"):
        if not notes.enabled(config):
            raise NotEditable("this application does not offer notes")
        if not notes.is_note(file):
            raise NotEditable(f"'{file}' is not a note: notes/<a-z, 0-9 and dashes>.md")
        return None
    meta = store.case_json(case_id, "meta.json") if store.exists(f"{stage}/{case_id}/meta.json") else {}
    label = str(meta.get("label") or case_id.split("-", 1)[0])
    d = next((x for x in config.deliverables(label) if x.file == file), None)
    if d is None or not editable(d):
        raise NotEditable(f"'{file}' cannot be edited in a {label} case")
    return d


def criteria_file(config: DomainConfig) -> str:
    """The file whose acceptance criteria the gate reads (theme `criteria.file`, as cases.data reads it)."""
    crit = config.theme.get("criteria") if isinstance(config.theme.get("criteria"), dict) else {}
    return str(crit.get("file") or "task.md")


def preview(store: FsStore, config: DomainConfig, case_id: str, file: str, text: str) -> dict:
    """How the reader renders the draft (`kind`), and — in the criteria file — the lines the gate could not read. The
    rendering itself is the reader's (api/text.py); the domain does not draw."""
    _deliverable(store, config, case_id, file)
    return {"file": file, "kind": "md" if file.endswith(".md") else "plain",
            "unreadable": criteria.unreadable(text) if file == criteria_file(config) else None}


def save(store: FsStore, config: DomainConfig, case_id: str, file: str, text: str) -> str:
    """The draft as the next version of `file`. Returns the name written; the older versions stay as they are (C-06)."""
    d = _deliverable(store, config, case_id, file)
    if not text.strip():
        raise StoreError("the text is empty")
    if d is None:
        return notes.save(store, case_id, file, text)
    return assets.put(store, config, case_id, file, text.encode("utf-8"))
