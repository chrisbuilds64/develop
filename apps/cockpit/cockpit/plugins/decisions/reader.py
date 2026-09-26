"""Decisions: the Context Loop decision log, read and shown.

`decisions.md` has one `## <date> — <what>` heading per entry, with `**Why:**`
and optionally `**Instead of:**` beneath. This reader counts them, shows the
latest, and lists them all. It reads through `access` like every plugin, and
the file it reads is the signed-in user's — the source says `{user.context}`.
"""

from __future__ import annotations

import datetime as dt
import re

ENTRY = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+[—-]+\s+(.+?)\s*$")
FIELD = re.compile(r"^\*\*(Why|Instead of):\*\*\s*(.*)$")


def _entries(text: str) -> list[dict]:
    out, cur = [], None
    for line in text.splitlines():
        m = ENTRY.match(line)
        if m:
            cur = {"date": m.group(1), "what": m.group(2), "why": "", "instead": ""}
            out.append(cur)
            continue
        m = FIELD.match(line)
        if m and cur:
            cur["why" if m.group(1) == "Why" else "instead"] = m.group(2).strip()
    return out


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    names = access.listdir(src, role)
    entries = _entries(access.read_text(src, "decisions.md", role)) if "decisions.md" in names else []
    month_ago = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    recent = [e for e in entries if e["date"] >= month_ago]
    latest = entries[-1] if entries else None
    return {
        "title": "decisions.title", "subtitle": "decisions.subtitle",
        "as_of": _now(), "state": "ok",
        "headline": {"value": len(entries), "unit": "decisions.count"},
        "lines": [
            {"label": "decisions.recent", "value": len(recent), "tone": "ok" if recent else "muted"},
            {"label": "decisions.latest", "value": (latest["what"][:60] if latest else "—"), "tone": "muted"},
            {"label": "decisions.latest_date", "value": (latest["date"] if latest else "—"), "tone": "muted"},
        ],
        "source": f"{access.source(src).label} · decisions.md",
        "figure": {"kind": "flow", "steps": [
            {"label": m, "value": sum(1 for e in entries if e["date"].startswith(m)), "tone": "accent"}
            for m in sorted({e["date"][:7] for e in entries})[-8:]
        ]} if entries else None,
    } | ({} if entries else {"figure": {"kind": "ring", "value": 0, "max": 1}})


def detail(access, role, module, config) -> dict:
    src = module.sources[0]
    names = access.listdir(src, role)
    entries = _entries(access.read_text(src, "decisions.md", role)) if "decisions.md" in names else []
    rows = [[e["date"], e["what"], e["why"], e["instead"] or "—"] for e in reversed(entries)]
    return {"blocks": [
        {"kind": "table", "title": "decisions.all", "columns": ["col.date", "decisions.what", "decisions.why", "decisions.instead"], "rows": rows},
        {"kind": "links", "title": "block.tools", "items": [{"label": "decisions.file", "href": f"/m/{module.id}/doc/decisions.md"}]},
    ]}


def document(access, role, module, config, ref) -> dict | None:
    if ref != "decisions.md":
        return None
    return {"title": "decisions.md", "body": access.read_text(module.sources[0], ref, role)}
