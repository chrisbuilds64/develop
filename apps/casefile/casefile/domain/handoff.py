"""A hand-off: a case in one application starts or feeds a case in another. One mechanism for every application.

Two kinds, both described by a spec, never by code:

    create   a new case opens in the target   — a claim orders an assessment, a mail becomes a claim or a signal
    deliver  files reach a case that waits    — the e-report returns to its claim, a question lands on its file

    {"target": "egutachten",                  key in the workspace's targets.json (the stage decides where it points); "self" = this workspace
     "mode": "create",                        create | deliver
     "label": "KH", "stage": "10-auftrag",    create: the new case's label and stage (default: the target's, its first stage)
     "number": "source",                      create: keep the source's number; default: the next free one of the label
     "slug": "source",                        create: the id's tail from the source id; default: from the title
     "external_id": "GA-{year}-{seq:05}",     create: the new case's reference
     "link": "gutachten_auftrag",             create: the source remembers the reference under this key
     "meta": {"title": "{source.title}"},     create: the new case's meta, filled from the context
     "files": {"meldung.md": "auftrag.md", "fotos-*.jpg": ""},   newest version of each; "" keeps the name, {n} counts
     "match": {"key": "gutachten_auftrag", "value": "{source.external_id}"},   deliver: which case waits
     "action": "deliver_report",              deliver: the step the waiting case takes
     "by": "innendienst",                     the person the target's entry or step is written for
     "entry": {"title": "…", "text": "…"},    what the target's thread says; templates
     "run": "<skill of the target>"}          create: the target's helper starts at once

Templates read `{source.<meta key>}`, `{fields.<key>}` and `{summary}` (a helper's reading, `einordnung.json`), `{number}`,
`{year}`, `{seq}` and `{ref}`; a format after a colon (`{seq:05}`). Targets are named in `targets.json` at the root (root,
config, url, label, stage) — written by whoever set the workspace up, so the engine never guesses another application's folder.

The rule matrix (`regeln.json`, the pipeline root's copy wins over the domain's) is one way to choose a spec: per kind of case a
row; the helper's reading picks the row, a person confirms, `execute` does it and records `aktion.json`. An action's own
`handover` is the other: the step lands, then the spec is carried out.
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import DomainConfig
from ..store import FsStore, StoreError
from . import cases as reading

IMAGES = (".jpg", ".jpeg", ".png", ".webp")
NEVER = ("meta.json", "review.md", "mail.eml", "einordnung.json", "aktion.json")   # the case's own records never travel


class HandoffError(Exception):
    """A sentence for the person."""


@dataclass
class Target:
    key: str
    store: FsStore
    config: DomainConfig
    label: str = ""
    url: str = ""
    stage: str = ""
    external_prefix: str = ""


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def matrix_doc(store: FsStore, config: DomainConfig) -> dict:
    """The whole rule matrix document (rules, privacy); the pipeline root's copy wins over the domain's."""
    for p in (store.root / "regeln.json", (config.dir / "regeln.json") if config.dir else None):
        if p and p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                return {}
    return {}


def matrix(store: FsStore, config: DomainConfig) -> list[dict]:
    return [r for r in matrix_doc(store, config).get("rules", []) if isinstance(r, dict) and r.get("id")]


def targets(store: FsStore) -> dict:
    p = store.root / "targets.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        return {}


def target(store: FsStore, key: str) -> Target:
    """The connected application under `key`, or a refusal that says it is not connected."""
    t = targets(store).get(key)
    if not t:
        raise HandoffError(f"target '{key}' is not connected in this workspace")
    root = Path(t["root"])
    return Target(key=key, store=FsStore(root), config=DomainConfig.load(Path(t["config"]), root), label=str(t.get("label", key)),
                  url=str(t.get("url", "")), stage=str(t.get("stage", "")), external_prefix=str(t.get("external_prefix", "")))


def connected(store: FsStore, rule: dict) -> bool:
    return rule.get("action") == "file_away" or (rule.get("action") in ("create_case", "note_to_case", "deliver") and rule.get("target", "") in targets(store))


def fill(template: str, ctx: dict) -> str:
    def one(m):
        cur = ctx
        for part in m.group(1).split("."):
            cur = cur.get(part, "") if isinstance(cur, dict) else ""
        if m.group(2) and cur != "":
            try:
                return format(int(cur) if str(cur).isdigit() else cur, m.group(2))
            except (ValueError, TypeError):
                return str(cur)
        return str(cur if cur is not None else "")
    return re.sub(r"\{([a-z_.]+)(?::([^}]+))?\}", one, template).strip()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))).strip("-")[:40]


def _files(store: FsStore, case_id: str, wanted: dict) -> list[tuple[str, Path]]:
    """(name in the target, source path): the newest version of each file the spec names, in a stable order."""
    src = store.case_dir(case_id)
    newest: dict[str, tuple[Path, int]] = {}
    for f in store.files(case_id):
        if f in NEVER:
            continue
        base, v = reading.split_version(f)
        if base not in newest or v > newest[base][1]:
            newest[base] = (src / f, v)
    out, n = [], 0
    for pattern, rename in wanted.items():
        for base in sorted(newest):
            if not (base.lower().endswith(IMAGES) if pattern == "images" else fnmatch.fnmatch(base, pattern)):
                continue
            n += 1
            name = rename.replace("{n}", str(n)) if rename else base
            if name not in (x for x, _ in out):
                out.append((name, newest[base][0]))
    return out


def _context(store: FsStore, config: DomainConfig, case_id: str) -> dict:
    case = reading.load(store, config, case_id)
    reading_ = case.data.get("einordnung.json") or {}
    return {"source": {"id": case_id, **case.meta}, "fields": reading_.get("fields") or {}, "summary": reading_.get("summary", ""),
            "mail": case.meta, "sender": case.meta.get("from_name") or case.meta.get("from", ""), "_case": case}


def _entry(tgt: Target, tid: str, stage: str, spec: dict, ctx: dict, files: list[str], fallback_title: str, author: str) -> None:
    from . import step as stepping
    person = tgt.config.person(str(spec.get("by", ""))) if spec.get("by") else None
    e = spec.get("entry") or {}
    stepping._append_entry(tgt.store, tgt.config, tid, stage, {"author": person.name if person else author, "status": "info",
                           "title": fill(str(e.get("title", "")), ctx)[:120] or fallback_title,
                           "text": fill(str(e.get("text", "")), ctx), "files": files})


def create(store: FsStore, config: DomainConfig, case_id: str, tgt: Target, spec: dict, by: str, request_id: str = "", ctx: dict | None = None) -> dict:
    """A new case in the target. Idempotent: a case that is already there is the answer, nothing is written twice."""
    ctx = ctx or _context(store, config, case_id)
    case = ctx.pop("_case", None) or reading.load(store, config, case_id)
    born = tgt.config.theme.get("create") or {}              # how a case starts in the target, when the spec does not say: same rule as the form
    stage = spec.get("stage") or tgt.stage or born.get("stage") or next((s.folder for s in tgt.config.stages if s.group != "archive"), None)
    if not stage or stage not in tgt.store.stages():
        raise HandoffError(f"the stage '{stage}' is missing in {tgt.label}")
    label = spec.get("label") or born.get("label") or "X"
    year = dt.date.today().year
    if spec.get("number") == "source" and case.meta.get("number"):
        number = str(case.meta["number"])
    else:
        from . import numbering
        rule = spec.get("number") if spec.get("number") not in (None, "", "source") else born.get("number") or ["{year}-{seq:04}"]
        number = numbering.next_number(tgt.store, label, rule, {k: v for k, v in (spec.get("values") or {}).items()})
    y, _, seq = number.partition("-")
    ctx.update(number=number, year=y or str(year), seq=seq or number)
    meta_t = dict(spec.get("meta") or {})
    title = fill(meta_t.pop("title", "{source.title}"), ctx) or str(case.meta.get("title") or case_id)
    tail = "-".join(case_id.split("-")[3:]) if spec.get("slug") == "source" else _slug(title)
    tid = f"{label}-{number}-{tail or 'akte'}"
    prefix = tgt.external_prefix
    ref = fill(spec["external_id"], ctx) if spec.get("external_id") else (f"{prefix}{y}-0{seq}" if prefix else "")
    ctx["ref"] = ref
    files = _files(store, case_id, spec.get("files") or {})
    result = {"mode": "create", "target": tgt.key, "target_label": tgt.label, "case": tid, "title": title, "ref": ref,
              "url": tgt.url.rstrip("/") + f"/case/{tid}" if tgt.url else ""}
    if tgt.store.find(tid):
        return {**result, "note": "already there"}
    tgt.store.mkcase(stage, tid)
    meta = {"configVersion": tgt.config.config_version, "label": label, "number": number, "title": title, "created": _now()[:10],
            **{k: fill(v, ctx) if isinstance(v, str) else v for k, v in meta_t.items()},
            "origin": {"application": config.name, "case": case_id, **({"message_id": case.meta["message_id"]} if case.meta.get("message_id") else {})}}
    if ref:
        meta["external_id"] = ref
    if case.meta.get("fictional"):
        meta["fictional"] = True                    # an invented case begets an invented case
    tgt.store.write_json(f"{stage}/{tid}/meta.json", {k: v for k, v in meta.items() if v != ""})
    for name, path in files:
        tgt.store.put_bytes(tid, name, path.read_bytes())
    if spec.get("link") and ref:                    # the source remembers what it started
        src_stage = store.find(case_id)
        store.write_json(f"{src_stage}/{case_id}/meta.json", {**case.meta, str(spec["link"]): ref})
    _entry(tgt, tid, stage, spec, ctx, [n for n, _ in files], title, config.name)
    if spec.get("run"):                             # the target's first helper starts at once
        from . import runs as ordering
        result["run"] = ordering.order(tgt.store, tgt.config, tid, stage, spec["run"], by, request_id=f"handoff-{request_id or case_id}")
    return result


def deliver(store: FsStore, config: DomainConfig, case_id: str, tgt: Target, spec: dict, by: str, request_id: str = "", ctx: dict | None = None) -> dict:
    """Files reach the case in the target that waits for them; that case takes its step."""
    from ..models import StepRequest
    from . import assets
    from . import step as stepping
    ctx = ctx or _context(store, config, case_id)
    ctx.pop("_case", None)
    m = spec.get("match") or {}
    key, value = str(m.get("key", "external_id")), fill(str(m.get("value", "{source.external_id}")), ctx)
    if not value:
        raise HandoffError(f"nothing to match: the value for '{key}' is empty")
    partner = next((k for k in reading.load_all(tgt.store, tgt.config) if str(k.meta.get(key, "")) == value), None)
    if partner is None:
        raise HandoffError(f"no case in {tgt.label} waits for {value}")
    written = [assets.put(tgt.store, tgt.config, partner.id, name, path, path.name) for name, path in _files(store, case_id, spec.get("files") or {})]
    e = spec.get("entry") or {}
    text = fill(str(e.get("text", "")), ctx)
    action = str(spec.get("action", "note"))
    actor = str(spec.get("by", "")) or by
    if action == "note":                            # a plain note needs no person of the target: it is said in the thread
        _entry(tgt, partner.id, partner.stage, spec, ctx, written, f"{config.name}: {ctx['source'].get('title', case_id)}", config.name)
        return {"mode": "deliver", "target": tgt.key, "target_label": tgt.label, "case": partner.id, "files": written,
                "url": tgt.url.rstrip("/") + f"/case/{partner.id}" if tgt.url else ""}
    r = stepping.step(tgt.store, tgt.config, partner.id, StepRequest(action=action, step_id=(request_id or f"handoff-{case_id}")[:80],
                      payload={"files": written, "note": text, "text": text, **({"title": fill(str(e["title"]), ctx)} if e.get("title") else {})}), actor)
    if not r.ok:
        raise HandoffError(f"{tgt.label} refused '{action}' on {partner.id}: {r.reason}")
    return {"mode": "deliver", "target": tgt.key, "target_label": tgt.label, "case": partner.id, "files": written,
            "url": tgt.url.rstrip("/") + f"/case/{partner.id}" if tgt.url else ""}


def hand_over(store: FsStore, config: DomainConfig, case_id: str, tgt: Target, spec: dict, by: str, request_id: str = "") -> dict:
    """Carry out a spec against a resolved target. The caller resolves the target (the workspace's targets.json, or a sandbox)."""
    mode = spec.get("mode") or ("deliver" if spec.get("match") and not spec.get("create") else "create")
    return (deliver if mode == "deliver" else create)(store, config, case_id, tgt, spec, by, request_id)


def execute(store: FsStore, config: DomainConfig, case_id: str, by: str) -> dict:
    """Carry out the confirmed rule of the matrix for this case. Returns what `aktion.json` records."""
    ctx = _context(store, config, case_id)
    picked = (ctx["_case"].data.get("einordnung.json") or {}).get("rule")
    rule = next((r for r in matrix(store, config) if r["id"] == picked), None)
    if rule is None:
        raise HandoffError("no rule of the matrix fits this reading — file it away or change the reading")
    result = {"rule": rule["id"], "action": rule.get("action"), "by": by, "at": _now()}
    act = rule.get("action")
    if act in ("create_case", "note_to_case", "deliver"):
        tgt = target(store, rule.get("target", ""))
        spec = {**rule, "files": rule.get("files") or rule.get("carry") or {}, "action": rule.get("step", "note")}   # the row's action is the matrix's word; the target's step is `step`
        spec.setdefault("entry", {"title": rule.get("entry_title", "{mail.title}"),
                                  "text": "{summary}\n\n*" + config.name + " · {sender} · " + rule["id"] + "*"})
        if act == "create_case":
            spec.setdefault("external_id", "")
            if not spec["external_id"] and tgt.external_prefix:
                spec["external_id"] = tgt.external_prefix + "{year}-0{seq}"
            done = create(store, config, case_id, tgt, spec, by, ctx=ctx)
        else:
            spec.setdefault("match", {"key": "external_id", "value": "{fields.reference}"})
            done = deliver(store, config, case_id, tgt, spec, by, request_id=f"rule-{case_id}"[:60], ctx=ctx)
        result.update({k: v for k, v in done.items() if k not in ("mode",)})
    elif act == "file_away":
        result.update(note="filed away")
    else:
        raise HandoffError(f"the action '{act}' is not connected yet")
    stage_now = store.find(case_id)
    store.write_json(f"{stage_now}/{case_id}/aktion.json", result)
    return result
