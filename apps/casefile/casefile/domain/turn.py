"""Whose move is it. One pure function; surface, CLI and agents all call this one.

The rule, in order (Bauplan §4, from the operating concept §7):
1. a run is running → Claude's move, nobody else's; work handed out of the case runs → the same wait (domain/outside.py);
2. the last run failed → the operator's move: see what went wrong;
3. open thread entries addressed to a person, not resolved → that person's move, one turn per entry;
4. otherwise by stage: whose turn, which action, which deliverables it needs;
5. four eyes: the one who approves is not the one who wrote the newest version of the primary.
"""

from __future__ import annotations

from ..config import DomainConfig
from ..models import Action, Case, Turn
from . import entries as thread

OPERATOR = "role:operator"


def _label(config: DomainConfig, key: str, lang: str | None) -> str:
    return config.word("actions", key, lang, key)


def missing_for(config: DomainConfig, case: Case, action: Action) -> list[str]:
    """Deliverables the action needs that are not in the case. Tokens: 'primary', 'required', 'shape:<prefix>', a file name, or alternatives 'a.pdf|a.md'."""
    out: list[str] = []
    for req in action.requires:
        if req == "answered":                                  # a conversation: at least one respondent said they are done
            from .interview import anyone_done
            if not anyone_done(config, case):
                out.append("answered")
        elif req.startswith("decided:"):                       # every line of a draft decided: 'decided:<draft>:<decisions>'
            from .interview import undecided
            _, draft, decisions = (req.split(":") + ["", ""])[:3]
            if undecided(case, draft, decisions):
                out.append(req)
        elif req == "criteria" or req.startswith("criteria:"):  # Definition of Ready: the task carries readable acceptance criteria
            got = (case.data or {}).get("_criteria") or {}
            if not got.get("found") or got.get("bad"):
                out.append(req)
        elif req.startswith("protocol:"):                       # a gate protocol sealed with every must-item passed (ADR-029)
            from .protocol import gate_open
            raised = f"protocol-{req[9:]}.json" in (case.data or {})
            if not gate_open(case, req[9:]) and (raised or not action.protocol_on_demand):
                out.append(req)
        elif req.startswith("failed:"):                         # a must-item of that protocol failed: the way back is offered
            from .protocol import failed
            if not failed(case, req[7:]):
                out.append(req)
        elif req == "primary":
            p = config.primary(case.label)
            if p and not (case.slot(p) and case.slot(p).present):
                out.append(p)
        elif req == "required":
            out += [s.file for s in case.slots if s.required and not s.present]
        elif req.startswith("shape:"):
            if not any(s.present and s.shape.startswith(req[6:]) for s in case.slots):
                out.append(req)
        elif "|" in req:
            alts = [case.slot(r) for r in req.split("|")]
            if not any(a and a.present for a in alts):
                out.append(req.split("|")[0])
        else:
            s = case.slot(req)
            if not (s and s.present):
                out.append(req)
    return out


def offered(config: DomainConfig, case: Case, action: Action) -> bool:
    """`when`: the action exists for this case only when its condition holds — same tokens as `requires`."""
    return not action.when or not missing_for(config, case, action.model_copy(update={"requires": action.when}))


def primary_author(config: DomainConfig, case: Case) -> str | None:
    """Who made the newest version of the primary deliverable, as far as the thread says."""
    p = config.primary(case.label)
    if not p:
        return None
    for e in reversed(case.entries):
        if any(f == p or f.startswith(p.rsplit(".", 1)[0] + ".v") for f in e.files):
            person = config.person(e.author)
            return person.id if person else e.author
    for r in reversed(case.runs):
        if r.status == "done":
            agent = config.agent
            return agent.id if agent else "claude"
    author = case.meta.get("author") or case.meta.get("created_by")
    if author:
        person = config.person(str(author))
        return person.id if person else str(author)
    return None


def four_eyes_block(config: DomainConfig, case: Case, action: Action, actor: str) -> str | None:
    """A sentence when the only possible approver is the author, else None. Decided per person in `may_act()`; here per role."""
    if not action.four_eyes:
        return None
    author = primary_author(config, case)
    if not author:
        return None
    persons = [p.id for p in config.persons_for(actor)]
    if persons and all(p == author for p in persons):
        return f"four eyes: {author} wrote the newest version and cannot approve it"
    return None


