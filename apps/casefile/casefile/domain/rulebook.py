"""The rulebook, edited in the app (design request 9, ADR-026): rules and text modules in `_bausteine/`, as versions.

    _bausteine/<id>-<slug>.md            the version in force: what compose, the AI and every reader take
    _bausteine/_fassungen/<id>.v<n>.md   every version there ever was, the one in force among them; a draft is the newest

A change is a draft first (an operator writes it). It comes into force when a second person approves it: an operator
or an approver who is not the one who wrote the draft. Retiring a module is a version too (status `zurückgezogen`),
so compose refuses it and the history says who and why. Nothing is deleted.

A case keeps the rulebook it started with: `in_force_at(case start)` gives, per module, the newest approved version
whose approval date is not after the case's `created`. A module may name the areas it applies to (`areas: HR, KFZ`,
the case's labels); outside them it is not offered.
"""

from __future__ import annotations

import datetime as dt
import re

from ..config import DomainConfig
from ..store import FsStore

FOLDER = "_bausteine"
HISTORY = f"{FOLDER}/_fassungen"
ID = re.compile(r"^[A-Z]{1,3}-\d{2,3}$")
APPROVED, DRAFT, RETIRED, REJECTED = "freigegeben", "entwurf", "zurückgezogen", "verworfen"
HEAD_ORDER = ("id", "kind", "title", "version", "status", "areas", "approved_by", "date", "in_force_since", "drafted_by",
              "drafted_by_id", "note", "source", "reason")


class RulebookError(Exception):
    """A sentence for the person."""


def _parse(text: str) -> dict | None:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None
    head = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            head[k.strip()] = v.strip()
    if not head.get("id"):
        return None
    # the body in other languages, after a line `<!-- en -->`: kept apart as `body_en`, so compose and every letter only
    # ever take the original; the surface shows a reader the version in their language (request 8)
    parts = re.split(r"\n?<!--\s*([a-z]{2})\s*-->\n?", m.group(2))
    langs = {f"body_{k}": v.strip() for k, v in zip(parts[1::2], parts[2::2]) if v.strip()}
    return {**head, **langs, "body": parts[0].strip()}


def _render(mod: dict) -> str:
    keys = [k for k in HEAD_ORDER if mod.get(k) not in (None, "")] + [k for k in mod if k not in HEAD_ORDER and k != "body" and not k.startswith(("_", "body_")) and mod.get(k) not in (None, "")]
    other = "".join(f"\n<!-- {k[5:]} -->\n{str(v).strip()}" for k, v in mod.items() if k.startswith("body_") and v)
    return "---\n" + "\n".join(f"{k}: {mod[k]}" for k in keys) + "\n---\n" + str(mod.get("body", "")).strip() + other + "\n"


def areas_of(mod: dict) -> list[str]:
    return [a.strip() for a in str(mod.get("areas") or "").split(",") if a.strip()]


def applies(mod: dict, label: str | None) -> bool:
    a = areas_of(mod)
    return not a or not label or label in a


def current(store: FsStore) -> dict[str, dict]:
    """id → the version in force, with `_file` (its name in `_bausteine/`)."""
    out = {}
    d = store.root / FOLDER
    for p in sorted(d.glob("*.md")) if d.is_dir() else []:
        mod = _parse(p.read_text(encoding="utf-8"))
        if mod:
            out[mod["id"]] = {**mod, "_file": p.name}
    return out


def _check_id(module_id: str) -> None:
    """Every entry point takes the id into a file name or pattern, so every one checks it (review S5)."""
    if not ID.match(module_id or ""):
        raise RulebookError(f"'{module_id}' is not a module id (like R-08 or B-19)")


def _moment(value) -> str:
    """A date or a time, comparable as text: `2026-11-08`, `2026-11-08 14:00:05`. A bare date is the start of its day."""
    return str(value or "").replace("T", " ")[:19]


def _since(mod: dict) -> str:
    """When a version came into force: to the second where the app recorded it, else its day (review S3)."""
    return _moment(mod.get("in_force_since") or mod.get("date"))


