"""A step: one move, whole or not at all (ADR-013).

    lock the case → check the precondition → journal `intent` → thread entry → move the folder → journal `done`

The same step id twice is a no-op that returns the first outcome. A journal left in `intent` is
completed on the next start (`recover()`): the entry is written if it is missing, the folder moved if it
still stands where it was. A folder somebody moved by hand is accepted and recorded as detected.
"""

from __future__ import annotations

import datetime as dt
import re

from ..config import DomainConfig
from ..models import Action, Entry, Journal, StepRequest, StepResult
from ..store import FsStore, StoreError
from . import cases as reading
from . import entries as thread
from . import runs as ordering
from .turn import four_eyes_block, missing_for, offered, primary_author

STEP_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
BUILTIN = ("answer", "note", "done", "deliver", "ask")
CLOSED = ("out", "archive")                 # the groups a case leaves the work in; `reopen` brings it back from there


def reopen_target(config: DomainConfig, case) -> str | None:
    """Where `reopen` takes a closed case: the open stage it last left for a closed one, from the thread; else the open
    stage just before its own in the configured order. None while the case still stands in the work."""
    here = config.stage(case.stage)
    if here is None or here.group not in CLOSED:
        return None
    open_ = [s.folder for s in config.stages if s.group not in CLOSED]
    closed = {s.folder for s in config.stages if s.group in CLOSED}
    for e in reversed(case.entries):
        if e.from_ in open_ and e.to in closed:
            return e.from_
    folders = [s.folder for s in config.stages]
    before = [f for f in folders[:folders.index(case.stage)] if f in open_] if case.stage in folders else []
    return before[-1] if before else (open_[0] if open_ else None)


def _done_by(store: FsStore, case_id: str, action: str) -> set[str]:
    """Who did this action on this case, from the journals."""
    out = set()
    for name in store.journals():
        try:
            doc = store.read_json(f"_steps/{name}")
        except (OSError, ValueError):
            continue
        if doc.get("case") == case_id and doc.get("action") == action and doc.get("status") == "done":
            out.add(str(doc.get("by")))
    return out


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _journal_path(step_id: str) -> str:
    return f"_steps/{step_id}.json"


def read_journal(store: FsStore, step_id: str) -> Journal | None:
    p = _journal_path(step_id)
    return Journal.model_validate(store.read_json(p)) if store.exists(p) else None


def _write_journal(store: FsStore, j: Journal) -> None:
    store.write_json(_journal_path(j.step_id), j.model_dump(by_alias=True, exclude_none=True))


def _result(j: Journal, replayed: bool = False) -> StepResult:
    return StepResult(ok=j.status == "done", step_id=j.step_id, case=j.case, action=j.action, **{"from": j.from_},
                      to=j.to, entry=j.entry, run=j.run, reason=j.reason, replayed=replayed)


def _refuse(store: FsStore, j: Journal, reason: str) -> StepResult:
    j.status, j.reason, j.finished = "refused", reason, _now()
    _write_journal(store, j)
    return _result(j)


