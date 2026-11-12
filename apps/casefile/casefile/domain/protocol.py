"""Gate protocols (ADR-029, REQ-003): what a person checked before a gate opened.

Nothing here names a domain. A protocol is a deliverable of the case (`protocol-<id>.json`, a new version `.v2` when a case
comes back to the same gate), written only here, under the case lock, atomically. Its items come from a template — the
application's `protocols/<id>.json`, or the workspace's own `_protocols/<id>.json` in the tree, which wins — plus the
templates and catalogue entries it includes (the Definition of Done, ADR-029 decision 10), plus case items.

    template:  {"id", "title": {lang: str}, "include": ["<template or catalogue id>", …], "skip": false | {"role": "<role>"},
                "items": [{"id", "question": {lang: str}, "type": "yesno|number|choice|evidence",
                           "criterion": {"eq"|"min"|"max": n} | {"allowed": [..]}, "options": [..],
                           "must": true, "role": "<role>", "agent": false, "rule": "<catalogue entry>"}]}

    protocol:  {"template", "version", "rules": {item: rule}, "items": [... + "origin", "struck"],
                "answers": {item: {"verdict": "pass|fail|na", "value", "note", "evidence", "by", "role", "at", "step"}},
                "observations": {item: [{"by", "note", "evidence", "at"}]}, "steps": [step ids], "sealed": {"by", "at"},
                "skipped": {"by", "at", "reason", "step"}}

**Nothing is preset** (the interview's lesson): an item without a verdict is open, and a verdict exists only when someone in
the item's role gave it. Not applicable needs a reason; failed needs what was seen. An agent answers for good only an item
marked `agent` (an objective check); elsewhere its answer is an observation, and the person decides. The gate reads the
protocol (`requires: ["protocol:<id>"]`): sealed, and every must-item passed or not applicable. `when: ["failed:<id>"]`
offers the way back while a must-item failed.

**A protocol may be skipped as a whole** (GP-43, GP-44): by a person who holds the gate — or the role the template's `skip`
names; `"skip": false` forbids it — with a reason. The gate opens, the way back is no longer offered, and the record says
that nothing was checked here. An agent never skips.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ..config import DomainConfig
from ..store import FsStore
from . import cases as reading

TYPES = ("yesno", "number", "choice", "evidence")
VERDICTS = ("pass", "fail", "na")


class ProtocolError(Exception):
    """A sentence for the person, never a stack trace."""


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- templates

def _template_file(config: DomainConfig, root: Path | None, tid: str) -> Path | None:
    for base in ([Path(root) / "_protocols"] if root else []) + [Path(config.dir) / "protocols"]:
        f = base / f"{tid}.json"
        if f.is_file():
            return f
    return None


def load_template(config: DomainConfig, root: Path | None, tid: str, _seen: tuple = ()) -> dict:
    """The template with everything it includes, flattened: items in order, each once, each knowing where it came from."""
    if tid in _seen:
        raise ProtocolError(f"protocol template '{tid}' includes itself")
    f = _template_file(config, root, tid)
    if f is None:
        raise ProtocolError(f"no protocol template '{tid}'")
    doc = json.loads(f.read_text(encoding="utf-8"))
    items: list[dict] = []
    for inc in doc.get("include") or []:
        for it in load_template(config, root, str(inc), _seen + (tid,))["items"]:
            own = it.get("origin") == f"template:{inc}"        # the included file's own items are catalogue entries here
            items.append({**it, "origin": f"catalogue:{inc}" if own else it["origin"]})
    for it in doc.get("items") or []:
        items.append({**it, "origin": it.get("origin") or f"template:{tid}"})
    seen, out = set(), []
    for it in items:
        _check_item(it, f"template '{tid}'")
        if it["id"] in seen:
            continue                                     # the first wins: an included rule is not asked twice
        seen.add(it["id"])
        out.append(it)
    return {"id": tid, "title": doc.get("title") or {}, "items": out}


def _criteria_stage(config: DomainConfig, root: Path | None, tid: str) -> dict | None:
    """`"criteria": {"stage": "ENTW", "from": "task.md"}` in a template: its case items are the task's criteria for that stage."""
    f = _template_file(config, root, tid)
    if f is None:
        return None
    c = json.loads(f.read_text(encoding="utf-8")).get("criteria")
    return c if isinstance(c, dict) and c.get("stage") else None