def history(store: FsStore, module_id: str) -> list[dict]:
    """Every version of one module, oldest first. A module never edited in the app has its version in force as its history."""
    if not ID.match(module_id or ""):
        return []
    d = store.root / HISTORY
    found = {}
    for p in d.glob(f"{module_id}.v*.md") if d.is_dir() else []:
        mod = _parse(p.read_text(encoding="utf-8"))
        if mod:
            found[int(mod.get("version") or 0)] = mod
    now = current(store).get(module_id)
    if now and int(now.get("version") or 0) not in found:
        found[int(now.get("version") or 0)] = {k: v for k, v in now.items() if not k.startswith("_")}
    return [found[v] for v in sorted(found)]


def draft_of(store: FsStore, module_id: str) -> dict | None:
    h = history(store, module_id)
    return h[-1] if h and h[-1].get("status") == DRAFT else None


def proposed(store: FsStore) -> dict[str, dict]:
    """id → the open draft of a module that is not in force yet: a new rule proposed (by the AI or a person) and waiting."""
    d = store.root / HISTORY
    ids = {p.name.split(".v")[0] for p in d.glob("*.v*.md")} if d.is_dir() else set()
    now = current(store)
    out = {}
    for mid in sorted(ids - set(now)):
        dr = draft_of(store, mid)
        if dr:
            out[mid] = dr
    return out


def _next_version(store: FsStore, module_id: str) -> int:
    h = history(store, module_id)
    return max([int(m.get("version") or 0) for m in h] + [0]) + 1


def _today() -> str:
    return dt.date.today().isoformat()


def _now() -> str:
    return dt.datetime.now().isoformat(sep=" ", timespec="seconds")


def _slug(title: str) -> str:
    s = title.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "baustein"


def _may(config: DomainConfig, person_id: str, roles: tuple[str, ...]) -> bool:
    p = config.person(person_id)
    return bool(p and p.kind == "human" and set(p.roles) & set(roles))


def save_draft(store: FsStore, config: DomainConfig, module_id: str, by: str, text: str, title: str = "", kind: str = "",
               areas: list[str] | None = None, note: str = "") -> dict:
    """A new version as a draft, or the open draft rewritten. A new id starts a new module (kind and title needed)."""
    if not _may(config, by, ("operator",)):
        raise RulebookError("only the people who run this place change the rulebook")
    if not ID.match(module_id or ""):
        raise RulebookError(f"'{module_id}' is not a module id (like R-08 or B-19)")
    if not text.strip():
        raise RulebookError("the text is empty")
    with store.lock(f"_rulebook-{module_id}"):
        now = current(store).get(module_id)
        open_ = draft_of(store, module_id)
        base = open_ or now
        if base is None and not (title.strip() and kind.strip()):
            raise RulebookError("a new module needs a kind and a title")
        version = int(open_["version"]) if open_ else _next_version(store, module_id)      # after a rejected draft too
        mod = {"id": module_id, "kind": kind.strip() or base.get("kind", ""), "title": title.strip() or base.get("title", ""),
               "version": version, "status": DRAFT, "areas": ", ".join(areas) if areas is not None else (base or {}).get("areas", ""),
               "drafted_by": config.person(by).name, "drafted_by_id": by, "date": _today(), "note": note.strip(), "source": (open_ or now or {}).get("source", ""), "body": text.strip()}
        store.write_atomic(f"{HISTORY}/{module_id}.v{version}.md", _render(mod))
        if now and not store.exists(f"{HISTORY}/{module_id}.v{now['version']}.md"):     # the version in force joins the history once
            store.write_atomic(f"{HISTORY}/{module_id}.v{now['version']}.md", _render({k: v for k, v in now.items() if not k.startswith("_")}))
    return mod


def approve(store: FsStore, config: DomainConfig, module_id: str, by: str) -> dict:
    """The open draft comes into force. Four eyes: not by the person who wrote it."""
    if not _may(config, by, ("operator", "approver")):
        raise RulebookError("an operator or an approver brings a change into force")
    _check_id(module_id)
    with store.lock(f"_rulebook-{module_id}"):
        d = draft_of(store, module_id)
        if d is None:
            raise RulebookError(f"{module_id} has no open draft")
        me = config.person(by)
        wrote = d.get("drafted_by_id") == me.id if d.get("drafted_by_id") else d.get("drafted_by") == me.name   # by id (review S6)
        if wrote:
            raise RulebookError(f"four eyes: {me.name} wrote this draft; somebody else brings it into force")
        mod = {**d, "status": APPROVED, "approved_by": me.name, "date": _today(), "in_force_since": _now()}
        _put_in_force(store, module_id, mod)
    return mod