def actor_of(actor: str | None, case: Case) -> str | None:
    """`field:<key>` names whoever the case's meta holds under that key (the worklist's assignee): `person:<id>`.
    Empty field, nobody's move. Every other actor stays as it is."""
    if actor and actor.startswith("field:"):
        who = str(case.meta.get(actor[6:]) or "").strip()
        return f"person:{who}" if who else None
    return actor


HELD = "held"                                   # meta.json: {"stage", "person", "by", "at"} — somebody took this stage's move over


def stage_actor(stage, case: Case) -> str | None:
    """Whose move a stage is for this case: its turn — or the one person who took the case over while it stands here
    (REQ-001 T-10: somebody is ill, the process goes on). The take-over holds for this stage only; a helper's stage is
    nobody's to take. An action's own actor (a gate's role) is never replaced by it."""
    if stage is None or not stage.turn:
        return None
    held = case.meta.get(HELD)
    if stage.turn != "claude" and isinstance(held, dict) and held.get("stage") == case.stage == stage.folder and held.get("person"):
        return f"person:{held['person']}"
    return actor_of(stage.turn, case)


def turn(case: Case, config: DomainConfig, lang: str | None = None) -> list[Turn]:
    out: list[Turn] = []
    run = case.last_run

    # 1. a helper is at work
    if run and run.status in ("running", "queued"):
        agent = config.agent
        return [Turn(actor="claude", action="wait", label=_label(config, "wait", lang), blocked_by=[],
                     reason=config.word("reasons", "running", lang, "a helper is working on it"), since=run.started or run.created)]

    # 1b. work for the case runs outside it (REQ-001 T-08): a wait like a helper's, in the application's words
    from .outside import standing, words
    away = standing(case)
    if away:
        return [Turn(actor="claude", action="wait", label=_label(config, "wait", lang), blocked_by=[],
                     reason=words(config, away, lang), since=str(away.get("since") or ""))]

    # 2. the last run failed
    if run and run.status == "failed":
        # Whoever may order the skill may order it again (run-policy `orderable_by`); the operator role when none of those is held.
        from .runs import policy_for
        roles = [r for r in policy_for(config, run.skill).get("orderable_by", []) if any(r in p.roles for p in config.people)]
        why = config.word("reasons", "failed", lang, "the last run failed")
        first = (run.result or "").strip().splitlines()[0][:160] if (run.result or "").strip() else ""
        label = config.word("actions", "retry", lang, "Erneut starten" if (lang or config.lang) == "de" else "Run again")
        out.append(Turn(actor=f"role:{roles[0]}" if roles else OPERATOR, action="retry", label=label, blocked_by=[],
                        reason=f"{why}: {first}" if first else why, since=run.finished or run.created))

    # 3. open entries addressed to a person
    for e in thread.open_for(case.entries, None):
        person = config.person(e.for_)
        if not person:
            continue
        out.append(Turn(actor=person.id, action="answer", label=_label(config, "answer", lang), blocked_by=[],
                        reason=e.title, since=e.date, entry=e.id))

    # 4. by stage
    stage = config.stage(case.stage)
    if stage and stage.interview:
        # a conversation: every respondent who is not done has a move of their own, beside the stage's own actions
        from .interview import progress
        for pid, p in progress(config, case).items():
            if not p["done"]:
                out.append(Turn(actor=pid, action="interview", label=_label(config, "interview" if p["answered"] == 0 else "interview_continue", lang),
                                reason=config.word("stages", case.stage, lang, case.stage), blocked_by=[], since=case.since))
    stage_turn = stage_actor(stage, case)
    if stage and stage_turn and stage_turn != "claude":
        for action in stage.actions:
            if not offered(config, case, action):
                continue
            missing = missing_for(config, case, action)
            actor = actor_of(action.actor, case) or stage_turn
            if action.actor and actor != stage_turn and missing:
                # the stage's own actor must deliver first; the action's actor waits
                out.append(Turn(actor=stage_turn, action="deliver", label=_label(config, "deliver", lang),
                                reason=config.word("reasons", "missing", lang, "something is still missing"),
                                blocked_by=missing, since=case.since))
                continue
            blocked = list(missing)
            fe = four_eyes_block(config, case, action, actor)
            if fe:
                blocked.append(fe)
            out.append(Turn(actor=actor, action=action.id, label=_rule_label(config, case, lang) if action.compile == "handoff" else _label(config, action.label, lang), payload=list(action.payload), seal=action.seal,
                            reason=config.word("stages", case.stage, lang, case.stage), blocked_by=blocked, since=case.since))
        _producers_first(config, stage, out)
        _next_after_create(config, case, out)
    elif stage and stage.turn == "claude":
        out.append(Turn(actor="claude", action="wait", label=_label(config, "wait", lang), blocked_by=[],
                        reason=config.word("stages", case.stage, lang, case.stage), since=case.since))

    return out