def _check_item(it: dict, where: str) -> None:
    if not it.get("id") or not isinstance(it.get("id"), str):
        raise ProtocolError(f"{where}: an item needs an id")
    if it.get("type") not in TYPES:
        raise ProtocolError(f"{where}: item '{it['id']}' has type '{it.get('type')}' — one of {', '.join(TYPES)}")
    if it["type"] == "choice" and not (it.get("criterion") or {}).get("allowed"):
        raise ProtocolError(f"{where}: choice item '{it['id']}' names no allowed values")


# ----------------------------------------------------------------------------- the file

def file_of(case, tid: str) -> str | None:
    """The newest protocol file of this template in the case, or None."""
    newest = reading.newest_versions(case.files)
    return newest.get(f"protocol-{tid}.json")


def _read(store: FsStore, case_id: str, name: str) -> dict:
    return json.loads(store.case_text(case_id, name))


def _write(store: FsStore, case_id: str, name: str, doc: dict) -> None:
    store.write_json(f"{store.find(case_id)}/{case_id}/{name}", doc)


def start(store: FsStore, config: DomainConfig, case_id: str, tid: str, by: str, items: list[dict] | None = None, locked: bool = False) -> str:
    """The protocol for this gate: the template's items plus case items (a helper's, from the task). A sealed one stays as it
    is and a new version starts (GP-12); an open one is returned as it is."""
    case = reading.load(store, config, case_id)
    current = file_of(case, tid)
    if current:
        doc = _read(store, case_id, current)
        if not _ended(doc):
            return current
        version = int(doc.get("version", 1)) + 1
        name = f"protocol-{tid}.v{version}.json"
    else:
        version, name = 1, f"protocol-{tid}.json"
    tpl = load_template(config, store.root, tid)
    extra = []
    wants = _criteria_stage(config, store.root, tid)          # the template asks for the task's acceptance criteria of a stage
    if wants:
        from . import criteria as acs
        task = reading.newest_versions(case.files).get(str(wants.get("from") or "task.md"))
        if task:
            found, _bad = acs.parse(store.case_text(case_id, task))
            extra += acs.items_for(found, str(wants["stage"]), config.lang)
    for it in items or []:
        _check_item(it, "case item")
        extra.append({**it, "origin": it.get("origin") or f"case:{by}"})
    ids = {i["id"] for i in tpl["items"]}
    doc = {"template": tid, "version": version, "title": tpl["title"], "started": {"by": by, "at": _now()},
           "items": tpl["items"] + [i for i in extra if i["id"] not in ids], "answers": {}, "observations": {}, "steps": [], "sealed": None}
    if locked:                                                # a step that holds the case's lock starts it (going back, ADR-035)
        _write(store, case_id, name, doc)
        return name
    with store.lock(case_id):
        _write(store, case_id, name, doc)
    return name


def _load(store: FsStore, config: DomainConfig, case_id: str, tid: str) -> tuple[str, dict]:
    case = reading.load(store, config, case_id)
    name = file_of(case, tid)
    if not name:
        raise ProtocolError(f"no protocol '{tid}' in this case — start it first")
    doc = _read(store, case_id, name)
    if _ended(doc):
        raise ProtocolError(f"protocol '{tid}' is {'skipped' if doc.get('skipped') else 'sealed'}; a change starts a new version")
    return name, doc


def _ended(doc: dict) -> bool:
    return bool(doc.get("sealed") or doc.get("skipped"))


def _item(doc: dict, iid: str) -> dict:
    it = next((i for i in doc["items"] if i["id"] == iid), None)
    if it is None:
        raise ProtocolError(f"no item '{iid}' in this protocol")
    return it


