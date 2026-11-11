"""Opening a case: the one way a case comes into being, for the surface and for an agent alike (REQ-001 C-10).

The application says how one starts (`theme.create`: label, the roles that may, the first stage, the numbering, what the
meta carries). A person or an agent with one of those roles opens it with a title, an optional description in Markdown
and attached files; the case gets its number, its folder in the first stage, its meta and its first thread entry. The
same step id twice is the same case.
"""

from __future__ import annotations

import datetime as dt
import re

from ..config import DomainConfig
from ..store import FsStore, StoreError
from . import assets
from . import step as stepping


class NotHere(Exception):
    """The application starts no cases (no `theme.create`)."""


class Refused(Exception):
    """The request is understood but not allowed or not complete; the message is for the person."""


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def open_case(store: FsStore, config: DomainConfig, by: str, title: str, step_id: str, *, label: str | None = None,
              values: dict | None = None, description: str = "", attached: list[tuple[str, bytes]] | None = None,
              lang: str | None = None) -> tuple[str, str]:
    """(case id, first stage) of the new case — or of the one this step id already opened."""
    attached = list(attached or [])
    create = config.theme.get("create") or {}
    if not create:
        raise NotHere("new cases are not started here")
    for name, _ in attached:
        if assets.free_name(name).rpartition(".")[2] not in assets.FREE:
            raise Refused(f"'{name}' cannot be attached; a case takes {', '.join(assets.FREE)}")
    p = config.person(by)
    if not p or not (set(create.get("roles", [])) & set(p.roles)):
        raise Refused(config.word("texts", "create_refused", lang, "You may not start a case here."))
    title = (title or "").strip()[:120]
    if not title:
        raise Refused(config.word("texts", "create_empty", lang, "Give it a name."))
    from . import fields as declared
    from . import lists as chosen
    own, listed = declared.split(config, values or {})            # declared fields (domain/fields.py) and the lists that ask on creation
    try:
        vals = chosen.validate_choice(config.lists, listed)        # what the lists that ask for it gave: field → key
        vals.update({k: v for k, v in declared.validate(config, own).items() if v != ""})
    except (chosen.ListError, declared.FieldError) as exc:
        raise Refused(str(exc)) from exc
    label = vals.get("label") or label or create.get("label", "X")
    first = create.get("stage") or next((s.folder for s in config.stages if s.group != "archive"), None)   # where a new case starts
    if not first or first not in {s.folder for s in config.stages}:     # declared is enough: the folder comes with its first case
        raise Refused("the first stage is not declared")
    for prior in store.journals():                              # the same step id twice is the same case
        j = store.read_json(f"_steps/{prior}")
        if j.get("step_id") == step_id and j.get("action") == "create":
            return j["case"], store.find(j["case"]) or first
    from . import numbering
    number = numbering.next_number(getattr(store, "everything", store), label, create.get("number"), vals)   # over every data point; the domain's own rule
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))).strip("-")[:40] or "akte"
    cid = f"{label}-{number}-{slug}" if create.get("slug", True) else f"{label}-{number}"   # `slug: false`: the number alone is the name
    try:
        store.mkcase(first, cid)
    except StoreError as exc:
        raise Refused(str(exc)) from exc
    meta = {"configVersion": config.config_version, "label": label, "number": number, "title": title, "created": _now()[:10], "created_by": p.id,
            **{k: v for k, v in (create.get("meta") or {}).items()}, **vals}
    if create.get("external_id"):                               # the domain's outside reference, from the same number: SN-{year}-{seq:05}
        from . import handoff
        m = re.match(r"^(?:(\d{4})-)?\D*?(\d+)$", number)
        meta["external_id"] = handoff.fill(str(create["external_id"]), {**vals, "number": number, "year": (m.group(1) if m and m.group(1) else str(dt.date.today().year)), "seq": (m.group(2) if m else number)})
    store.write_json(f"{first}/{cid}/meta.json", meta)
    text = (description or "").strip()[:20000]
    names = []
    for original, data in attached:
        name = assets.put_free(store, config, cid, original, data)
        names.append(name)
        if name != original and [o for o, _ in attached].count(original) == 1:   # the description points at the name the case keeps
            text = text.replace(f"]({original})", f"]({name})")
    text = re.sub(r"^(## REV-\d)", r"\\\1", text, flags=re.M)    # a line the thread would read as an entry of its own
    store.write_json(f"_steps/{step_id}.json", {"step_id": step_id, "case": cid, "action": "create", "by": p.id, "status": "done", "created": _now(), "payload": {"title": title, "files": names}})
    stepping._append_entry(store, config, cid, first, {"author": p.name, "status": "info", "title": config.word("texts", "created", lang, "Started"),
                                                       "text": text or title, "step": step_id, **({"files": names} if names else {})})
    return cid, first
