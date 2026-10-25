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
from .turn import four_eyes_block, missing_for, primary_author

STEP_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
BUILTIN = ("answer", "note", "done", "deliver", "ask")


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


def step(store: FsStore, config: DomainConfig, case_id: str, req: StepRequest, by: str) -> StepResult:
    """Perform one step on behalf of `by` (a person id). Never raises for a refusal; returns the reason."""
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

        # ---- built-in moves: answer, note, done, deliver (an entry, never a move)
        if req.action in BUILTIN:
            return _builtin(store, config, j, case, person.id, req)

        # ---- a configured action
        stage = config.stage(case.stage)
        action = config.action(case.stage, req.action)
        if stage is None or action is None:
            return _refuse(store, j, f"'{req.action}' is not an action while the case stands in {case.stage}")
        actor = action.actor or stage.turn
        if not config.may_act(person.id, actor) and not config.may_act(person.id, "role:operator"):
            return _refuse(store, j, f"{person.name} may not {req.action} here; it is {actor}'s move")
        missing = missing_for(config, case, action)
        if missing:
            return _refuse(store, j, "still missing: " + ", ".join(missing))
        if action.four_eyes:
            author = primary_author(config, case)
            if author and author == person.id:
                return _refuse(store, j, "four eyes: you wrote the newest version and cannot approve it")
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
    skill = str(req.payload.get("skill") or ("ask" if req.action == "ask" else "interpret")).strip()
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
        j.run = ordering.order(store, config, j.case, case.stage, skill, person_id, text, request_id=j.step_id)
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
                j.run = ordering.order(store, config, j.case, case.stage, rule.skill, person_id, rule.note, request_id=f"{j.step_id}-auto")
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
        j.run = ordering.order(store, config, j.case, stage_now, action.run, j.by, str(j.payload.get("note") or j.payload.get("text") or ""), request_id=j.step_id)
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