def _replayed(doc: dict, step_id: str) -> bool:
    return bool(step_id) and step_id in (doc.get("steps") or [])


def _done(doc: dict, step_id: str) -> None:
    doc.setdefault("steps", []).append(step_id)


# ----------------------------------------------------------------------------- before the first verdict: shape the list

def add_item(store: FsStore, config: DomainConfig, case_id: str, tid: str, by: str, item: dict, step_id: str) -> dict:
    name, doc = _load(store, config, case_id, tid)
    if _replayed(doc, step_id):
        return doc
    if doc["answers"]:
        raise ProtocolError("items are added before the first verdict")
    _check_item(item, "new item")
    if any(i["id"] == item["id"] for i in doc["items"]):
        raise ProtocolError(f"item '{item['id']}' exists")
    doc["items"].append({**item, "origin": f"person:{by}"})
    _done(doc, step_id)
    with store.lock(case_id):
        _write(store, case_id, name, doc)
    return doc


def strike_item(store: FsStore, config: DomainConfig, case_id: str, tid: str, by: str, iid: str, reason: str, step_id: str) -> dict:
    name, doc = _load(store, config, case_id, tid)
    if _replayed(doc, step_id):
        return doc
    if doc["answers"]:
        raise ProtocolError("items are struck before the first verdict")
    if not reason.strip():
        raise ProtocolError("striking an item needs a reason")
    it = _item(doc, iid)
    it["struck"] = {"by": by, "at": _now(), "reason": reason.strip()}
    _done(doc, step_id)
    with store.lock(case_id):
        _write(store, case_id, name, doc)
    return doc


# ----------------------------------------------------------------------------- the verdicts

def verdict_of(item: dict, value) -> str:
    """pass or fail, from the item's type and criterion — never a default."""
    t, crit = item["type"], item.get("criterion") or {}
    if t == "yesno":
        if not isinstance(value, bool):
            raise ProtocolError("this item is answered yes or no")
        return "pass" if value else "fail"
    if t == "number":
        try:
            n = float(value)
        except (TypeError, ValueError):
            raise ProtocolError("this item is answered with a number")
        ok = ("eq" not in crit or n == float(crit["eq"])) and ("min" not in crit or n >= float(crit["min"])) and ("max" not in crit or n <= float(crit["max"]))
        return "pass" if ok else "fail"
    if t == "choice":
        options = item.get("options") or crit.get("allowed") or []
        if value not in options:
            raise ProtocolError(f"choose one of: {', '.join(map(str, options))}")
        return "pass" if value in crit.get("allowed", []) else "fail"
    if not str(value or "").strip():                       # evidence: text, a file in the case, a link
        raise ProtocolError("this item needs its evidence: a note, a file or a link")
    return "pass"


def _may_answer(config: DomainConfig, item: dict, person_id: str) -> str:
    """'verdict' when this person answers for good, 'observation' when an agent may only observe; refuses everyone else."""
    p = config.person(person_id)
    if p is None:
        raise ProtocolError(f"'{person_id}' is not a person here")
    role = item.get("role")
    if p.kind == "agent":
        if item.get("agent") and (not role or config.may_act(p.id, f"role:{role}")):
            return "verdict"
        return "observation"                               # judgement stays a person's: the agent observes, attaches evidence
    if role and not config.may_act(p.id, f"role:{role}"):
        raise ProtocolError(f"this item is answered by the role {role}")
    return "verdict"


