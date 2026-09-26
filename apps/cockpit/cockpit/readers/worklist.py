"""Work list: what is open, who holds it, what is blocked.

Reads todo.json — the structured list with its own value lists — and never
the markdown board. The terminal statuses come from the file, not from here.
"""

from __future__ import annotations

import datetime as dt

from . import mtime_iso, today


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    path = access.resolve(src, "todo.json", role)
    doc = access.read_json(src, "todo.json", role)

    terminal = {s["id"] for s in doc["lov"]["statuses"] if s.get("terminal")}
    t0 = today()
    soon = (t0 + dt.timedelta(days=7)).isoformat()
    week_ago = (t0 - dt.timedelta(days=7)).isoformat()

    open_ = [t for t in doc["todos"] if t["status"] not in terminal]
    due_soon = [t for t in open_ if t.get("due") and t["due"] <= soon]
    overdue = [t for t in open_ if t.get("due") and t["due"] < t0.isoformat()]
    waiting = [t for t in open_ if t["status"] == "waiting"]
    blocked = [t for t in open_ if t.get("blockedBy")]
    done_week = [t for t in doc["todos"] if t.get("closed") and t["closed"] >= week_ago]

    state = "blocked" if overdue else "attention" if due_soon else "ok"
    return {
        "title": "worklist.title",
        "subtitle": "worklist.subtitle",
        "as_of": mtime_iso(path),
        "state": state,
        "headline": {"value": len(open_), "unit": "worklist.open"},
        "lines": [
            {"label": "worklist.due_soon", "value": len(due_soon), "tone": "warn" if due_soon else "muted"},
            {"label": "worklist.waiting", "value": len(waiting), "tone": "muted"},
            {"label": "worklist.blocked", "value": len(blocked), "tone": "warn" if blocked else "muted"},
            {"label": "worklist.done_week", "value": len(done_week), "tone": "ok"},
        ],
        "source": f"{access.source(src).label} · todo.json",
        "figure": {"kind": "bar", "segments": [
            {"label": "status." + s["id"], "value": sum(1 for t in doc["todos"] if t["status"] == s["id"]),
             "tone": "muted" if s.get("terminal") else ("warn" if s["id"] == "waiting" else "accent")}
            for s in sorted(doc["lov"]["statuses"], key=lambda s: s["order"])
        ]},
    }


def detail(access, role, module, config) -> dict:
    src = module.sources[0]
    doc = access.read_json(src, "todo.json", role)
    people = {p["id"]: p["name"].split()[0] for p in doc["lov"]["people"]}
    clusters = {c["id"]: c["label"] for c in doc["lov"]["clusters"]}
    columns = []
    for s in sorted(doc["lov"]["statuses"], key=lambda s: s["order"]):
        items = [t for t in doc["todos"] if t["status"] == s["id"]]
        items.sort(key=lambda t: (t.get("due") or "9999", t["id"]))
        columns.append({
            "label": s["label"], "tone": "warn" if s["id"] == "waiting" else "ok" if s.get("terminal") else "",
            "cards": [{"tag": f'{t["id"]} · {clusters[t["cluster"]]}', "title": t["title"],
                       "meta": [m for m in (t.get("due"), t["priority"], people.get(t["assignee"]),
                                            ("⟵ " + ", ".join(t["blockedBy"])) if t.get("blockedBy") else None) if m]}
                      for t in items[:40]],
        })
    return {"blocks": [{"kind": "kanban", "title": "block.by_status", "columns": columns}]}
