"""Canon elicitation: how far the interview is, and where the answers went.

Reads the two files Gatehouse leaves in an instance directory — `run.json`
(the state) and `audit.jsonl` (every model call, written before it was sent).
The line "answers go to" is the one a decision-maker understands first: it
says, in plain words, which endpoints the client's material reached.
"""

from __future__ import annotations

import json

from cockpit.plugins._shared import mtime_iso, now_iso


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    label = access.source(src).label
    names = access.listdir(src, role)

    if "run.json" not in names:
        return {
            "title": "gatehouse.title", "subtitle": "gatehouse.subtitle",
            "as_of": now_iso(), "state": "ok",
            "headline": {"value": 0, "unit": "gatehouse.answered"},
            "lines": [{"label": "gatehouse.no_run", "value": "—", "tone": "muted"}],
            "source": f"{label} · run.json",
        }

    run_path = access.resolve(src, "run.json", role)
    run = access.read_json(src, "run.json", role)
    answers = run.get("answers", {})
    answered = sum(1 for a in answers.values() if (a.get("text") or "").strip())
    closed = len(run.get("closed_blocks", []))

    calls, routes = 0, {}
    if "audit.jsonl" in names:
        for line in access.read_text(src, "audit.jsonl", role).splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            calls += 1
            dest = entry.get("destination") or entry.get("adapter") or "?"
            local = bool(entry.get("local")) or entry.get("egress") is False
            r = routes.setdefault(dest, {"label": dest, "value": 0, "local": local})
            r["value"] += 1
    destinations = [r["label"] + (" (local)" if r["local"] else "") for r in routes.values()]

    return {
        "title": "gatehouse.title",
        "subtitle": f"{run.get('client', '')} · {run.get('pack_name', '')} {run.get('pack_version', '')}".strip(" ·"),
        "as_of": mtime_iso(run_path),
        "state": "ok" if closed else "attention",
        "headline": {"value": answered, "unit": "gatehouse.answered"},
        "lines": [
            {"label": "gatehouse.blocks", "value": closed, "tone": "ok" if closed else "muted"},
            {"label": "gatehouse.calls", "value": calls, "tone": "muted"},
            {"label": "gatehouse.destinations", "value": ", ".join(destinations) or "—", "tone": "muted"},
        ],
        "source": f"{label} · run.json, audit.jsonl",
        "figure": {"kind": "route", "origin": "route.you",
                   "routes": sorted(routes.values(), key=lambda r: (not r["local"], -r["value"]))[:6]},
    }
