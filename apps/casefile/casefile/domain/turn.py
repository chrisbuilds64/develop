"""Whose move is it. One pure function; surface, CLI and agents all call this one.

The rule, in order (Bauplan §4, from the operating concept §7):
1. a run is running → Claude's move, nobody else's;
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


def turn(case: Case, config: DomainConfig, lang: str | None = None) -> list[Turn]:
    out: list[Turn] = []
    run = case.last_run

    # 1. a helper is at work
    if run and run.status in ("running", "queued"):
        agent = config.agent
        return [Turn(actor="claude", action="wait", label=_label(config, "wait", lang), blocked_by=[],
                     reason=config.word("reasons", "running", lang, "a helper is working on it"), since=run.started or run.created)]

    # 2. the last run failed
    if run and run.status == "failed":
        out.append(Turn(actor=OPERATOR, action="see_failure", label=_label(config, "see_failure", lang), blocked_by=[],
                        reason=config.word("reasons", "failed", lang, "the last run failed"), since=run.finished or run.created))

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
    if stage and stage.turn and stage.turn != "claude":
        for action in stage.actions:
            missing = missing_for(config, case, action)
            actor = action.actor or stage.turn
            if action.actor and action.actor != stage.turn and missing:
                # the stage's own actor must deliver first; the action's actor waits
                out.append(Turn(actor=stage.turn, action="deliver", label=_label(config, "deliver", lang),
                                reason=config.word("reasons", "missing", lang, "something is still missing"),
                                blocked_by=missing, since=case.since))
                continue
            blocked = list(missing)
            fe = four_eyes_block(config, case, action, actor)
            if fe:
                blocked.append(fe)
            out.append(Turn(actor=actor, action=action.id, label=_label(config, action.label, lang), payload=list(action.payload), seal=action.seal,
                            reason=config.word("stages", case.stage, lang, case.stage), blocked_by=blocked, since=case.since))
    elif stage and stage.turn == "claude":
        out.append(Turn(actor="claude", action="wait", label=_label(config, "wait", lang), blocked_by=[],
                        reason=config.word("stages", case.stage, lang, case.stage), since=case.since))
    return out


def turns_for(person_id: str, cases: list[Case], config: DomainConfig, lang: str | None = None) -> list[tuple[Case, Turn]]:
    """Every (case, turn) where this person is the actor — the 'your move' list. Main turns first."""
    out: list[tuple[Case, Turn]] = []
    for c in cases:
        for t in turn(c, config, lang):
            if t.actor == person_id or config.may_act(person_id, t.actor):
                out.append((c, t))
    out.sort(key=lambda ct: (ct[1].since or "", ct[0].id))
    return out
