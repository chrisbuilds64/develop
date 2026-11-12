"""Going back, and resuming where the case stood (ADR-035, REQ-001 T-14 to T-19).

Until a case is final, a person takes it back to any stage it has stood in. What is redone there is approved again; a
later gate whose deliverables are unchanged still holds, and `resume` takes the case forward over such gates, never
beyond the furthest stage it has stood in (its mark) and never into a stage that deploys. Nothing here names a domain:
what is final and what deploys is the application's configuration.

    meta.json → "gates": {"<stage>": {"action", "step", "by", "at", "covered": {"<base name>": {"file", "print"}}}}

A gate's record is what it covered when it was passed: the deliverables the action asked for, each with the file that
held its newest version and a fingerprint of the content. The gate holds while every one of them is still that file
with that content.
"""

from __future__ import annotations

import hashlib

from ..config import DomainConfig
from ..models import Action, Case
from ..store import FsStore
from . import cases as reading

GATES = "gates"
CLOSED = ("out", "archive")
LARGE = 32 * 1024 * 1024          # above this a fingerprint is size and time, not content (a video is not hashed at a gate)


def _order(config: DomainConfig) -> list[str]:
    return [s.folder for s in config.stages]


def stood_in(config: DomainConfig, case: Case) -> list[str]:
    """Every stage the case has stood in, in the configured order — from the thread, where each move is recorded."""
    seen = {case.stage}
    for e in case.entries:
        seen.update(x for x in (e.stage, e.from_, e.to) if x)
    return [f for f in _order(config) if f in seen]


def mark(config: DomainConfig, case: Case) -> str:
    """The furthest stage the case has stood in."""
    return (stood_in(config, case) or [case.stage])[-1]


def is_final(config: DomainConfig, case: Case) -> bool:
    """The case has reached a stage its application calls final, or it is closed: it does not go back any more."""
    here = config.stage(case.stage)
    if here is not None and here.group in CLOSED:
        return True
    return any((st := config.stage(f)) is not None and st.final for f in stood_in(config, case))


def gate_of(config: DomainConfig, stage: str) -> Action | None:
    """The stage's gate: its first action that moves the case forward."""
    order = _order(config)
    st = config.stage(stage)
    if st is None or stage not in order:
        return None
    return next((a for a in st.actions if a.to in order and order.index(a.to) > order.index(stage)), None)


def fingerprint(store: FsStore, case_id: str, name: str) -> str:
    f = store.case_dir(case_id) / name
    size = f.stat().st_size
    if size > LARGE:
        return f"size:{size}:time:{int(f.stat().st_mtime)}"
    return "sha256:" + hashlib.sha256(f.read_bytes()).hexdigest()


def _asked(config: DomainConfig, case: Case, action: Action) -> list[str]:
    """The base names of the deliverables a gate asks for, as far as they are in the case."""
    names: list[str] = []
    for req in action.requires:
        if req == "primary":
            names += [config.primary(case.label) or ""]
        elif req == "required":
            names += [s.file for s in case.slots if s.required]
        elif req.startswith("shape:"):
            names += [s.file for s in case.slots if s.present and s.shape.startswith(req[6:])]
        elif req.startswith("protocol:"):
            names += [f"protocol-{req[9:]}.json"]
        elif "|" in req:
            names += [r for r in req.split("|")]
        elif ":" not in req and req not in ("answered", "criteria"):
            names += [req]
    newest = reading.newest_versions(case.files)
    return [n for n in dict.fromkeys(names) if n and n in newest]


def covered(store: FsStore, config: DomainConfig, case: Case, action: Action) -> dict:
    newest = reading.newest_versions(case.files)
    return {n: {"file": newest[n], "print": fingerprint(store, case.id, newest[n])} for n in _asked(config, case, action)}


def holds(store: FsStore, config: DomainConfig, case: Case, stage: str) -> bool:
    """The gate of this stage was passed, and everything it covered is unchanged."""
    record = (case.meta.get(GATES) or {}).get(stage)
    gate = gate_of(config, stage)
    if not isinstance(record, dict) or gate is None or record.get("action") != gate.id:
        return False
    newest = reading.newest_versions(case.files)
    was = record.get("covered") or {}
    if set(_asked(config, case, gate)) != set(was):                  # something the gate asks for came or went
        return False
    for base, doc in was.items():
        if newest.get(base) != doc.get("file"):
            return False
        try:
            if fingerprint(store, case.id, doc["file"]) != doc.get("print"):
                return False
        except OSError:
            return False
    return True


def resume_target(store: FsStore, config: DomainConfig, case: Case) -> str | None:
    """Where `resume` takes the case: forward over every gate that holds, up to the first that does not, never beyond
    the mark, never into a stage that deploys. None when there is nowhere to resume to."""
    if is_final(config, case):
        return None
    order = _order(config)
    limit = order.index(mark(config, case))
    at, target = case.stage, None
    while at in order and order.index(at) < limit and holds(store, config, case, at):
        nxt = gate_of(config, at).to
        st = config.stage(nxt)
        if st is None or order.index(nxt) > limit or st.deploys:
            break
        at = target = nxt
    return target


def back_targets(config: DomainConfig, case: Case) -> list[str]:
    """The earlier stages a person may take the case back to: stood in before, and a person's to work in."""
    if is_final(config, case):
        return []
    order = _order(config)
    here = order.index(case.stage) if case.stage in order else -1
    out = []
    for f in stood_in(config, case):
        st = config.stage(f)
        if st is None or order.index(f) >= here or st.group in CLOSED or not st.turn or st.turn == "claude":
            continue
        out.append(f)
    return out
