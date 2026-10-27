"""A hand-off: a case in one application starts or feeds a case in another — the rule matrix's action, made real.

The matrix (`regeln.json`, the pipeline root's copy wins over the domain's) says per kind of case what happens:

    {"rules": [{"id": "R-01", "kind": "schadensmeldung", "word": {"de": "Schadensmeldung", "en": "Claim report"},
                "action": "create_case", "target": "schadenakte", "label": "KFZ", "approval": "human",
                "carry": {"images": "fotos-{n}.jpg", "mail.md": "meldung.md"},
                "meta": {"title": "{fields.title}", "subtitle": "{fields.summary}", "policy": "{fields.policy}"}, "run": "<a helper of the target, optional>"},
               {"id": "R-09", "kind": "werbung", "action": "file_away", "approval": "auto"}]}

The helper's reading (`einordnung.json`: kind, rule, fields, summary, reasons) picks the row; a person confirms; this
module does it. Targets are named in `targets.json` at the root (root, config, url) — written by whoever set the workspace
up, so the engine never guesses another application's folder. The result is `aktion.json` beside the mail, and an entry in
the target case's thread that says where it came from.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from ..config import DomainConfig
from ..store import FsStore, StoreError
from . import cases as reading

IMAGES = (".jpg", ".jpeg", ".png", ".webp")


class HandoffError(Exception):
    """A sentence for the person."""


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def matrix(store: FsStore, config: DomainConfig) -> list[dict]:
    for p in (store.root / "regeln.json", (config.dir / "regeln.json") if config.dir else None):
        if p and p.is_file():
            try:
                return [r for r in json.loads(p.read_text(encoding="utf-8")).get("rules", []) if isinstance(r, dict) and r.get("id")]
            except ValueError:
                return []
    return []


def targets(store: FsStore) -> dict:
    p = store.root / "targets.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        return {}


def _fill(template: str, ctx: dict) -> str:
    def one(m):
        cur = ctx
        for part in m.group(1).split("."):
            cur = cur.get(part, "") if isinstance(cur, dict) else ""
        return str(cur or "")
    return re.sub(r"\{([a-z_.]+)\}", one, template).strip()


def execute(store: FsStore, config: DomainConfig, case_id: str, by: str) -> dict:
    """Carry out the confirmed rule for this case. Returns what `aktion.json` records."""
    case = reading.load(store, config, case_id)
    reading_ = case.data.get("einordnung.json") or {}
    rule = next((r for r in matrix(store, config) if r["id"] == reading_.get("rule")), None)
    if rule is None:
        raise HandoffError("no rule of the matrix fits this reading — file it away or change the reading")
    result = {"rule": rule["id"], "action": rule.get("action"), "by": by, "at": _now()}
    if rule.get("action") == "create_case":
        t = targets(store).get(rule.get("target", ""))
        if not t:
            raise HandoffError(f"target '{rule.get('target')}' is not connected in this workspace")
        tstore = FsStore(Path(t["root"]))
        tconfig = DomainConfig.load(Path(t["config"]), tstore.root)
        stage = t.get("stage") or next((s.folder for s in tconfig.stages if s.group != "archive"), None)
        if not stage or stage not in tstore.stages():
            raise HandoffError("the target's first stage is missing")
        label = rule.get("label") or t.get("label") or "X"
        year = dt.date.today().year
        nums = [int(x.group(1)) for st in tstore.stages() for c in tstore.cases(st) if (x := re.match(rf"^{re.escape(label)}-{year}-(\d+)", c))]
        number = f"{year}-{(max(nums) + 1) if nums else 1:04d}"
        ctx = {"fields": reading_.get("fields") or {}, "summary": reading_.get("summary", ""), "mail": case.meta}
        title = _fill(rule.get("meta", {}).get("title", "{mail.title}"), ctx) or str(case.meta.get("title") or case_id)
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))).strip("-")[:40] or "meldung"
        tid = f"{label}-{number}-{slug}"
        tstore.mkcase(stage, tid)
        meta = {"configVersion": tconfig.config_version, "label": label, "number": number, "title": title, "created": _now()[:10],
                **{k: _fill(v, ctx) for k, v in (rule.get("meta") or {}).items() if k != "title"},
                "origin": {"application": config.name, "case": case_id, "message_id": case.meta.get("message_id", "")}}
        if t.get("external_prefix"):
            meta["external_id"] = f"{t['external_prefix']}{number.replace(f'{year}-', f'{year}-0')}"
        tstore.write_json(f"{stage}/{tid}/meta.json", {k: v for k, v in meta.items() if v != ""})
        carried = []
        carry = rule.get("carry") or {}
        files = [f for f in store.files(case_id) if f not in ("meta.json", "review.md", "mail.eml", "einordnung.json", "aktion.json")]
        n = 0
        for f in files:
            src = store.case_dir(case_id) / f
            if f.lower().endswith(IMAGES) and carry.get("images"):
                n += 1
                name = carry["images"].replace("{n}", str(n))
            elif f in carry:
                name = carry[f]
            else:
                continue
            tstore.put_bytes(tid, name, src.read_bytes())
            carried.append(name)
        from . import step as stepping
        stepping._append_entry(tstore, tconfig, tid, stage, {"author": config.name, "status": "info",
                               "title": _fill(rule.get("entry_title", "{mail.title}"), ctx)[:120] or title,
                               "text": (reading_.get("summary") or "") + f"\n\n*{config.name} · {case.meta.get('from_name') or case.meta.get('from', '')} · {rule['id']}*",
                               "files": carried})
        if rule.get("run"):                                         # the target's first helper starts at once: the questionnaire fills while the person reads on
            from . import runs as ordering
            result["run"] = ordering.order(tstore, tconfig, tid, stage, rule["run"], by, request_id=f"handoff-{case_id}")
        result.update(target=rule.get("target"), target_label=t.get("label", rule.get("target")), case=tid, title=title, url=t.get("url", "").rstrip("/") + f"/case/{tid}" if t.get("url") else "")
    elif rule.get("action") == "file_away":
        result.update(note="filed away")
    else:
        raise HandoffError(f"the action '{rule.get('action')}' is not connected yet")
    stage_now = store.find(case_id)
    store.write_json(f"{stage_now}/{case_id}/aktion.json", result)
    return result
