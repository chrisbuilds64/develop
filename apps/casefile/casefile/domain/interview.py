"""A conversation as a deliverable: questions from a pack, answers from several people, follow-ups from a helper,
then a draft that a person decides line by line and the core compiles.

Nothing here names a domain. The questions are a pack in the tree (`_packs/<id>.toml` or `.json` at the pipeline root,
named by `meta.pack`), never in this repository; a pack is somebody's licensed work. The answers are one file in the
case (the stage's `interview`, e.g. `gespraech.json`), written only here, under the case lock, atomically.

    {"anchor":   {person: "the last finished piece, in their words"},
     "answers":  {person: {question: {"text", "marker", "at", "step"}}},
     "followups":{person: {followup: {"text", "at", "step"}}},
     "done":     {person: iso}}

**No default, anywhere.** An answer carries the marker its author chose — what is (`is`), what should be (`should`),
what nobody knows for sure (`open`) — and an answer without one is refused. A preset marker became the record in 53 of
55 answers of the first real run; a valid default is caught by nothing.

The helper's files (`nachfragen-<person>.json`) are collected by the deliverable and read, never written, here:

    {"followups": [{"id", "question", "ask"}], "tensions": [{"id", "questions", "text"}],
     "drafts": [{"block", "text", "marker", "source"}]}

The draft (`kanon-entwurf.json`: {"lines": [{"id", "block", "text", "marker", "sources"}]}) is the helper's; the
decisions (`entscheide.json`: {line: {"verdict": accept|edit|reject, "text", "by", "at", "step"}}) are the person's.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import tomllib
from pathlib import Path

from ..config import DomainConfig
from ..models import Case
from ..store import FsStore, StoreError
from . import cases as reading
from . import runs as ordering

MARKERS = ("is", "should", "open")
VERDICTS = ("accept", "edit", "reject")
STEP_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
MAX_TEXT = 8000


class InterviewError(Exception):
    """A refusal in one sentence."""


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- the pack

def load_pack(root: Path, pack_id: str) -> dict:
    """The pack as the surface may see it: blocks, questions with their `why`, triggers with their words. What a
    question is for (`yields`, `seeks`) is the author's craft and stays out."""
    if not pack_id or "/" in pack_id or pack_id.startswith("."):
        raise InterviewError("the case names no pack")
    folder = Path(root) / "_packs"
    raw = None
    for ext in ("toml", "json"):
        p = folder / f"{pack_id}.{ext}"
        if p.is_file():
            raw = tomllib.loads(p.read_text(encoding="utf-8")) if ext == "toml" else json.loads(p.read_text(encoding="utf-8"))
            break
    if raw is None:
        raise InterviewError(f"pack '{pack_id}' is not in _packs/")
    meta = raw.get("pack", {})
    blocks = []
    for b in raw.get("block", []):
        qs = [{"id": q.get("id") or f"{b['id']}.{i + 1}", "text": q["text"], "why": q.get("why", "")} for i, q in enumerate(b.get("question", []))]
        blocks.append({"id": b["id"], "title": b.get("title", b["id"]), "canon": b.get("canon", ""), "lead": b.get("lead", ""), "questions": qs})
    triggers = [{"cue": t.get("cue", ""), "ask": t.get("ask", ""), "match": list(t.get("match", []))} for t in raw.get("trigger", []) if t.get("match")]
    return {"id": pack_id, "name": meta.get("name", pack_id), "version": str(meta.get("version", "")), "language": meta.get("language", ""),
            "anchor": raw.get("anchor", {}), "blocks": blocks, "triggers": triggers}


def question_ids(pack: dict) -> list[str]:
    return [q["id"] for b in pack["blocks"] for q in b["questions"]]


def block_of(pack: dict, qid: str) -> dict | None:
    return next((b for b in pack["blocks"] if any(q["id"] == qid for q in b["questions"])), None)


# ----------------------------------------------------------------------------- who answers

def interview_file(config: DomainConfig, case: Case) -> str | None:
    st = config.stage(case.stage)
    if st and st.interview:
        return st.interview
    return next((d.file for d in config.deliverables(case.label) if d.shape == "interview"), None)


def respondents(config: DomainConfig, case: Case) -> list[str]:
    """Who is asked: the case names them (`meta.respondents`), else everyone with the role."""
    named = [str(x) for x in (case.meta.get("respondents") or [])]
    if named:
        return [p.id for p in (config.person(x) for x in named) if p]
    return [p.id for p in config.people if "respondent" in p.roles]


