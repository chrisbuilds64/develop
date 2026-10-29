"""The number of a new case, from the domain's own rule — a claim counts within its year, an idea waits for its number,
a piece of a series counts within its series. One mechanism, configured per domain (`theme.create.number`):

    "number": ["{series}-{seq:02}", "xxx"]      PressRoom: in a series SIM-03, else the placeholder until it is numbered
    "number": ["{year}-{seq:04}"]               a claims file: 2026-0418

Templates are tried in order; the first whose fields are all set wins. `{year}` is this year, `{seq}` the next free number
among the cases of the same label whose number starts like this template's fixed part; any other `{field}` comes from the
values the new case carries (the lists it was given). A template without `{seq}` is a fixed number; the id stays unique
by its slug. Default: `{year}-{seq:02}`, as before.
"""

from __future__ import annotations

import datetime as dt
import re

from ..store import FsStore

DEFAULT = ["{year}-{seq:02}"]
_FIELD = re.compile(r"\{([a-z_]+)(?::([^}]+))?\}")


def _fields(template: str) -> list[str]:
    return [m.group(1) for m in _FIELD.finditer(template) if m.group(1) not in ("year", "seq")]


def next_number(store: FsStore, label: str, rule: list[str] | str | None, values: dict) -> str:
    templates = [rule] if isinstance(rule, str) else list(rule or DEFAULT)
    year = str(dt.date.today().year)
    for t in templates:
        if any(not str(values.get(f) or "").strip() for f in _fields(t)):
            continue
        ctx = {**{k: str(v) for k, v in values.items()}, "year": year}
        head = _FIELD.sub(lambda m: ctx.get(m.group(1), "") if m.group(1) != "seq" else "\0", t).split("\0")[0]
        if "{seq" not in t:
            return head
        pattern = rf"^{re.escape(label)}-{re.escape(head)}(\d+)"
        taken = [int(m.group(1)) for st in store.stages() for cid in store.cases(st) if (m := re.match(pattern, cid))]
        seq = (max(taken) + 1) if taken else 1
        spec = next((m.group(2) for m in _FIELD.finditer(t) if m.group(1) == "seq"), "") or ""
        ctx["seq"] = format(seq, spec)
        return _FIELD.sub(lambda m: ctx.get(m.group(1), ""), t)
    return f"{year}-01"