def _producers_first(config: DomainConfig, stage, out: list[Turn]) -> None:
    """A move that waits for something another offered action delivers (`produces`) is not the first thing to do: the
    producing action is. It moves before the waiting one and says which move it opens — for every application alike.
    `produces` names files; a missing `criteria` check waits for the file the criteria are read from."""
    from .edit import criteria_file
    by_id = {a.id: a for a in stage.actions}
    cfile = criteria_file(config)
    for t in list(out):
        if not t.blocked_by:
            continue
        waits = {cfile if b == "criteria" or b.startswith("criteria:") else b for b in t.blocked_by}
        for p in out:
            act = by_id.get(p.action)
            if p is t or p.actor != t.actor or p.blocked_by or not act or not set(act.produces) & waits:
                continue
            p.unblocks = t.action
            i, j = out.index(t), out.index(p)
            if j > i:
                out.insert(i, out.pop(j))
            break


def _next_after_create(config: DomainConfig, case: Case, out: list[Turn]) -> None:
    """A case just started offers the action its application names first (`theme.create.next`, REQ-002 SW-15): while it
    stands in the stage it started in, no helper has worked on it, and nothing the action produces is there yet (a task
    written by hand makes confirming first again). Without the key nothing changes."""
    create = config.theme.get("create") or {}
    nxt = create.get("next")
    start = create.get("stage") or next((s.folder for s in config.stages if s.group != "archive"), None)
    stage = config.stage(case.stage)
    action = next((a for a in stage.actions if a.id == nxt), None) if stage else None
    if not action or case.runs or case.stage != start or any((s := case.slot(f)) and s.present for f in action.produces):
        return
    i = next((k for k, t in enumerate(out) if t.action == nxt), None)
    if i:
        out.insert(0, out.pop(i))


def stage_run(case: Case):
    """The last foreground run that worked on this case in the stage it stands in now, or None."""
    fg = [r for r in case.runs if not r.background and (r.container or "").split("/")[0] == case.stage]
    return fg[-1] if fg else None


ORDER = ("date", "seal", "gate", "gap", "nudge")       # the stack's rule (Chris, 2026-10-29): a date first, then gates with a seal, gates without,
                                                        # moves that wait for something, then nudges; inside a group the longest-waiting first
DATE_KEYS = ("due", "publishDate", "deadline")          # a meta key that puts a case on a date


def _lookup(config: DomainConfig, kind: str, key: str, lang: str | None) -> str | None:
    """A word from the vocabulary, or None — unlike `config.word`, which falls back to the key."""
    v = config.vocabulary.get(lang or config.lang) or config.vocabulary.get("en") or {}
    section = v.get(kind)
    return section.get(key) if isinstance(section, dict) and section.get(key) else None


# Words for the tokens the core itself defines; an application's vocabulary (`requires`) overrides them.
CORE_REQUIRES = {
    "de": {"criteria": "Akzeptanzkriterien"},
    "en": {"criteria": "acceptance criteria"},
}


def missing_words(config: DomainConfig, tokens: list[str], lang: str | None) -> list[str]:
    """The words for what is missing: a file name through `files`, a token (`shape:image`, `answered`, `decided:…`) through `requires`."""
    out = []
    for t in tokens:
        if t.startswith("four eyes:"):
            continue
        key = t.split(":")[0] + ":" if ":" in t and not t.endswith(".json") else t
        if t.startswith("decided:"):
            key = "decided:"
        # the whole token first ("shape:image" is its own word), then the family ("decided:"), then the file's word
        core = CORE_REQUIRES.get(lang or config.lang) or CORE_REQUIRES["en"]
        out.append(_lookup(config, "requires", t, lang) or _lookup(config, "requires", key, lang) or core.get(t)
                   or config.word("files", t, lang, t))
    return out