def answer(store: FsStore, config: DomainConfig, case_id: str, tid: str, by: str, iid: str, step_id: str,
           value=None, na: bool = False, note: str = "", evidence: list[str] | None = None) -> dict:
    name, doc = _load(store, config, case_id, tid)
    if _replayed(doc, step_id):
        return doc
    it = _item(doc, iid)
    if it.get("struck"):
        raise ProtocolError(f"item '{iid}' is struck")
    how = _may_answer(config, it, by)
    note = note.strip()
    if na:
        if not note:
            raise ProtocolError("not applicable needs a reason")
        verdict = "na"
    else:
        verdict = verdict_of(it, value if it["type"] != "evidence" else (value or note or (evidence or [""])[0]))
        if verdict == "fail" and not note:
            raise ProtocolError("a failed item needs what was seen")
    entry = {"verdict": verdict, "value": value, "note": note, "evidence": list(evidence or []), "by": by, "at": _now(), "step": step_id}
    if how == "observation":
        doc.setdefault("observations", {}).setdefault(iid, []).append({k: v for k, v in entry.items() if k != "verdict"} | {"suggests": verdict})
    else:
        doc["answers"][iid] = entry
    _done(doc, step_id)
    with store.lock(case_id):
        _write(store, case_id, name, doc)
    return doc


# ----------------------------------------------------------------------------- reading it

def live(doc: dict) -> list[dict]:
    return [i for i in doc.get("items") or [] if not i.get("struck")]


def state(doc: dict) -> dict:
    """{'open': [...], 'failed_must': [...], 'failed_should': [...], 'passed': [...], 'gate_open': bool, 'complete': bool,
    'skipped': bool} — a skipped protocol opens the gate whatever its answers say."""
    out = {"open": [], "failed_must": [], "failed_should": [], "passed": []}
    for it in live(doc):
        a = (doc.get("answers") or {}).get(it["id"])
        if a is None:
            out["open"].append(it["id"])
        elif a["verdict"] == "fail":
            out["failed_must" if it.get("must", True) else "failed_should"].append(it["id"])
        else:
            out["passed"].append(it["id"])
    must_open = [i for i in out["open"] if next(x for x in live(doc) if x["id"] == i).get("must", True)]
    out["complete"] = not out["open"]
    out["skipped"] = bool(doc.get("skipped"))
    out["gate_open"] = out["skipped"] or (bool(doc.get("sealed")) and not out["failed_must"] and not must_open)
    return out


def seal(store: FsStore, config: DomainConfig, case_id: str, tid: str, by: str, step_id: str, lang: str | None = None) -> dict:
    """Every live item answered: the protocol is sealed with the person and the time, and a readable record is compiled beside it."""
    name, doc = _load(store, config, case_id, tid)
    if _replayed(doc, step_id):
        return doc
    st = state(doc)
    if st["open"]:
        raise ProtocolError(f"still open: {', '.join(st['open'])}")
    p = config.person(by)
    if p is None or p.kind != "human":
        raise ProtocolError("a protocol is sealed by a person")
    doc["sealed"] = {"by": by, "at": _now(), "step": step_id}
    _done(doc, step_id)
    record = compile_record(config, doc, lang)
    with store.lock(case_id):
        _write(store, case_id, name, doc)
        store.write_atomic(f"{store.find(case_id)}/{case_id}/{name[:-5]}.md", record)
    return doc


# ----------------------------------------------------------------------------- skipping it as a whole (GP-43, GP-44)

def skip_actor(config: DomainConfig, case, tid: str, root: Path | None) -> str | None:
    """Who may skip this protocol: the template's `"skip": {"role": r}` names a role; `false` nobody; absent, whoever holds
    the gate — the actor of the action that requires the protocol, else its stage's turn (the case's stage first)."""
    f = _template_file(config, root, tid)
    rule = json.loads(f.read_text(encoding="utf-8")).get("skip", True) if f else True
    if rule is False:
        return None
    if isinstance(rule, dict) and rule.get("role"):
        return f"role:{rule['role']}"
    from .turn import actor_of
    here = config.stage(case.stage)
    for st in ([here] if here else []) + [s for s in config.stages if s is not here]:
        for a in st.actions:
            if f"protocol:{tid}" in a.requires:
                from .turn import stage_actor
                return actor_of(a.actor, case) or stage_actor(st, case)
    return None


def may_skip(config: DomainConfig, case, tid: str, person_id: str | None, root: Path | None) -> bool:
    p = config.person(person_id)
    if p is None or p.kind != "human":
        return False
    who = skip_actor(config, case, tid, root)
    return bool(who) and config.may_act(p.id, who)


