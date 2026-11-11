"""Acceptance criteria in the task (ADR-029 decision 9, REQ-003 GP-14 – GP-16): the list a helper drafts from the
requirement and a person confirms with the task — the Definition of Ready — and from which the protocols take their case
items. One line per criterion, readable by people and parsed here:

    ## Acceptance criteria
    - AC-1 · ENTW · yes/no — Station words never overlap at 480 px.
    - AC-2 · TEST · evidence — A screenshot of the case at 780 px.
    - AC-3 · both · number ≤ 0 — New errors in the log after the deploy.
    - AC-4 · TEST · choice good|acceptable / broken — How it looks on a phone.

Where: a stage key (ENTW, TEST, PROD, …) or `both` (ENTW and TEST). How: `yes/no`, `number` with `= n`, `≤ n`, `≥ n` or
`a..b`, `choice` with the passing values before ` / ` and the others after, or `evidence`. Nothing here names a domain:
the heading, the separators and the stage keys are the same for every application.
"""

from __future__ import annotations

import re

HEADING = re.compile(r"^#{2,3}\s*(acceptance criteria|akzeptanzkriterien)\s*$", re.I | re.M)
LINE = re.compile(r"^\s*[-*]\s*(AC-\d+)\s*·\s*([A-Za-z]+)\s*·\s*(.+?)\s+[—–-]\s+(.+?)\s*$")
BOTH = ("both", "beide")


def _how(text: str) -> dict:
    t = text.strip()
    low = t.lower()
    if low in ("yes/no", "yesno", "ja/nein"):
        return {"type": "yesno"}
    if low == "evidence" or low == "beleg":
        return {"type": "evidence"}
    if low.startswith("number") or low.startswith("zahl"):
        rest = t.split(None, 1)[1] if " " in t else ""
        rest = rest.replace("<=", "≤").replace(">=", "≥").strip()
        crit: dict = {}
        if m := re.fullmatch(r"=\s*(-?\d+(?:\.\d+)?)", rest):
            crit["eq"] = float(m.group(1))
        elif m := re.fullmatch(r"≤\s*(-?\d+(?:\.\d+)?)", rest):
            crit["max"] = float(m.group(1))
        elif m := re.fullmatch(r"≥\s*(-?\d+(?:\.\d+)?)", rest):
            crit["min"] = float(m.group(1))
        elif m := re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)", rest):
            crit["min"], crit["max"] = float(m.group(1)), float(m.group(2))
        else:
            raise ValueError(f"a number criterion is '= n', '≤ n', '≥ n' or 'a..b', not '{rest}'")
        return {"type": "number", "criterion": crit}
    if low.startswith("choice") or low.startswith("auswahl"):
        rest = t.split(None, 1)[1] if " " in t else ""
        good, _, bad = rest.partition("/")
        allowed = [x.strip() for x in good.split("|") if x.strip()]
        others = [x.strip() for x in bad.split("|") if x.strip()]
        if not allowed:
            raise ValueError("a choice criterion names its passing values: 'choice good|ok / broken'")
        return {"type": "choice", "options": allowed + others, "criterion": {"allowed": allowed}}
    raise ValueError(f"how a criterion is checked is yes/no, number …, choice … or evidence, not '{t}'")


def _scan(text: str) -> tuple[list[dict], list[dict]]:
    """The criteria, and the unreadable lines as {line (1-based in the whole text), text, reason}."""
    m = HEADING.search(text or "")
    if not m:
        return [], []
    first = text.count("\n", 0, m.end()) + 1                    # the heading's line; the body starts on the line after it
    body = text[m.end():]
    nxt = re.search(r"^#{1,3}\s", body, re.M)
    if nxt:
        body = body[:nxt.start()]
    out, bad = [], []
    for n, raw in enumerate(body.split("\n")[1:], start=first + 1):
        if not raw.strip():
            continue
        lm = LINE.match(raw)
        if not lm:
            if raw.strip().startswith(("-", "*")):
                bad.append({"line": n, "text": raw.strip(), "reason": "not 'AC-n · STAGE · how — statement'"})
            continue
        aid, where, how, statement = lm.groups()
        try:
            spec = _how(how)
        except ValueError as exc:
            bad.append({"line": n, "text": raw.strip(), "reason": f"{aid}: {exc}"})
            continue
        out.append({"id": aid, "stages": ["ENTW", "TEST"] if where.lower() in BOTH else [where.upper()], "statement": statement, **spec})
    return out, bad


def parse(text: str) -> tuple[list[dict], list[str]]:
    """The criteria of a task text, and the lines under the heading that could not be read (with why)."""
    out, bad = _scan(text)
    return out, [f"{b['text']} — {b['reason']}" if b["reason"].startswith("not ") else b["reason"] for b in bad]


def unreadable(text: str) -> list[dict]:
    """The lines the gate could not read, where they stand: what an editor marks before the text is saved (REQ-001 S-16)."""
    return _scan(text)[1]


def items_for(criteria: list[dict], stage: str, lang: str = "en") -> list[dict]:
    """Protocol case items for the criteria that name this stage, each pointing back at its criterion."""
    out = []
    for c in criteria:
        if stage.upper() not in c["stages"]:
            continue
        it = {"id": c["id"].lower(), "question": {lang: c["statement"], "en": c["statement"]}, "type": c["type"], "must": True,
              "origin": f"task:{c['id']}"}
        for k in ("criterion", "options"):
            if k in c:
                it[k] = c[k]
        out.append(it)
    return out