def classify(case: Case, action: Action | None, t: Turn) -> str:
    """Which group of the stack a move belongs to. A move that waits for something is a gap whatever its gate would be."""
    if t.action == "wait":
        return "nudge"
    if any(not b.startswith("four eyes:") for b in t.blocked_by):
        return "gap"
    if t.seal:
        return "seal"
    if t.action in ("answer", "retry", "see_failure", "interview"):
        return "gate"
    if action is not None and action.to:
        return "gate"
    return "nudge"



def _rule_label(config: DomainConfig, case: Case, lang: str | None) -> str:
    """A mail's confirm says what it will do: the action word of the rule of the matrix the AI's reading picked
    ("Open a claim file", "File away"), in the reader's language; the plain confirm when there is no reading yet."""
    import json as _json
    picked = (case.data.get("einordnung.json") or {}).get("rule") if isinstance(case.data.get("einordnung.json"), dict) else None
    try:
        rules = _json.loads((config.dir / "regeln.json").read_text(encoding="utf-8")).get("rules", []) if picked and config.dir else []
    except (OSError, ValueError):
        rules = []
    rule = next((r for r in rules if r.get("id") == picked), None)
    word = (rule or {}).get("action_word")
    if isinstance(word, dict):
        return str(word.get(lang or "") or word.get("en") or next(iter(word.values()), "")) or _label(config, "confirm", lang)
    return str(word) if word else _label(config, "confirm", lang)


def sentence(config: DomainConfig, case: Case, t: Turn, lang: str | None) -> tuple[str, str]:
    """(headline, lock) from the vocabulary's templates, with {title}, {label}, {missing}, {first}, {n} filled; defaults when none is configured."""
    over = ((case.meta.get("i18n") or {}).get(lang or "") or {}) if isinstance(case.meta.get("i18n"), dict) else {}
    title = str(over.get("title") or case.meta.get("title") or case.meta.get("working_title") or case.id)   # in the reader's language (request 8)
    words = missing_words(config, t.blocked_by, lang)
    ctx = {"title": title, "label": t.label, "missing": ", ".join(words), "first": words[0] if words else "", "n": str(len(words))}

    def fill(s: str) -> str:
        for k, v in ctx.items():
            s = s.replace("{" + k + "}", v)
        return s.strip()

    head = _lookup(config, "headlines", t.action, lang) or ""
    if head and not words and ("{missing}" in head or "{first}" in head):   # a template about a gap, but nothing is missing: the plain form
        head = ""
    headline = fill(head) if head else (fill(config.word("texts", "headline_default", lang, "{label}: {title}")))
    lock = ""
    if words:
        lk = _lookup(config, "locks", t.action, lang) or config.word("texts", "lock_default", lang, "{label} — {missing}")
        lock = fill(lk)
    return headline, lock


def enrich(case: Case, turns: list[Turn], config: DomainConfig, lang: str | None = None) -> list[Turn]:
    """Kind, headline, lock and date on every move of a case — the stack's vocabulary, computed once from the configuration."""
    stage = config.stage(case.stage)
    actions = {a.id: a for a in (stage.actions if stage else [])}
    date = next((str(case.meta[k])[:10] for k in DATE_KEYS if case.meta.get(k)), "")
    for t in turns:
        t.kind = classify(case, actions.get(t.action), t)
        if date and t.kind in ("seal", "gate", "gap"):
            t.kind, t.date = "date", date
        t.headline, t.lock = sentence(config, case, t, lang)
        t.missing = missing_words(config, t.blocked_by, lang)
    return turns


def rank(config: DomainConfig, case: Case, t: Turn) -> tuple:
    order = list(config.order or ORDER)
    pos = order.index(t.kind) if t.kind in order else len(order)
    return (pos, t.date or "", t.since or "", case.id)


def turns_for(person_id: str, cases: list[Case], config: DomainConfig, lang: str | None = None) -> list[tuple[Case, Turn]]:
    """Every (case, turn) where this person is the actor — the stack. Ordered by the stack's rule (`order` in stages.json, else ORDER),
    inside a group by date, then the longest-waiting first."""
    out: list[tuple[Case, Turn]] = []
    for c in cases:
        for t in enrich(c, turn(c, config, lang), config, lang):
            if t.actor == person_id or config.may_act(person_id, t.actor):
                out.append((c, t))
    out.sort(key=lambda ct: rank(config, ct[0], ct[1]))
    return out