def retire(store: FsStore, config: DomainConfig, module_id: str, by: str, note: str) -> dict:
    """The module goes out of force as a version of its own, with the reason. Cases that started before keep theirs."""
    if not _may(config, by, ("operator",)):
        raise RulebookError("only the people who run this place change the rulebook")
    if not note.strip():
        raise RulebookError("retiring needs its reason")
    _check_id(module_id)
    with store.lock(f"_rulebook-{module_id}"):
        now = current(store).get(module_id)
        if now is None:
            raise RulebookError(f"{module_id} is not in the rulebook")
        if now.get("status") == RETIRED:
            raise RulebookError(f"{module_id} is retired already")
        if draft_of(store, module_id):
            raise RulebookError(f"{module_id} has an open draft; bring it into force or write over it first")
        if not store.exists(f"{HISTORY}/{module_id}.v{now['version']}.md"):
            store.write_atomic(f"{HISTORY}/{module_id}.v{now['version']}.md", _render({k: v for k, v in now.items() if not k.startswith("_")}))
        mod = {k: v for k, v in now.items() if not k.startswith("_")}
        mod.update(version=_next_version(store, module_id), status=RETIRED, approved_by=config.person(by).name, date=_today(), in_force_since=_now(), note=note.strip())
        _put_in_force(store, module_id, mod)
    return mod


def reject(store: FsStore, config: DomainConfig, module_id: str, by: str, reason: str) -> dict:
    """The open draft is not taken: it stays in the history as `verworfen`, with who and why. The version in force stays."""
    if not _may(config, by, ("operator", "approver")):
        raise RulebookError("an operator or an approver decides on a proposed change")
    if not reason.strip():
        raise RulebookError("rejecting needs its reason")
    _check_id(module_id)
    with store.lock(f"_rulebook-{module_id}"):
        d = draft_of(store, module_id)
        if d is None:
            raise RulebookError(f"{module_id} has no open draft")
        mod = {**d, "status": REJECTED, "approved_by": config.person(by).name, "date": _today(), "reason": reason.strip()}
        store.write_atomic(f"{HISTORY}/{module_id}.v{mod['version']}.md", _render(mod))
    return mod


def _put_in_force(store: FsStore, module_id: str, mod: dict) -> None:
    store.write_atomic(f"{HISTORY}/{module_id}.v{mod['version']}.md", _render(mod))
    old = current(store).get(module_id)
    name = old["_file"] if old else f"{module_id}-{_slug(mod.get('title', ''))}.md"
    store.write_atomic(f"{FOLDER}/{name}", _render(mod))


def in_force_at(store: FsStore, when: str | None, label: str | None = None) -> dict[str, dict]:
    """The rulebook as it stood on `when` (a case's `created`, ISO date or time): per module the newest approved or
    retired version dated on or before that day; a module that did not exist then is absent. Without `when`, today's.
    Modules outside the case's areas are marked `_skip`, so compose passes over them."""
    out = {}
    day = _moment(when)                                           # the case's start, to the second where it has one (review S3);
    if len(day) == 10:                                            # a bare date says nothing of the hour: the whole day counts, as before
        day += " 23:59:59"
    for mid, now in current(store).items():
        mod = now
        if day and _since(now) > day:
            recorded = (store.root / HISTORY).is_dir() and any((store.root / HISTORY).glob(f"{mid}.v*.md"))
            if recorded:                                          # edited in the app: the history knows what stood that day
                earlier = [v for v in history(store, mid) if v.get("status") in (APPROVED, RETIRED) and _since(v) <= day]
                if not earlier:
                    continue                                      # it came into force after the case started
                mod = earlier[-1]
        mod = {k: v for k, v in mod.items()}
        if not applies(mod, label):
            mod["_skip"] = True
        out[mid] = mod
    return out
