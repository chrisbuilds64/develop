"""Canon: the documents and their header blocks.

Our canon files open with a fenced block of `key: value` lines — path, type,
purpose, maintained, updated. This reader walks the released directory, reads
those blocks, and shows the rulebook as a table: what exists, what kind it is,
when it was last touched. Nothing is written.
"""

from __future__ import annotations

import datetime as dt
import re

HEADER = re.compile(r"^```\n(.*?)\n```", re.S)
LINE = re.compile(r"^(path|type|purpose|maintained|updated):\s*(.*)$", re.M)


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _walk(access, role, src, sub="."):
    for n in access.listdir(src, role, sub):
        p = n if sub == "." else f"{sub}/{n}"
        if n.startswith((".", "_")):
            continue
        try:
            names = access.listdir(src, role, p)     # a directory
        except Exception:
            names = None
        if names is None:
            if n.endswith(".md"):
                yield p
        else:
            yield from _walk(access, role, src, p)


def _docs(access, role, src):
    out = []
    for p in _walk(access, role, src):
        try:
            text = access.read_text(src, p, role)
        except Exception:
            continue
        m = HEADER.match(text)
        head = dict(LINE.findall(m.group(1))) if m else {}
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.rsplit("/", 1)[-1])
        out.append({"path": p, "title": title, "type": head.get("type", "—"), "purpose": head.get("purpose", ""),
                    "updated": head.get("updated", "—"), "header": bool(m)})
    return out


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    docs = _docs(access, role, src)
    cutoff = (dt.date.today() - dt.timedelta(days=90)).isoformat()
    with_header = [d for d in docs if d["header"]]
    stale = [d for d in with_header if d["updated"] < cutoff and d["updated"] != "—"]
    kinds = {}
    for d in with_header:
        k = d["type"].split("·")[0].strip()
        kinds[k] = kinds.get(k, 0) + 1
    return {
        "title": "canon.title", "subtitle": "canon.subtitle", "as_of": _now(),
        "state": "attention" if stale else "ok",
        "headline": {"value": len(docs), "unit": "canon.documents"},
        "lines": [
            {"label": "canon.with_header", "value": len(with_header), "tone": "ok"},
            {"label": "canon.without_header", "value": len(docs) - len(with_header), "tone": "warn" if len(docs) - len(with_header) else "muted"},
            {"label": "canon.stale", "value": len(stale), "tone": "warn" if stale else "muted"},
        ],
        "source": f"{access.source(src).label} · *.md",
        "figure": {"kind": "bar", "segments": [{"label": k, "value": v, "tone": "accent"} for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:8]]},
    }


def detail(access, role, module, config) -> dict:
    src = module.sources[0]
    rows = [[{"text": d["path"], "href": f"/m/{module.id}/doc/{d['path']}"}, d["type"], d["updated"],
             d["purpose"][:120]] for d in sorted(_docs(access, role, src), key=lambda d: d["path"])]
    return {"blocks": [{"kind": "table", "title": "canon.all", "columns": ["col.path", "col.type", "col.updated", "col.purpose"], "rows": rows}]}


def document(access, role, module, config, ref) -> dict | None:
    if not ref.endswith(".md"):
        return None
    text = access.read_text(module.sources[0], ref, role)
    return {"title": ref, "body": text}
