"""The working view behind a card.

A reader may offer two more functions beside `read`:

    detail(access, role, module, config) -> {"blocks": [...]}
    document(access, role, module, config, ref) -> {"title", "body"} | None

`detail` is checked against `schemas/detail.schema.json` before it is shown;
a broken detail becomes one error block, never a broken page. Markdown in a
`document` block is rendered here — readers send text, the surface makes HTML.
"""

from __future__ import annotations

import json
from pathlib import Path

import markdown

from .access import Denied
from .config import Config, Module, Role
from .panel import _check

SCHEMA_PATH = Path(__file__).parent / "schemas" / "detail.schema.json"
_MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])


def render_md(text: str) -> str:
    _MD.reset()
    return _MD.convert(text)


def blocks_for(reader, access, role: Role, module: Module, config: Config) -> list[dict]:
    fn = getattr(reader, "detail", None)
    if fn is None:
        return []
    try:
        detail = fn(access, role, module, config)
    except Denied as exc:
        return [{"kind": "document", "html": f"<p class='hint'>{exc}</p>"}]
    except Exception as exc:  # a broken reader is a block, not a crash
        return [{"kind": "document", "html": f"<p class='hint'>{type(exc).__name__}: {exc}</p>"}]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    problems = _check(detail, schema, schema)
    if problems:
        return [{"kind": "document", "html": "<p class='hint'>detail does not match the contract:<br>"
                                             + "<br>".join(problems) + "</p>"}]
    out = []
    for b in detail["blocks"]:
        if b["kind"] == "document" and "body" in b:
            b = dict(b)
            b["html"] = render_md(b.pop("body"))
        out.append(b)
    return out


def document_for(reader, access, role: Role, module: Module, config: Config, ref: str) -> dict | None:
    fn = getattr(reader, "document", None)
    if fn is None:
        return None
    doc = fn(access, role, module, config, ref)
    if doc is None:
        return None
    out = {"title": doc.get("title", ref), "html": render_md(doc.get("body", "")), "ref": ref,
           "raw": doc.get("body", "")}
    if doc.get("proposal"):
        prop = doc["proposal"]
        provenance = ""
        if prop.startswith("<!-- proposal"):
            provenance, prop = prop.split("-->", 1)
            provenance = provenance.replace("<!-- proposal", "").strip(" ·")
        out["proposal"] = {"html": render_md(prop.strip()), "provenance": provenance}
    if doc.get("files"):
        out["files"] = doc["files"]
    if doc.get("cover"):
        out["cover"] = doc["cover"]
    return out
