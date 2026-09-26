"""Audits: when each kind last ran, and when the next one is due.

Reads nothing but file names — `YYYY-MM-DD_<kind>-audit.md`. The content of an
audit stays where it is; the cockpit reports cadence, not findings.
"""

from __future__ import annotations

import datetime as dt
import re

from . import now_iso, today

NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(security|documentation)-audit\.md$")
CADENCE_DAYS = 14


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    last: dict[str, str] = {}
    count = 0
    for name in access.listdir(src, role):
        m = NAME.match(name)
        if not m:
            continue
        count += 1
        date, kind = m.groups()
        if date > last.get(kind, ""):
            last[kind] = date

    t0 = today()
    due_in = None
    for kind, date in last.items():
        nxt = dt.date.fromisoformat(date) + dt.timedelta(days=CADENCE_DAYS)
        days = (nxt - t0).days
        due_in = days if due_in is None else min(due_in, days)

    state = "ok" if due_in is None or due_in > 3 else "attention" if due_in >= 0 else "blocked"
    lines = [
        {"label": "audits.security", "value": last.get("security", "—"), "tone": "muted"},
        {"label": "audits.documentation", "value": last.get("documentation", "—"), "tone": "muted"},
        {"label": "audits.count", "value": count, "tone": "muted"},
    ]
    return {
        "title": "audits.title",
        "subtitle": "audits.subtitle",
        "as_of": now_iso(),
        "state": state,
        "headline": {"value": due_in if due_in is not None else "—", "unit": "audits.days"},
        "lines": lines,
        "source": f"{access.source(src).label} · file names only",
        "figure": {"kind": "ring", "value": max(0, CADENCE_DAYS - (due_in or 0)) if due_in is not None else 0,
                   "max": CADENCE_DAYS},
    }
