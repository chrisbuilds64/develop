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


HEADING = re.compile(r"^###\s+([A-Z]{2,5}-\d+)[:\s]+(.+?)\s*$")
TABLE_ROW = re.compile(r"^\|\s*\*\*([A-Z]{2,5}-\d+)\*\*\s*(.*?)\s*\|")
SECTION = re.compile(r"^##\s+(.+?)\s*$")
SEVERITY = re.compile(r"^###\s+(KRITISCH|HOCH|MITTEL|NIEDRIG|CRITICAL|HIGH|MEDIUM|LOW)\s*$", re.I)
BULLET = re.compile(r"^-\s+\[( |x)\]\s+\**(.+?)\**\s*(?:—|-|:)")
RISK = re.compile(r"(?:Overall Risk|Risk|Risiko)(?:\s+stays|\s+bleibt)?[:\s]+\**([A-Z]{3,})\b")


def _findings(text: str) -> list[dict]:
    """Findings, from three shapes audits actually use.

    `### SEC-038: title` headings under a `## New` / `## Open` / `## Resolved`
    section; `| **SEC-034** title | resolution |` table rows in a resolved
    section; and `- [ ] **title** — …` items under a severity heading, which is
    how documentation audits list theirs.
    """
    out, section, severity = [], "", ""
    for line in text.splitlines():
        m = SECTION.match(line)
        if m:
            section, severity = m.group(1).lower(), ""
            continue
        m = SEVERITY.match(line)
        if m:
            severity = m.group(1).upper()
            continue
        state = ("closed" if "resolved" in section or "closed" in section or "erledigt" in section
                 else "new" if "new" in section or "neu" in section else "open")
        m = HEADING.match(line)
        if m:
            out.append({"id": m.group(1), "title": m.group(2), "state": state})
            continue
        m = TABLE_ROW.match(line)
        if m and state == "closed":
            out.append({"id": m.group(1), "title": m.group(2) or m.group(1), "state": "closed"})
            continue
        m = BULLET.match(line)
        if m and severity and "finding" in section:
            out.append({"id": severity, "title": m.group(2).strip("* "),
                        "state": "closed" if m.group(1) == "x" else "open"})
    return out


def detail(access, role, module, config) -> dict:
    src = module.sources[0]
    rows, findings = [], []
    for name in sorted(access.listdir(src, role), reverse=True):
        m = NAME.match(name)
        if not m:
            continue
        date, kind = m.groups()
        text = access.read_text(src, name, role)
        fs = _findings(text)
        risk = RISK.search(text)
        rows.append([
            {"text": date, "href": f"/m/audits/doc/{name}"},
            {"badge": f"audits.{kind}", "tone": "muted"},
            {"badge": risk.group(1).upper(), "tone": {"LOW": "ok", "MEDIUM": "warn"}.get(risk.group(1).upper(), "bad")} if risk else "—",
            sum(1 for f in fs if f["state"] == "new"),
            sum(1 for f in fs if f["state"] == "open"),
            sum(1 for f in fs if f["state"] == "closed"),
        ])
        for f in fs:
            findings.append([f["id"], f["title"], {"badge": f"finding.{f['state']}",
                             "tone": {"new": "warn", "open": "warn", "closed": "ok"}[f["state"]]},
                             {"text": date, "href": f"/m/audits/doc/{name}"}])
    seen, latest = set(), []
    for row in findings:                      # newest audit first: the first sighting is the current state
        if row[0] not in seen:
            seen.add(row[0]); latest.append(row)
    return {"blocks": [
        {"kind": "table", "title": "block.audits", "columns": ["col.date", "col.kind", "col.risk", "col.new", "col.open", "col.closed"], "rows": rows},
        {"kind": "table", "title": "block.findings", "columns": ["col.id", "col.title", "col.status", "col.audit"], "rows": latest},
    ]}


def document(access, role, module, config, ref) -> dict | None:
    src = module.sources[0]
    if not NAME.match(ref):
        return None
    return {"title": ref, "body": access.read_text(src, ref, role)}