def progress(config: DomainConfig, case: Case, pack_total: int | None = None) -> dict[str, dict]:
    """person → {answered, done}; the total comes from the pack when the caller has it."""
    name = interview_file(config, case)
    doc = case.data.get(name or "", {}) if name else {}
    out = {}
    for pid in respondents(config, case):
        answered = sum(1 for a in (doc.get("answers", {}).get(pid) or {}).values() if str(a.get("text", "")).strip() and a.get("marker") in MARKERS)
        out[pid] = {"answered": answered, "done": bool((doc.get("done") or {}).get(pid)), **({"total": pack_total} if pack_total is not None else {})}
    return out


def anyone_done(config: DomainConfig, case: Case) -> bool:
    return any(p["done"] for p in progress(config, case).values())


def undecided(case: Case, draft: str, decisions: str) -> list[str]:
    lines = [str(x.get("id")) for x in (case.data.get(draft) or {}).get("lines", []) if x.get("id")]
    done = case.data.get(decisions) or {}
    if not lines:
        return ["draft"]
    return [i for i in lines if (done.get(i) or {}).get("verdict") not in VERDICTS]


# ----------------------------------------------------------------------------- writing

def _doc(store: FsStore, case_id: str, name: str) -> dict:
    files = store.files(case_id)
    newest = reading.newest_versions(files).get(name)
    if not newest:
        return {}
    try:
        return json.loads(store.case_text(case_id, newest))
    except ValueError:
        raise InterviewError(f"{name} does not parse; fix it by hand before anybody answers again")


def _write(store: FsStore, case_id: str, name: str, doc: dict) -> None:
    stage = store.find(case_id)
    store.write_json(f"{stage}/{case_id}/{name}", doc)


def _case(store: FsStore, config: DomainConfig, case_id: str) -> Case:
    try:
        return reading.load(store, config, case_id)
    except (KeyError, StoreError):
        raise InterviewError(f"case '{case_id}' not found")


def _respondent(config: DomainConfig, case: Case, person: str) -> str:
    if interview_file(config, case) is None or not (config.stage(case.stage) and config.stage(case.stage).interview):
        raise InterviewError("this case is not in a conversation right now")
    if person not in respondents(config, case):
        p = config.person(person)
        raise InterviewError(f"{p.name if p else person} is not asked in this conversation")
    return person


def _check_step(step_id: str) -> None:
    if not STEP_ID.match(step_id or ""):
        raise InterviewError("step id must be 1–80 letters, digits, '-' or '_'")


def answer(store: FsStore, config: DomainConfig, case_id: str, person: str, qid: str, text: str, marker: str, step_id: str) -> dict:
    """One answer, whole. The same step id twice changes nothing. An empty text with a marker is refused; an empty text
    without one removes the answer (somebody cleared the field)."""
    _check_step(step_id)
    text = (text or "").strip()
    if len(text) > MAX_TEXT:
        raise InterviewError(f"an answer holds at most {MAX_TEXT} characters")
    with store.lock(case_id):
        case = _case(store, config, case_id)
        _respondent(config, case, person)
        pack = load_pack(store.root, str(case.meta.get("pack", "")))
        if qid not in question_ids(pack):
            raise InterviewError(f"'{qid}' is not a question of this conversation")
        if text and marker not in MARKERS:
            raise InterviewError("say how this answer stands: as it is, as it should be, or not known for sure")
        name = interview_file(config, case)
        doc = _doc(store, case_id, name)
        mine = doc.setdefault("answers", {}).setdefault(person, {})
        prior = mine.get(qid) or {}
        if prior.get("step") == step_id:
            return prior
        if text:
            mine[qid] = {"text": text, "marker": marker, "at": _now(), "step": step_id}
        else:
            mine.pop(qid, None)
        _write(store, case_id, name, doc)
        return mine.get(qid, {})


def anchor(store: FsStore, config: DomainConfig, case_id: str, person: str, text: str) -> str:
    text = (text or "").strip()[:200]
    if not text:
        raise InterviewError("name the piece in a few words")
    with store.lock(case_id):
        case = _case(store, config, case_id)
        _respondent(config, case, person)
        name = interview_file(config, case)
        doc = _doc(store, case_id, name)
        doc.setdefault("anchor", {})[person] = text
        _write(store, case_id, name, doc)
    return text


