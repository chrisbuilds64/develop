"""Dependencies between cases (ADR-031 decision 5, REQ-005 DP-01 to DP-05).

A case may wait for other cases. The list lives in the case's `meta.json` under `waitsFor` and is written only by the
step `wait_for`, so it is journaled and stands in the thread like every other move. A reference is either a case of
the same application instance (`SYS-131`) or one of another instance it is connected to (`shipyard:SW-2026-001`).

Which other instances a case can reach is the resolver's business, not this module's: today the connections of
`targets.json` (ADR-022/023), after ADR-032 the bindings of the workspace. A reference the resolver cannot reach is
treated like one that does not exist — the person may not see it.

A waiting case is *released* when every case it waits for is closed (its stage is in a closing group). It does not
move by itself (DP-03); the release is a fact the surface shows, the move stays a person's.
"""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel

from ..config import DomainConfig
from ..store import FsStore

KEY = "waitsFor"
CLOSED = ("out", "archive")                     # the same groups step.py closes a case into
Resolver = Callable[[str], "tuple[FsStore, DomainConfig] | None"]


class Dependency(BaseModel):
    ref: str                                    # as written: "SYS-131" or "shipyard:SW-2026-001"
    instance: str = ""                          # "" = the same instance
    case: str
    found: bool = False
    closed: bool = False
    title: str = ""
    stage_word: str = ""


def parse(ref: str) -> tuple[str, str]:
    """'SYS-131' → ('', 'SYS-131'); 'shipyard:SW-2026-001' → ('shipyard', 'SW-2026-001')."""
    ref = str(ref).strip()
    inst, sep, case = ref.partition(":")
    return (inst.strip(), case.strip()) if sep else ("", ref)


def resolver_for(store: FsStore, config: DomainConfig) -> Resolver:
    """The instance itself under "", every connected target under its key."""
    from . import handoff

    def resolve(instance: str):
        if not instance:
            return store, config
        try:
            t = handoff.target(store, instance)
        except Exception:                       # not connected, or its tree is gone: not reachable
            return None
        return t.store, t.config
    return resolve


def _identity(st: FsStore, case: str) -> tuple[str, str]:
    return str(st.root), case


def _meta(st: FsStore, case: str) -> dict | None:
    try:
        stage = st.find(case)
    except Exception:
        return None
    if stage is None:
        return None
    try:
        return st.case_json(case, "meta.json")
    except (OSError, ValueError):
        return {}


def refs_of(meta: dict) -> list[str]:
    v = meta.get(KEY) or []
    return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []


def state(resolve: Resolver, ref: str, lang: str) -> Dependency:
    inst, case = parse(ref)
    dep = Dependency(ref=ref, instance=inst, case=case)
    got = resolve(inst)
    if got is None:
        return dep
    st, cfg = got
    stage = None
    try:
        stage = st.find(case)
    except Exception:
        pass
    if stage is None:
        return dep
    meta = _meta(st, case) or {}
    s = cfg.stage(stage)
    dep.found = True
    dep.closed = bool(s and s.group in CLOSED)
    dep.title = str(meta.get("title") or meta.get("working_title") or case)
    dep.stage_word = cfg.word("stages", stage, lang, stage)
    return dep


def waits(meta: dict, resolve: Resolver, lang: str) -> list[Dependency]:
    return [state(resolve, r, lang) for r in refs_of(meta)]


def released(deps: list[Dependency]) -> bool:
    """Waiting for something, and all of it closed."""
    return bool(deps) and all(d.closed for d in deps)


def check(store: FsStore, case_id: str, refs: list[str], resolve: Resolver) -> str | None:
    """Why these references may not be set, in one sentence — or None. Unknown or unreachable (DP-04), the case itself,
    a circle (DP-05). The search follows each reference into its own instance and resolves the references found there
    relative to that instance; it reaches only what this case's resolver reaches."""
    me = _identity(store, case_id)
    for ref in refs:
        inst, case = parse(ref)
        if not case:
            return f"'{ref}' names no case"
        got = resolve(inst)
        if got is None:
            return f"'{inst}' is not connected here" if inst else f"'{ref}' cannot be reached"
        st = got[0]
        if _meta(st, case) is None:
            return f"'{ref}' does not exist"
        if _identity(st, case) == me:
            return "a case cannot wait for itself"
    # circle: walk from every new reference; reaching this case again closes a circle
    stores = {"": store}
    for k in {parse(r)[0] for r in refs if parse(r)[0]}:
        got = resolve(k)
        if got:
            stores[k] = got[0]
    seen: set[tuple[str, str]] = set()
    todo = [(stores[parse(r)[0]], parse(r)[1], r) for r in refs]
    while todo:
        st, case, first = todo.pop()
        ident = _identity(st, case)
        if ident == me:
            return f"'{first}' already waits for this case — that would be a circle"
        if ident in seen:
            continue
        seen.add(ident)
        for r in refs_of(_meta(st, case) or {}):
            inst, nxt = parse(r)
            if not inst:
                todo.append((st, nxt, first))
            elif st is store or str(st.root) == str(store.root):
                got = resolve(inst)
                if got:
                    todo.append((got[0], nxt, first))
            # a reference made inside another instance to a third one is not followed: this case cannot reach the
            # third instance's names, and a circle through it is caught when that instance sets its own reference
    return None
