"""A file as readable HTML, for the viewer over the case. Raw HTML in a file is shown, never run."""

from __future__ import annotations

import html
import re

import markdown

_MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])


def render(text: str, kind: str) -> str:
    """Markdown → HTML with raw tags escaped and script links defused; plain text → a <pre>."""
    if kind != "md":
        return "<pre>" + html.escape(text, quote=False) + "</pre>"
    _MD.reset()
    out = _MD.convert(text.replace("&", "&amp;").replace("<", "&lt;"))     # tags are shown, not run; a line's leading > stays a quote
    return re.sub(r'(href|src)=(["\'])\s*(javascript|data|vbscript):', r"\1=\2#", out, flags=re.I)
