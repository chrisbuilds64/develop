"""The thread: review.md as data. One format, read and written here and nowhere else.

    ## REV-004 — v3 checked against the transcript
    **Date:** 2026-09-24 14:05 · **Author:** Axel · **For:** Akhil · **Status:** open · **Stage:** 30-review-human · **Resolves:** REV-002

    text …

The format is the one the pipeline has used since 2026-09 (every existing container parses). The
core adds four attributes a step may carry — Step, From, To, Amount — and Files for deliveries.
Older readers ignore attributes they do not know.
"""

from __future__ import annotations

import re

from ..models import Entry

HEAD = re.compile(r"^## (REV-\d{3}) — (.+?)\s*$", re.M)
ATTR = re.compile(r"\*\*([A-Za-z]+):\*\*\s*([^·\n]+?)(?=\s*·\s*\*\*|\s*$)", re.M)
LABELS = {"date": "Date", "author": "Author", "for_": "For", "status": "Status", "stage": "Stage",
          "resolves": "Resolves", "step": "Step", "from_": "From", "to": "To", "amount": "Amount", "files": "Files"}
BY_LABEL = {v: k for k, v in LABELS.items()}


def parse(text: str) -> list[Entry]:
    out: list[Entry] = []
    heads = list(HEAD.finditer(text))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[m.end():end]
        lines = block.strip("\n").split("\n", 1)
        attrs = dict(ATTR.findall(lines[0])) if lines and lines[0].startswith("**") else {}
        fields: dict = {"id": m.group(1), "title": m.group(2).strip(), "text": (lines[1] if len(lines) > 1 else "").strip()}
        for label, value in attrs.items():
            key = BY_LABEL.get(label)
            value = value.strip()
            if not key or value in ("", "—"):
                continue
            fields[key] = [v.strip() for v in value.split(",") if v.strip()] if key == "files" else value
        out.append(Entry.model_validate(fields))
    return out


def next_id(text: str) -> str:
    nums = [int(m.group(1)[4:]) for m in HEAD.finditer(text)]
    return f"REV-{max(nums, default=0) + 1:03d}"


def render(e: Entry) -> str:
    head = [f"**Date:** {e.date}", f"**Author:** {e.author}", f"**For:** {e.for_ or '—'}",
            f"**Status:** {e.status}", f"**Stage:** {e.stage}"]
    for key in ("resolves", "step", "from_", "to", "amount"):
        v = getattr(e, key)
        if v:
            head.append(f"**{LABELS[key]}:** {v}")
    if e.files:
        head.append(f"**Files:** {', '.join(e.files)}")
    return f"\n## {e.id} — {e.title}\n{' · '.join(head)}\n\n{e.text.strip()}\n"


def head_for(case_id: str) -> str:
    return f"# Review — {case_id}\n\nAppend only. Newest entry at the end, never edited afterwards.\n"


def resolved_ids(entries: list[Entry]) -> set[str]:
    return {e.resolves for e in entries if e.resolves}


def open_for(entries: list[Entry], person_name: str | None) -> list[Entry]:
    """Open entries addressed to a person that no later entry resolves."""
    done = resolved_ids(entries)
    return [e for e in entries if e.status == "open" and e.id not in done
            and (person_name is None or (e.for_ or "").lower() == person_name.lower())]