def skip(store: FsStore, config: DomainConfig, case_id: str, tid: str, by: str, reason: str, step_id: str, lang: str | None = None) -> dict:
    """The whole protocol left out on purpose: recorded like a seal (who, when, why), answers already given stay, the gate opens."""
    case = reading.load(store, config, case_id)
    current = file_of(case, tid)
    if current:
        doc = _read(store, case_id, current)
        if _replayed(doc, step_id):
            return doc
    p = config.person(by)
    if p is None or p.kind != "human":
        raise ProtocolError("a protocol is skipped by a person, never by an agent")
    who = skip_actor(config, case, tid, store.root)
    if who is None:
        raise ProtocolError(f"protocol '{tid}' may not be skipped here — its template says so")
    if not config.may_act(p.id, who):
        raise ProtocolError(f"this protocol is skipped by {who.removeprefix('role:').removeprefix('person:')}")
    if not reason.strip():
        raise ProtocolError("skipping a protocol needs a reason")
    if not current:
        start(store, config, case_id, tid, by)
    name, doc = _load(store, config, case_id, tid)
    doc["skipped"] = {"by": by, "at": _now(), "reason": reason.strip(), "step": step_id}
    _done(doc, step_id)
    record = compile_record(config, doc, lang)
    with store.lock(case_id):
        _write(store, case_id, name, doc)
        store.write_atomic(f"{store.find(case_id)}/{case_id}/{name[:-5]}.md", record)
    return doc


def compile_record(config: DomainConfig, doc: dict, lang: str | None = None) -> str:
    lang = lang or config.lang
    pick = lambda d, fb: (d or {}).get(lang) or (d or {}).get("en") or fb  # noqa: E731
    sym = {"pass": "✓", "fail": "✗", "na": "–"}
    st = state(doc)
    lines = [f"# {pick(doc.get('title'), doc['template'])} · v{doc.get('version', 1)}", ""]
    if doc.get("sealed"):
        s = doc["sealed"]
        lines += [f"Sealed by {s['by']} · {s['at']} · gate {'open' if st['gate_open'] else 'closed'}", ""]
    if doc.get("skipped"):
        s = doc["skipped"]
        lines += [f"Skipped by {s['by']} · {s['at']} · reason: {s['reason']} · gate open without the check", ""]
    lines += ["| | Item | Must | Answer | By | Evidence |", "|---|---|---|---|---|---|"]
    for it in doc.get("items") or []:
        q = pick(it.get("question"), it["id"]).replace("|", "/")
        if it.get("struck"):
            lines.append(f"| ~ | ~~{q}~~ | | struck: {it['struck']['reason']} | {it['struck']['by']} | |")
            continue
        a = (doc.get("answers") or {}).get(it["id"]) or {}
        shown = a.get("note") or ("" if a.get("value") is None else str(a.get("value")))
        if not a and doc.get("skipped"):
            shown = "not checked"
        lines.append(f"| {sym.get(a.get('verdict'), '·')} | {q} | {'must' if it.get('must', True) else 'should'} | {shown.replace('|', '/')} | "
                     f"{a.get('by', '')} | {', '.join(a.get('evidence') or [])} |")
    obs = doc.get("observations") or {}
    if obs:
        lines += ["", "## Observations", ""]
        for iid, xs in obs.items():
            for o in xs:
                lines.append(f"- `{iid}` · {o['by']}: {o.get('note') or o.get('value')} (suggests {o.get('suggests')})")
    origins = sorted({it.get("origin", "") for it in doc.get("items") or []})
    lines += ["", "Items from: " + ", ".join(o for o in origins if o), ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- the gate

def gate_open(case, tid: str) -> bool:
    doc = (case.data or {}).get(f"protocol-{tid}.json")
    return bool(doc) and state(doc)["gate_open"]


def failed(case, tid: str) -> bool:
    doc = (case.data or {}).get(f"protocol-{tid}.json")
    st = state(doc) if doc else None
    return bool(st) and bool(st["failed_must"]) and not st["skipped"]