def followup(store: FsStore, config: DomainConfig, case_id: str, person: str, fid: str, text: str, step_id: str) -> dict:
    """The answer to a follow-up the helper asked this person."""
    _check_step(step_id)
    text = (text or "").strip()[:MAX_TEXT]
    with store.lock(case_id):
        case = _case(store, config, case_id)
        _respondent(config, case, person)
        asked = {f.get("id") for f in (case.data.get(f"nachfragen-{person}.json") or {}).get("followups", [])}
        if fid not in asked:
            raise InterviewError("no such follow-up for you")
        name = interview_file(config, case)
        doc = _doc(store, case_id, name)
        mine = doc.setdefault("followups", {}).setdefault(person, {})
        if (mine.get(fid) or {}).get("step") == step_id:
            return mine[fid]
        if text:
            mine[fid] = {"text": text, "at": _now(), "step": step_id}
        else:
            mine.pop(fid, None)
        _write(store, case_id, name, doc)
        return mine.get(fid, {})


def chapter(store: FsStore, config: DomainConfig, case_id: str, person: str, block_id: str, skill: str, step_id: str) -> str | None:
    """A person left a chapter with answers in it: the helper reads it in the background. Returns the run id, or None
    when the policy has no such helper (the conversation goes on without follow-ups)."""
    _check_step(step_id)
    case = _case(store, config, case_id)
    _respondent(config, case, person)
    pack = load_pack(store.root, str(case.meta.get("pack", "")))
    block = next((b for b in pack["blocks"] if b["id"] == block_id), None)
    if block is None:
        raise InterviewError(f"'{block_id}' is not a chapter of this conversation")
    if skill not in (config.run_policy.get("skills") or {}):
        return None
    p = config.person(person)
    if ordering.may_order(config, skill, p):
        return None
    return ordering.order(store, config, case_id, case.stage, skill, person, f"person={person} block={block_id}", request_id=step_id, background=True)


def finish(store: FsStore, config: DomainConfig, case_id: str, person: str, step_id: str) -> bool:
    """A person says they are done. Their answers stay editable until the conversation closes; done is a statement, not a lock."""
    _check_step(step_id)
    with store.lock(case_id):
        case = _case(store, config, case_id)
        _respondent(config, case, person)
        name = interview_file(config, case)
        doc = _doc(store, case_id, name)
        if not any(str(a.get("text", "")).strip() for a in (doc.get("answers", {}).get(person) or {}).values()):
            raise InterviewError("answer at least one question first")
        if (doc.get("done") or {}).get(person):
            return False
        doc.setdefault("done", {})[person] = _now()
        _write(store, case_id, name, doc)
        return True


def decide(store: FsStore, config: DomainConfig, case_id: str, person: str, line: str, verdict: str, text: str, step_id: str,
           draft: str, decisions: str, role: str = "decider") -> dict:
    """One line of the draft: accepted, changed, or rejected — by the person who decides, nobody else."""
    _check_step(step_id)
    if verdict not in VERDICTS and verdict != "undo":
        raise InterviewError("accept, edit, reject or undo")
    with store.lock(case_id):
        case = _case(store, config, case_id)
        p = config.person(person)
        if not p or role not in p.roles:
            raise InterviewError(f"only the {config.word('roles', role, None, role)} decides the canon")
        ids = {str(x.get("id")) for x in (case.data.get(draft) or {}).get("lines", [])}
        if line not in ids:
            raise InterviewError(f"'{line}' is not a line of the draft")
        text = (text or "").strip()[:2000]
        if verdict == "edit" and not text:
            raise InterviewError("a changed line needs its new wording")
        doc = _doc(store, case_id, decisions)
        if (doc.get(line) or {}).get("step") == step_id:
            return doc[line]
        if verdict == "undo":
            doc.pop(line, None)
        else:
            doc[line] = {"verdict": verdict, "by": p.id, "at": _now(), "step": step_id, **({"text": text} if verdict == "edit" else {})}
        _write(store, case_id, decisions, doc)
        return doc.get(line, {})


# ----------------------------------------------------------------------------- the canon map

CANON_DIR = "_kanon"                                   # the layers above the areas: basis.md, marke.md — at the pipeline root


