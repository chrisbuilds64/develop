"""Ordering a helper: one file in `_runs/`, status queued. A runner elsewhere picks it up (the contract of
run_request.py, kept: id `<yyyymmdd-hhmmss>_<skill>_<case>`, the same fields, the same policy file)."""

from __future__ import annotations

import datetime as dt

from ..config import DomainConfig
from ..models import Person
from ..store import FsStore


def policy_for(config: DomainConfig, skill: str) -> dict:
    p = config.run_policy
    return {**p.get("default", {}), **p.get("skills", {}).get(skill, {})}


def may_order(config: DomainConfig, skill: str, person: Person) -> str | None:
    """None when the person may order this skill, else the sentence that refuses."""
    if not config.run_policy:
        return "no run-policy.json at the pipeline root — nothing is ordered without a declared policy"
    allowed = policy_for(config, skill).get("orderable_by", [])
    if not allowed:
        return f"'{skill}' may not be ordered by anyone right now"
    if not (set(allowed) & set(person.roles)):
        return f"'{skill}' may be ordered by {', '.join(allowed)}, not {person.name}"
    return None


def order(store: FsStore, config: DomainConfig, case_id: str, stage: str, skill: str, by: str, note: str = "", request_id: str | None = None,
          background: bool = False) -> str:
    """Write the order. With a request id, a second call with the same id returns the first order's id. A background
    order works beside the people and is never anybody's move (a follow-up while somebody answers)."""
    if request_id:
        for name in store.runs():
            doc = store.read_json(f"_runs/{name}")
            if doc.get("request_id") == request_id:
                return doc["id"]
    now = dt.datetime.now().astimezone()
    run = {"id": f"{now.strftime('%Y%m%d-%H%M%S')}_{skill}_{case_id}", "skill": skill, "container": f"{stage}/{case_id}",
           "requested_by": by, "runner": "claude-code", "status": "queued", "created": now.isoformat(timespec="seconds")}
    if note.strip():
        run["note"] = note.strip()
    if request_id:
        run["request_id"] = request_id
    if background:
        run["background"] = True
    n = 0
    while store.exists(f"_runs/{run['id']}.json"):           # two orders in the same second
        n += 1
        run["id"] = f"{now.strftime('%Y%m%d-%H%M%S')}-{n}_{skill}_{case_id}"
    store.write_json(f"_runs/{run['id']}.json", run)
    return run["id"]
