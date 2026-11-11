"""A question's numbered choices as buttons (REQ-001 A-06).

A helper hands a decision back as an open entry with a numbered list. Each line is a choice. A choice that starts with
the words of a move the case offers the viewer right now makes that move; any other sends the same helper again with
the choice as its note; where no helper can be sent (a person asked, or none worked in this stage), the choice is the
answer. Every one of them resolves the question.

Matched by the words the buttons carry, in every language of the application — never by an id in the text, so the thread
stays readable for people. The same in every application: nothing here knows a stage, an action or a word.
"""

from __future__ import annotations

import re

from ..config import DomainConfig
from ..models import Case, Choice, Entry
from . import entries as thread

LINE = re.compile(r"^ {0,3}(\d{1,2})[.)]\s+(\S.*?)\s*$")
CUT = re.compile(r"\s+[—–-]\s+|:\s|;\s|\s\(")
MARKS = re.compile(r"[*_`]")
NOT_MOVES = ("answer", "retry", "wait", "interview", "deliver")


def parse(text: str) -> list[str]:
    """The numbered lines of the text, in order. One line alone is no choice."""
    out = [m.group(2) for m in (LINE.match(line) for line in (text or "").splitlines()) if m]
    return out if len(out) >= 2 else []


def head(choice: str) -> str:
    """What the button says: the choice up to its first explanation, without Markdown marks."""
    return MARKS.sub("", CUT.split(choice, maxsplit=1)[0]).strip().rstrip(".").strip()


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", MARKS.sub("", s).casefold()).split())


def _phrases(config: DomainConfig, label: str) -> list[str]:
    """A move's words in every language, and the parts of each ("Checks red, back to the build" → both halves)."""
    words = {config.word("actions", label, lang, "") for lang, v in config.vocabulary.items() if isinstance(v, dict)} | {label}
    out = set()
    for w in words:
        for part in re.split(r"[,;()]|\s[—–-]\s", w or ""):
            n = _norm(part)
            if len(n) >= 3:
                out.add(n)
    return sorted(out, key=len, reverse=True)


def _moves(config: DomainConfig, case: Case, viewer: str | None) -> list[tuple[str, list[str]]]:
    """The configured moves the viewer can make on the case right now: not blocked, asking for nothing but a note."""
    from .turn import turn
    if not viewer:
        return []
    out = []
    for t in turn(case, config):
        action = config.action(case.stage, t.action)
        if (t.action in NOT_MOVES or action is None or action.compile or t.blocked_by or set(action.payload) - {"note"}
                or not (t.actor == viewer or config.may_act(viewer, t.actor))):
            continue
        out.append((t.action, _phrases(config, action.label)))
    return out


def _again(config: DomainConfig, case: Case, entry: Entry, viewer: str | None) -> str:
    """The skill a choice sends again: the helper that finished in this stage and wrote the question, if the viewer may order it."""
    from .outside import standing
    from .runs import may_order
    from .turn import stage_run
    last = stage_run(case)
    author = config.person(entry.author)
    person = config.person(viewer) if viewer else None
    busy = (case.last_run is not None and case.last_run.status in ("queued", "running")) or standing(case) is not None
    if last is None or last.status != "done" or busy or person is None or author is None or author.kind != "agent":
        return ""
    return "" if may_order(config, last.skill, person) else last.skill


def options(config: DomainConfig, case: Case, entry: Entry, viewer: str | None) -> list[Choice]:
    items = parse(entry.text)
    if not items:
        return []
    moves = _moves(config, case, viewer)
    skill = _again(config, case, entry, viewer)
    out = []
    for n, text in enumerate(items, 1):
        label = head(text)
        said = f" {_norm(label)} "
        hits = [(len(p), action) for action, phrases in moves for p in phrases if f" {p} " in said]
        if hits:
            out.append(Choice(n=n, label=label, text=text, kind="move", action=max(hits)[1]))
        else:
            out.append(Choice(n=n, label=label, text=text, kind="again" if skill else "answer", skill=skill))
    return out


def for_case(config: DomainConfig, case: Case, viewer: str | None) -> dict[str, list[Choice]]:
    """The choices of every open question on the case, by entry id; questions without choices are left out."""
    out = {}
    for e in thread.open_for(case.entries, None):
        opts = options(config, case, e, viewer)
        if opts:
            out[e.id] = opts
    return out


def pick(config: DomainConfig, case: Case, viewer: str, payload: dict) -> tuple[str, dict] | str:
    """The step a choice stands for — (action, payload) — or why there is none."""
    rid = str(payload.get("resolves", "")).strip().upper()
    entry = next((e for e in case.entries if e.id == rid), None)
    if entry is None:
        return f"'{rid}' is not an entry of this case"
    if entry not in thread.open_for(case.entries, None):
        return "this question is answered already"
    try:
        n = int(payload.get("choice"))
    except (TypeError, ValueError):
        return "no choice given"
    chosen = next((o for o in options(config, case, entry, viewer) if o.n == n), None)
    if chosen is None:
        return f"the question has no choice {n}"
    keep = {k: v for k, v in payload.items() if k.startswith("_")}
    if chosen.kind == "move":
        return chosen.action, {**keep, "note": chosen.text, "resolves": rid}
    if chosen.kind == "again":
        return "order_again", {**keep, "note": chosen.text, "resolves": rid}
    return "answer", {**keep, "text": chosen.text, "resolves": rid}