def canon_layer(root: Path, name: str) -> dict:
    """One layer above the areas, as the map shows it: present or still open, its title and how many rules it holds."""
    f = Path(root) / CANON_DIR / f"{name}.md"
    if not f.is_file():
        return {"present": False, "title": "", "rules": 0}
    text = f.read_text(encoding="utf-8", errors="replace")
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), name)
    return {"present": True, "title": title, "rules": len(re.findall(r"^## ", text, re.M))}


def canon_map(store: FsStore, current: str = "") -> dict:
    """Where a canon stands among the others (canonical-hierarchy, depth): the basis and the brand above, every area this
    workspace elicits beside it. An area is a case that names a pack; its version is its newest compiled canon, 0 while
    it is still being worked out. The brand is never derived from process answers — absent, it stays open."""
    areas = []
    for stage in store.stages():
        for cid in store.cases(stage):
            try:
                meta = store.case_json(cid, "meta.json")
            except (StoreError, OSError, ValueError):
                continue
            if not meta.get("pack"):
                continue
            canon = reading.newest_versions(store.files(cid)).get("canon.md")
            areas.append({"case": cid, "title": str(meta.get("title") or cid), "current": cid == current,
                          "version": max(1, reading.split_version(canon)[1]) if canon else 0})
    areas.sort(key=lambda a: (a["version"] == 0, a["title"]))
    return {"basis": canon_layer(store.root, "basis"), "marke": canon_layer(store.root, "marke"), "areas": areas}


# ----------------------------------------------------------------------------- the canon, compiled

def compile_canon(store: FsStore, config: DomainConfig, case_id: str, draft: str, decisions: str, target: str = "canon.md", lang: str | None = None) -> str:
    """The accepted and changed lines, grouped by chapter, each with where it came from. A new version beside the old
    one, never an overwrite. Returns the file written."""
    from .assets import next_name
    case = _case(store, config, case_id)
    lines = (case.data.get(draft) or {}).get("lines", [])
    decided = case.data.get(decisions) or {}
    try:
        pack = load_pack(store.root, str(case.meta.get("pack", "")))
    except InterviewError:
        pack = {"blocks": []}
    titles = {b["id"]: (b.get("canon") or b["title"]) for b in pack["blocks"]}
    chapter = {b["id"]: re.sub(r"^Block \d+ — ", "", b["title"]) for b in pack["blocks"]}
    order = [b["id"] for b in pack["blocks"]]
    w = lambda k, d: config.word("texts", k, lang, d)
    marker_word = {m: config.word("markers", m, lang, m) for m in MARKERS}
    out = [f"# {w('canon_title', 'Canon')} — {case.meta.get('title') or case_id}", "",
           w("canon_lead", "Approved line by line. What was rejected is not here; what was changed stands in its new wording."), "",
           f"*{w('canon_scope', 'Layer: area — process and procedures. The basis and the brand above it take precedence.')}*", ""]
    kept = [x for x in lines if (decided.get(str(x.get("id"))) or {}).get("verdict") in ("accept", "edit")]
    for bid in order + sorted({str(x.get("block")) for x in kept} - set(order)):
        group = [x for x in kept if str(x.get("block")) == bid]
        if not group:
            continue
        out += [f"## {titles.get(bid, bid)}", ""]
        for x in group:
            d = decided[str(x["id"])]
            text = d.get("text") if d.get("verdict") == "edit" else x.get("text", "")
            m = marker_word.get(str(x.get("marker")), "")
            out.append(f"- **{x['id']}** {text}" + (f" *({m})*" if m else ""))
            for s in x.get("sources", [])[:2]:
                who = config.person(str(s.get("person", "")))
                bid, _, n = str(s.get("question", "")).partition(".")
                place = f"{chapter.get(bid, bid)}, {w('question_word', 'question')} {n}" if n else str(s.get("question", ""))
                out.append(f"  > „{str(s.get('quote', '')).strip()}“ — {who.name if who else s.get('person', '')}, {place}")
        out.append("")
    person = config.person(next((d.get("by") for d in decided.values() if d.get("by")), "") or "")
    out += ["---", "", w("canon_foot", "Approved by {who} on {date}. Version 0.1: a draft of the operation, not its final state; the second pass after four weeks of real work belongs to it.")
            .replace("{who}", person.name if person else "—").replace("{date}", dt.date.today().isoformat()), ""]
    name = next_name(store.files(case_id), target)
    stage = store.find(case_id)
    store.write_atomic(f"{stage}/{case_id}/{name}", "\n".join(out))
    return name