def _append_entry(store: FsStore, config: DomainConfig, case_id: str, stage: str, e: dict) -> str:
    rel = f"{stage}/{case_id}/review.md"
    existing = store.read_text(rel) if store.exists(rel) else ""
    entry = Entry.model_validate({"id": thread.next_id(existing), "date": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"), "stage": stage, **e})
    store.append(rel, thread.render(entry), head=thread.head_for(case_id))
    return entry.id


def step(store: FsStore, config: DomainConfig, case_id: str, req: StepRequest, by: str, resolve=None) -> StepResult:
    """Perform one step on behalf of `by` (a person id). Never raises for a refusal; returns the reason.
    `resolve` reaches other application instances for `wait_for` (domain/depends.py); without it, their targets."""
    if not STEP_ID.match(req.step_id):
        return StepResult(ok=False, step_id=req.step_id, case=case_id, action=req.action, reason="step id must be 1–80 letters, digits, '-' or '_'")
    with store.lock(case_id):
        prior = read_journal(store, req.step_id)
        if prior is not None:
            if prior.status == "intent":
                _complete(store, config, prior)
                prior = read_journal(store, req.step_id)
            return _result(prior, replayed=True)

        person = config.person(by)
        if person is None:
            j = Journal(step_id=req.step_id, case=case_id, action=req.action, by=by, created=_now(), payload=req.payload)
            return _refuse(store, j, f"'{by}' is not in people.json")
        try:
            case = reading.load(store, config, case_id)
        except KeyError:
            j = Journal(step_id=req.step_id, case=case_id, action=req.action, by=person.id, created=_now(), payload=req.payload)
            return _refuse(store, j, f"case '{case_id}' not found")

        j = Journal(step_id=req.step_id, case=case_id, action=req.action, by=person.id, created=_now(), payload=req.payload, **{"from": case.stage})

        # ---- reopen: a closed case goes back into the work, logged like any move
        if req.action == "reopen":
            return _reopen(store, config, j, case, person, req)
        if req.action == "undo":
            return _undo(store, config, j, case, person, req)
        if req.action == "correct":
            return _correct(store, config, j, case, person, req)
        if req.action == "remind":
            return _remind(store, config, j, case, person, req)
        if req.action == "take_back":
            return _take_back(store, config, j, case, person, req)
        if req.action == "wait_for":
            return _wait_for(store, config, j, case, person, req, resolve)
        if req.action == "set_fields":
            return _set_fields(store, config, j, case, person, req)
        if req.action in ("share", "delegate"):
            return _hand_on(store, config, j, case, person, req)
        if req.action == "retry":
            return _retry(store, config, j, case, person)
        if req.action == "order_again":
            return _order_again(store, config, j, case, person, req)

        # ---- built-in moves: answer, note, done, deliver (an entry, never a move)
        if req.action in BUILTIN:
            return _builtin(store, config, j, case, person.id, req)

        # ---- a configured action
        stage = config.stage(case.stage)
        action = config.action(case.stage, req.action)
        if stage is None or action is None:
            return _refuse(store, j, f"'{req.action}' is not an action while the case stands in {case.stage}")
        if not offered(config, case, action):
            return _refuse(store, j, f"'{req.action}' is not offered for this case: nothing calls for it")
        from .turn import actor_of
        actor = actor_of(action.actor, case) or actor_of(stage.turn, case)
        if not config.may_act(person.id, actor) and not config.may_act(person.id, "role:operator"):
            return _refuse(store, j, f"{person.name} may not {req.action} here; it is {actor}'s move")
        missing = missing_for(config, case, action)
        if missing:
            return _refuse(store, j, "still missing: " + ", ".join(missing))
        if action.four_eyes:
            author = primary_author(config, case)
            if author and author == person.id:
                return _refuse(store, j, "four eyes: you wrote the newest version and cannot approve it")
        if action.four_eyes_of:
            earlier = _done_by(store, case_id, action.four_eyes_of)
            if person.id in earlier:
                return _refuse(store, j, f"four eyes: {person.name} did '{action.four_eyes_of}' on this case; somebody else does this")
        for field in action.payload:
            if not str(req.payload.get(field, "")).strip():
                return _refuse(store, j, f"'{field}' is required for {req.action}")
        if action.to and action.to not in store.stages():
            return _refuse(store, j, f"stage '{action.to}' does not exist")
        if action.run:
            refusal = ordering.may_order(config, action.run, person)
            if refusal:
                return _refuse(store, j, refusal)

        j.to = action.to
        _write_journal(store, j)                                                   # 3. intent
        return _complete(store, config, j, action=action, case_meta=case.meta)


def holders(config: DomainConfig, case, viewer: str | None) -> list:
    """The people who hold the case right now: the actors of its main move, when that is not the viewer's own and
    not a helper at work. Empty for a closed case or when it waits for the viewer."""
    from .turn import turn as whose
    here = config.stage(case.stage)
    if here is None or here.group in CLOSED:
        return []
    moves = whose(case, config)
    if not moves or moves[0].actor == "claude":
        return []
    people = [p for p in config.persons_for(moves[0].actor) if p.kind == "human"]
    if viewer and any(p.id == viewer for p in people):
        return []
    return people


def take_back_target(config: DomainConfig, case, viewer: str | None) -> str | None:
    """Where `take_back` pulls a case somebody else holds: the stage it came from, when that stage is the viewer's to act in."""
    if not viewer or not holders(config, case, viewer):
        return None
    came = next((e.from_ for e in reversed(case.entries) if e.to == case.stage and e.from_), None)
    if came is None:                                          # no move on record: the stage just before, in the configured order
        folders = [x.folder for x in config.stages]
        before = [f for f in folders[:folders.index(case.stage)] if config.stage(f).group not in CLOSED] if case.stage in folders else []
        came = before[-1] if before else None
    st = config.stage(came) if came else None
    if st is None or st.group in CLOSED or not st.turn or st.turn == "claude":
        return None
    return came if config.may_act(viewer, st.turn) else None


def _remind(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """A note to whoever holds the case. It adds no move of theirs (status info, not open); it makes the case new to
    them (domain/seen.py), which is the nudge."""
    if person.kind != "human":
        return _refuse(store, j, f"{person.name} may not send reminders; a person does that")
    who = holders(config, case, person.id)
    if not who:
        return _refuse(store, j, "nobody else holds this case right now")
    names = ", ".join(p.name for p in who)
    text = str(req.payload.get("text") or "").strip() or config.word("texts", "reminder_text", None, "Could you take a look at this case?")
    _write_journal(store, j)
    j.entry = _append_entry(store, config, j.case, case.stage, {"author": person.name, "status": "info", "for": names, "step": j.step_id,
                                                               "title": config.word("texts", "reminder", None, "Reminder")[:120], "text": text})
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _wait_for(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest, resolve) -> StepResult:
    """Set what the case waits for (REQ-005 DP-01, DP-04, DP-05). The list replaces the old one; an empty list ends the
    waiting. The case does not move; the thread says what changed."""
    from . import depends
    raw = req.payload.get("refs", [])
    if not isinstance(raw, list):
        return _refuse(store, j, "refs must be a list of case references")
    refs = list(dict.fromkeys(str(r).strip() for r in raw if str(r).strip()))
    resolve = resolve or depends.resolver_for(store, config)
    refusal = depends.check(store, j.case, refs, resolve)
    if refusal:
        return _refuse(store, j, refusal)
    before = depends.refs_of(case.meta)
    if refs == before:
        return _refuse(store, j, "nothing changed")
    _write_journal(store, j)
    store.write_json(f"{case.stage}/{j.case}/meta.json", {**{k: v for k, v in case.meta.items() if k != depends.KEY}, **({depends.KEY: refs} if refs else {})})
    text = (config.word("texts", "waits_for", None, "Waits for {refs}.").format(refs=", ".join(refs)) if refs
            else config.word("texts", "waits_for_nothing", None, "Waits for nothing any more."))
    j.entry = _append_entry(store, config, j.case, case.stage, {"author": person.name, "status": "info", "step": j.step_id,
                                                               "title": config.word("texts", "dependencies", None, "Dependencies")[:120], "text": text})
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _set_fields(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """Change declared fields of a case (domain/fields.py): who may move the case may change them. The case does not
    move; the thread names every change, old → new."""
    from . import fields as declared
    from .turn import actor_of
    stage = config.stage(case.stage)
    mover = actor_of(stage.turn, case) if stage else None
    if not (config.may_act(person.id, "role:operator") or (mover and config.may_act(person.id, mover))):
        return _refuse(store, j, f"{person.name} may not change this case")
    raw = req.payload.get("fields")
    if not isinstance(raw, dict) or not raw:
        return _refuse(store, j, "fields must name at least one field and its value")
    try:
        values = declared.validate(config, raw)
    except declared.FieldError as exc:
        return _refuse(store, j, str(exc))
    changed = {k: v for k, v in values.items() if str(case.meta.get(k) or "") != v}
    if not changed:
        return _refuse(store, j, "nothing changed")
    _write_journal(store, j)
    meta = {k: v for k, v in case.meta.items() if k not in changed or changed[k] != ""}
    meta.update({k: v for k, v in changed.items() if v != ""})
    store.write_json(f"{case.stage}/{j.case}/meta.json", meta)
    lines = [f"{config.word('fields', k, None, k)}: {case.meta.get(k) or '—'} → {v or '—'}" for k, v in changed.items()]
    j.entry = _append_entry(store, config, j.case, case.stage, {"author": person.name, "status": "info", "step": j.step_id,
                                                               "title": config.word("texts", "fields_changed", None, "Changed")[:120], "text": "\n".join(lines)})
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _private_point(store, person_id: str):
    """The data point only this person reads and writes — where a delegated item lands."""
    return next((p for p in store.all_points if p.readers == {person_id} and p.writers == {person_id}), None)


def _hand_on(store, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """Hand an item on between data points (REQ-005 PV-03, PV-04).

    share     the case moves into a data point the person may write (`to`: its name); its id stays.
    delegate  a new case with the next number of its label opens in the other person's private data point (`to`: the
              person), with origin, creator and link; this one closes with a reference to it. Writing into somebody
              else's private data point is the core's hand-off, not the person's right: they still cannot read it.
    """
    if not hasattr(store, "transfer"):
        return _refuse(store, j, "this application runs on one data point; there is nowhere to hand it on to")
    to = str(req.payload.get("to") or "").strip()
    if not to:
        return _refuse(store, j, "say where to: a data point (share) or a person (delegate)")
    if req.action == "share":
        try:
            dst = store.point(to)
        except StoreError as exc:
            return _refuse(store, j, str(exc))
        _write_journal(store, j)
        try:
            frm, _ = store.transfer(j.case, dst.name)
        except StoreError as exc:
            return _refuse(store, j, str(exc))
        j.entry = _append_entry(store, config, j.case, case.stage, {"author": person.name, "status": "info", "step": j.step_id,
                                "title": config.word("texts", "shared", None, "Shared")[:120],
                                "text": config.word("texts", "shared_text", None, "Moved from {frm} to {to}.").format(frm=frm, to=dst.label or dst.name)})
        j.status, j.finished = "done", _now()
        _write_journal(store, j)
        return _result(j)
    # delegate
    target = config.person(to)
    if target is None:
        return _refuse(store, j, f"'{to}' is nobody here")
    if target.id == person.id:
        return _refuse(store, j, "delegating to yourself changes nothing")
    point = _private_point(store, target.id)
    if point is None:
        return _refuse(store, j, f"{target.name} has no private data point here")
    closing = next((s.folder for s in config.stages if s.group in CLOSED), None)
    if closing is None:
        return _refuse(store, j, "this application has no stage that closes a case")
    from . import numbering
    label = str(case.meta.get("label") or case.id.split("-", 1)[0])
    create = config.theme.get("create") or {}
    number = numbering.next_number(store.everything, label, create.get("number"), case.meta)
    new_id = f"{label}-{number}"
    if store.everything.find(new_id) is not None:
        return _refuse(store, j, f"'{new_id}' already exists")
    _write_journal(store, j)
    import shutil
    src = store.case_dir(j.case)
    first = create.get("stage") or case.stage
    dst = point.store.write_root / first / new_id
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("review.md", ".*"))
    meta = {**{k: v for k, v in case.meta.items() if k not in ("waitsFor",)}, "number": number, "assignee": target.id, "created": _now()[:10],
            "created_by": person.id, "origin_kind": "other", "origin_ref": f"{j.case} ({person.name})"}
    point.store.write_json(f"{first}/{new_id}/meta.json", meta)
    text = config.word("texts", "delegated_from", None, "Delegated by {who} from {ref}.").format(who=person.name, ref=j.case)
    head = f"# Review — {new_id}\n\nAppend only. Newest entry at the end, never edited afterwards.\n"
    from ..models import Entry
    point.store.append(f"{first}/{new_id}/review.md", thread.render(Entry.model_validate({"id": "REV-001", "date": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
                       "stage": first, "author": person.name, "status": "info", "step": j.step_id, "title": config.word("texts", "delegated", None, "Delegated")[:120],
                       "text": text})), head=head)
    j.to = closing
    j.entry = _append_entry(store, config, j.case, case.stage, {"author": person.name, "status": "info", "step": j.step_id, "from": case.stage, "to": closing,
                            "title": config.word("texts", "delegated", None, "Delegated")[:120],
                            "text": config.word("texts", "delegated_to", None, "Delegated to {who} as {ref}.").format(who=target.name, ref=new_id)})
    store.move(j.case, closing)
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _take_back(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """Pull a case somebody else holds back to the stage it came from, the viewer's own. A move like any other."""
    target = take_back_target(config, case, person.id)
    if target is None:
        return _refuse(store, j, "this case cannot be taken back: nobody else holds it, or it did not come from your stage")
    if target not in store.stages():
        return _refuse(store, j, f"stage '{target}' does not exist")
    j.to = target
    _write_journal(store, j)
    return _complete(store, config, j)


# ---------------------------------------------------------------------------- undo and corrections (ADR-025)
SENT = ("_handed", "_rated", "_composed", "_compiled")    # payload marks of a step that wrote or sent something beyond the move


def undoable(store: FsStore, config: DomainConfig, case, viewer: str | None) -> Journal | None:
    """The viewer's step that `undo` would take back: their newest move on the case, while the case has not gone on
    since. Gone on = an entry after it (by anybody), the case moved, a helper ordered, or something sent or written
    beyond the move (a hand-off, a quote, a document). Then the decision is sealed and only a correction is left."""
    if not viewer or not case.entries:
        return None
    last = case.entries[-1]
    if not last.step:
        return None
    j = read_journal(store, last.step)
    if j is None or j.status != "done" or j.case != case.id or j.by != viewer:
        return None
    if j.action in BUILTIN or j.action == "undo" or not j.to or not j.from_ or j.to == j.from_:
        return None
    if case.stage != j.to or j.run or any(j.payload.get(k) for k in SENT + ("date", "url")):   # a date or link went into meta.json
        return None
    action = config.action(j.from_, j.action)
    if action is not None and (action.handover or action.run or action.compile):
        return None
    return j


def _undo(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """Take the viewer's newest move back: the case returns, the thread says so, the first step's journal reads
    `undone`. Nothing is deleted; the decision and its undoing both stay in the thread."""
    target = undoable(store, config, case, person.id)
    asked = str(req.payload.get("step") or "").strip()
    if target is None or (asked and asked != target.step_id):
        return _refuse(store, j, "nothing to undo: the case has gone on since, or the last move was not yours")
    label = config.word("actions", (config.action(target.from_, target.action).label if config.action(target.from_, target.action) else target.action), None, target.action)
    j.to = target.from_
    j.payload = {**j.payload, "step": target.step_id}
    _write_journal(store, j)
    j.entry = _append_entry(store, config, j.case, case.stage, {
        "author": person.name, "status": "undone", "step": j.step_id, "from": case.stage, "to": target.from_, "corrects": target.entry,
        "title": config.word("texts", "undone", None, "Undone: {action}").format(action=label)[:120],
        "text": str(req.payload.get("text") or "").strip() or config.word("texts", "undone_text", None, "Taken back before the next step started.")})
    _write_journal(store, j)
    return _complete(store, config, j)


def _correct(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """A sealed decision is not replaced: a correction stands next to it, with the reason and, where it changes one,
    the corrected amount. The case does not move."""
    if person.kind != "human":
        return _refuse(store, j, f"{person.name} may not correct a decision; a person does that")
    ref = str(req.payload.get("corrects") or "").strip().upper()
    src = next((e for e in case.entries if e.id == ref), None)
    if src is None or not src.step or not (src.to or src.amount) or src.status in ("undone", "correction"):
        return _refuse(store, j, f"'{ref}' is not a decision of this case")
    if any(e.corrects == src.id and e.status == "undone" for e in case.entries):
        return _refuse(store, j, f"{src.id} was undone; there is nothing to correct")
    text = str(req.payload.get("text") or "").strip()
    if not text:
        return _refuse(store, j, "a correction needs its reason")
    stage = config.stage(src.from_ or src.stage)
    if stage is not None and stage.turn and not config.may_act(person.id, stage.turn) and not config.may_act(person.id, "role:operator"):
        return _refuse(store, j, f"{person.name} may not correct this decision; it was {stage.turn}'s")
    e = {"author": person.name, "status": "correction", "step": j.step_id, "corrects": src.id, "text": text,
         "title": config.word("texts", "correction", None, "Correction: {title}").format(title=src.title)[:120]}
    if str(req.payload.get("amount") or "").strip():
        e["amount"] = str(req.payload["amount"]).strip()
    _write_journal(store, j)
    j.entry = _append_entry(store, config, j.case, case.stage, e)
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def may_reopen(config: DomainConfig, person_id: str | None, stage_id: str) -> bool:
    """A closed case goes back only by a person who may act in the stage it returns to, or by an operator (review S4):
    reopening undoes a closure, so it is not open to everyone the application knows."""
    person = config.person(person_id) if person_id else None
    if person is None or person.kind != "human":
        return False
    if config.may_act(person.id, "role:operator"):
        return True
    st = config.stage(stage_id)
    return bool(st is not None and st.turn and config.may_act(person.id, st.turn))


def _reopen(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """A person (not an agent) who may act in the stage the case returns to, or an operator, takes a closed case back;
    it returns to the stage it left, or to `payload.to` when that is an open stage. The stage's turn then says whose
    move it is."""
    if person.kind != "human":
        return _refuse(store, j, f"{person.name} may not reopen a case; a person does that")
    target = reopen_target(config, case)
    if target is None:
        return _refuse(store, j, f"the case stands in {case.stage}, which is not closed")
    asked = str(req.payload.get("to") or "").strip()
    if asked:
        st = config.stage(asked)
        if st is None or st.group in CLOSED:
            return _refuse(store, j, f"'{asked}' is not an open stage")
        target = asked
    if target not in store.stages():
        return _refuse(store, j, f"stage '{target}' does not exist")
    if not may_reopen(config, person.id, target):
        return _refuse(store, j, f"{person.name} may not move this case back to {target}; it is not their stage")
    j.to = target
    _write_journal(store, j)
    return _complete(store, config, j)


RUN_OWN = {"id", "status", "created", "started", "finished", "taken_by", "exit", "result", "log", "cost_usd", "model", "claim",
           "request_id", "retry_of", "background"}


def _retry(store: FsStore, config: DomainConfig, j: Journal, case, person) -> StepResult:
    """The last run failed: order the same skill again for the same case — its note and its own fields (a file, a target) as
    they were, a new id, `retry_of` naming the failed one. Whoever may order the skill may do it. A thread entry says so."""
    last = case.last_run
    if last is None or last.status != "failed":
        return _refuse(store, j, "the last run did not fail — nothing to run again")
    refusal = ordering.may_order(config, last.skill, person)
    if refusal:
        return _refuse(store, j, refusal)
    try:
        raw = store.read_json(f"_runs/{last.id}.json")
    except (OSError, ValueError):
        raw = {}
    extra = {k: v for k, v in raw.items() if k not in RUN_OWN and k not in ("skill", "container", "requested_by", "runner", "lang", "note")}
    extra["retry_of"] = last.id
    _write_journal(store, j)
    j.run = ordering.order(store, config, j.case, case.stage, last.skill, person.id, raw.get("note") or last.note or "", request_id=j.step_id,
                           lang=raw.get("lang"), extra=extra)
    title = config.word("texts", "retry_title", None, "{skill} started again").format(skill=config.word("skills", last.skill, None, last.skill))
    e = {"author": person.name, "status": "info", "title": title[:120], "text": (last.result or "").strip()[:600], "step": j.step_id}
    j.entry = _append_entry(store, config, j.case, case.stage, e)
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _order_again(store: FsStore, config: DomainConfig, j: Journal, case, person, req: StepRequest) -> StepResult:
    """A helper finished in this stage and the case did not move on (it handed a decision back): order the same skill
    again for this case, with the person's note on top of the original one (SYS-161)."""
    from .turn import stage_run
    last = stage_run(case)
    active = case.last_run is not None and case.last_run.status in ("queued", "running")
    if last is None or last.status != "done" or active:
        return _refuse(store, j, "no helper finished in this stage, or one is at work — nothing to send again")
    refusal = ordering.may_order(config, last.skill, person)
    if refusal:
        return _refuse(store, j, refusal)
    try:
        raw = store.read_json(f"_runs/{last.id}.json")
    except (OSError, ValueError):
        raw = {}
    extra = {k: v for k, v in raw.items() if k not in RUN_OWN and k not in ("skill", "container", "requested_by", "runner", "lang", "note")}
    extra["again_after"] = last.id
    said = str(req.payload.get("note") or req.payload.get("text") or "").strip()
    note = "\n\n".join(x for x in (raw.get("note") or last.note or "", f"{person.name}: {said}" if said else "") if x)
    _write_journal(store, j)
    j.run = ordering.order(store, config, j.case, case.stage, last.skill, person.id, note, request_id=j.step_id, lang=raw.get("lang"), extra=extra)
    title = config.word("texts", "again_title", None, "{skill} sent again").format(skill=config.word("skills", last.skill, None, last.skill))
    e = {"author": person.name, "status": "info", "title": title[:120], "text": said[:1200], "step": j.step_id}
    j.entry = _append_entry(store, config, j.case, case.stage, e)
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _builtin(store: FsStore, config: DomainConfig, j: Journal, case, person_id: str, req: StepRequest) -> StepResult:
    text = str(req.payload.get("text", "")).strip()
    person = config.person(person_id)
    if req.action in ("answer", "note") and not text:
        return _refuse(store, j, "the text is empty")
    resolves = str(req.payload.get("resolves", "")).strip().upper() or None
    if req.action in ("answer", "done"):
        if not resolves or not any(e.id == resolves for e in case.entries):
            return _refuse(store, j, f"'{resolves or ''}' is not an entry of this case")
    if req.action == "deliver":
        files = [str(f) for f in req.payload.get("files", []) if str(f).strip()]
        if not files:
            return _refuse(store, j, "nothing delivered")
    skill = str(req.payload.get("skill") or "ask").strip()
    if req.action == "ask":
        if not text:
            return _refuse(store, j, "the text is empty")
        refusal = ordering.may_order(config, skill, person)
        if refusal:
            return _refuse(store, j, refusal)
    _write_journal(store, j)
    e = {"author": person.name, "status": "resolved" if req.action in ("answer", "done") else "open" if req.action == "note" and req.payload.get("for") else "info",
         "title": str(req.payload.get("title") or ("Re: " + next((x.title for x in case.entries if x.id == resolves), "")) if resolves else req.payload.get("title") or "Note")[:120],
         "text": text or config.word("texts", req.action, None, {"done": "Done.", "deliver": "Delivered."}.get(req.action, "")),
         "step": j.step_id, "resolves": resolves}
    if req.action == "deliver":
        e["files"] = [str(f) for f in req.payload.get("files", [])]
        from .cases import split_version
        words = [config.word("files", split_version(f)[0], None, f) for f in e["files"]]
        e["title"] = str(req.payload.get("title") or config.word("texts", "delivered_title", None, "{files}").format(files=", ".join(words)))[:120]
    if req.action == "ask":
        agent = config.agent
        e["title"] = (text.splitlines()[0] if text else skill)[:120]
        e["status"] = "info"
        if agent:
            e["for"] = agent.name
        j.run = ordering.order(store, config, j.case, case.stage, skill, person_id, text, request_id=j.step_id, lang=j.payload.get("_lang"))
    target = config.person(str(req.payload.get("for", "")))
    if req.action == "answer":
        src = next((x for x in case.entries if x.id == resolves), None)
        target = config.person(src.author) if src else None
    if target and req.action != "ask":
        e["for"] = target.name
    j.entry = _append_entry(store, config, j.case, case.stage, e)
    if req.action == "deliver":
        from .cases import split_version
        delivered = {split_version(f)[0] for f in e["files"]}
        stage = config.stage(case.stage)
        for rule in (stage.auto if stage else []):
            if rule.on_file in delivered and j.run is None:
                j.run = ordering.order(store, config, j.case, case.stage, rule.skill, person_id, rule.note, request_id=f"{j.step_id}-auto", lang=j.payload.get("_lang"))
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def _complete(store: FsStore, config: DomainConfig, j: Journal, action: Action | None = None, case_meta: dict | None = None) -> StepResult:
    """Steps 4 to 6 for a journal in `intent`; safe to call again after a crash."""
    stage_now = store.find(j.case)
    if stage_now is None:
        return _refuse(store, j, f"case '{j.case}' vanished")
    if action is None:
        action = config.action(j.from_ or stage_now, j.action) if j.from_ else None
    person = config.person(j.by)
    name = person.name if person else j.by

    # 4. the thread entry, once
    rel = f"{stage_now}/{j.case}/review.md"
    existing = store.read_text(rel) if store.exists(rel) else ""
    if j.entry is None and f"**Step:** {j.step_id}" not in existing:
        label = config.word("actions", action.label if action else j.action, None, j.action)
        e = {"author": name, "status": action.entry_status if action else "info", "title": label[:120],
             "text": str(j.payload.get("note") or j.payload.get("text") or "").strip() or label,
             "step": j.step_id, "from": j.from_, "to": j.to}
        if j.payload.get("amount"):
            e["amount"] = str(j.payload["amount"])
        j.entry = _append_entry(store, config, j.case, stage_now, e)
        _write_journal(store, j)
    elif j.entry is None:
        m = re.search(rf"^## (REV-\d{{3}}) — .*\n.*\*\*Step:\*\* {re.escape(j.step_id)}", existing, re.M)
        j.entry = m.group(1) if m else None

    # 4b. payload into meta.json (a date, a link) — idempotent writes
    if j.payload and case_meta is not None or (j.payload and store.exists(f"{stage_now}/{j.case}/meta.json")):
        meta = store.case_json(j.case, "meta.json") if store.exists(f"{stage_now}/{j.case}/meta.json") else {}
        changed = False
        if j.payload.get("date") and meta.get("publishDate") != j.payload["date"]:
            meta["publishDate"], changed = str(j.payload["date"])[:10], True
        if j.payload.get("url") and meta.get("publishUrl") != j.payload["url"]:
            meta["publishUrl"], changed = str(j.payload["url"]), True
        if changed:
            store.write_json(f"{stage_now}/{j.case}/meta.json", meta)

    # 4c. a run, once
    if action and action.run and j.run is None:
        # the helper works where the case will stand: the move below takes it there before the runner takes the order
        j.run = ordering.order(store, config, j.case, (j.to or stage_now), action.run, j.by, str(j.payload.get("note") or j.payload.get("text") or ""), request_id=j.step_id,
                               lang=j.payload.get("_lang"))
        _write_journal(store, j)

    # 4d. a hand-off to another application (the rule matrix's action), once, before the move: if it fails, nothing moved
    if action and action.compile == "handoff" and not j.payload.get("_handed"):
        from .handoff import HandoffError, execute
        try:
            j.payload["_handed"] = execute(store, config, j.case, j.by)
        except (HandoffError, StoreError, OSError) as exc:
            return _refuse(store, j, str(exc))
        _write_journal(store, j)

    # 4e. a quote the core rates from the questionnaire, once, before the move: a missing answer refuses, nothing moved
    if action and action.compile == "rate" and not j.payload.get("_rated"):
        from .rating import RatingError, compile_quote
        try:
            j.payload["_rated"] = compile_quote(store, config, j.case)
        except (RatingError, StoreError, OSError, ValueError) as exc:
            return _refuse(store, j, str(exc))
        _write_journal(store, j)

    # 4f. a document the core composes from approved modules over the case's result, once, before the move
    if action and action.compile == "compose" and not j.payload.get("_composed"):
        from .compose import ComposeError, compile_document
        try:
            j.payload["_composed"] = compile_document(store, config, j.case)
        except (ComposeError, StoreError, OSError, ValueError) as exc:
            return _refuse(store, j, str(exc))
        _write_journal(store, j)

    # 5. the move, once
    if j.to and stage_now != j.to:
        if stage_now != j.from_:
            return _refuse(store, j, f"case moved meanwhile: stands in {stage_now}, expected {j.from_}")
        try:
            store.move(j.case, j.to)
        except StoreError as exc:
            return _refuse(store, j, str(exc))

    # 5b. a document the core compiles from the case's data, once per step
    if action and action.compile == "canon" and not j.payload.get("_compiled"):
        from .interview import compile_canon
        draft, decisions = next(((r.split(":") + ["", ""])[1:3] for r in action.requires if r.startswith("decided:")), ("", ""))
        if draft and decisions:
            j.payload["_compiled"] = compile_canon(store, config, j.case, draft, decisions)
            _write_journal(store, j)

    # 5c. an undo marks the step it took back, once (ADR-025)
    if j.action == "undo" and j.payload.get("step"):
        first = read_journal(store, str(j.payload["step"]))
        if first is not None and first.status == "done":
            first.status, first.reason = "undone", f"undone by {j.step_id}"
            _write_journal(store, first)

    # 6. done
    j.status, j.finished = "done", _now()
    _write_journal(store, j)
    return _result(j)


def recover(store: FsStore, config: DomainConfig) -> list[StepResult]:
    """On start: complete every journal left in `intent`."""
    out = []
    for name in store.journals():
        j = Journal.model_validate(store.read_json(f"_steps/{name}"))
        if j.status == "intent":
            with store.lock(j.case):
                out.append(_complete(store, config, j))
    return out


def detect(store: FsStore, config: DomainConfig) -> list[str]:
    """Folders moved by hand: the thread's last known stage differs from where the case stands. Record it once."""
    noted = []
    agent = config.agent
    for stage in store.stages():
        for cid in store.cases(stage):
            rel = f"{stage}/{cid}/review.md"
            if not store.exists(rel):
                continue
            entries = thread.parse(store.read_text(rel))
            if not entries:
                continue
            last = entries[-1]
            known = last.to or last.stage
            if known and known != stage and known in store.stages():
                e = {"author": agent.name if agent else "system", "status": "info", "title": config.word("texts", "detected", None, "Moved by hand"),
                     "text": config.word("texts", "detected_text", None, "The folder was found in {stage}; the thread last knew {known}.").format(stage=stage, known=known),
                     "from": known, "to": stage}
                _append_entry(store, config, cid, stage, e)
                noted.append(f"{cid}: {known} → {stage}")
    return noted
