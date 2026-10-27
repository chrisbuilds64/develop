"""Composing: a document assembled from approved text modules, chosen by rules over a result — by the core, never by the AI.

The helper reads what a person recorded (a dictation, a calculation) and writes the result as data (`ergebnis.json`, every
value with the words it came from). This module turns the result into the document: per section, the first module whose
condition holds; each module quoted with its id and version, so a reader sees which approved sentence stands where and why.
A module that is not approved, or a value a module needs and the result lacks, is a refusal that names it.

The structure is configuration (`aufbau.json`, the pipeline root's copy wins over the domain's):

    {"source": "ergebnis.json", "target": "gutachten.md", "modules": "_bausteine",
     "title": "Kfz-Schadengutachten", "head": [["Auftragsnummer", "{order}"], …],
     "derive": [{"id": "quote_rk", "ratio": ["rk_brutto", "wbw"]}],
     "sections": [{"title": "Befund", "text": "{befund}"},
                  {"title": "Totalschadenprüfung", "choose": [
                      {"module": "B-13", "when": {"quote_rk": {"gte": 100}}, "rule": "R-07"},
                      {"module": "B-12", "rule": "R-07"}]}]}

Modules are the rulebook's `_bausteine/<id>-*.md`: front matter (id, title, version, status) and a body that may carry
`{field}`, `{field|eur}` or `{field|pct}`. Only `status: freigegeben` is used.
"""

from __future__ import annotations

import json
import re

from ..config import DomainConfig
from ..store import FsStore
from .cases import split_version

PLACE = re.compile(r"\{([a-z_][a-z0-9_]*)(?:\|([a-z]+))?\}")


class ComposeError(Exception):
    """A sentence for the person."""


def structure(store: FsStore, config: DomainConfig) -> dict:
    for p in (store.root / "aufbau.json", (config.dir / "aufbau.json") if config.dir else None):
        if p and p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    raise ComposeError("no structure (aufbau.json) in this application")


def modules(store: FsStore, folder: str = "_bausteine") -> dict[str, dict]:
    out = {}
    d = store.root / folder
    for p in sorted(d.glob("*.md")) if d.is_dir() else []:
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        if not m:
            continue
        head = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
        head = {k.strip(): v.strip() for k, v in head.items()}
        if head.get("id"):
            out[head["id"]] = {**head, "body": m.group(2).strip()}
    return out


def _eur(x: float) -> str:
    return f"{x:,.2f} €".replace(",", "x").replace(".", ",").replace("x", ".")


def _fill(text: str, values: dict, missing: set) -> str:
    def one(m):
        key, fmt = m.group(1), m.group(2)
        if key not in values or values[key] in (None, ""):
            missing.add(key)
            return m.group(0)
        v = values[key]
        if fmt == "eur":
            return _eur(float(v))
        if fmt == "pct":
            return f"{float(v):.1f} %".replace(".", ",")
        return str(v)
    return PLACE.sub(one, text)


def _holds(when: dict, values: dict) -> bool:
    for field, want in (when or {}).items():
        have = values.get(field)
        if isinstance(want, dict):
            try:
                n = float(have)
            except (TypeError, ValueError):
                return False
            tests = {"gte": n.__ge__, "gt": n.__gt__, "lte": n.__le__, "lt": n.__lt__}
            if not all(tests[op](float(limit)) for op, limit in want.items() if op in tests):
                return False
        elif str(have).strip().lower() not in [str(w).lower() for w in (want if isinstance(want, list) else [want])]:
            return False
    return True


def compose(result: dict, spec: dict, mods: dict[str, dict]) -> tuple[str, list[dict]]:
    """The document and the list of modules it used, in order. Raises ComposeError naming what is missing."""
    values = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in (result.get("fields") or {}).items()}
    words = {k: (v.get("word") if isinstance(v, dict) else None) or k for k, v in (result.get("fields") or {}).items()}
    for d in spec.get("derive") or []:                                  # a ratio in percent or a difference, from two values of the result
        a, b = d.get("ratio") or d.get("minus")
        try:
            values[d["id"]] = round(float(values[a]) / float(values[b]) * 100, 1) if "ratio" in d else round(float(values[a]) - float(values[b]), 2)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            pass
    missing: set = set()
    used: list[dict] = []
    out = [f"# {_fill(spec.get('title', ''), values, missing)}", ""]
    if spec.get("head"):
        out += ["| | |", "|---|---|"] + [f"| **{k}** | {_fill(v, values, missing)} |" for k, v in spec["head"]] + [""]
    for sec in spec.get("sections", []):
        if sec.get("when") and not _holds(sec["when"], values):
            continue
        body = []
        if sec.get("text"):
            body.append(_fill(sec["text"], values, missing))
        for choice in ([next((c for c in sec["choose"] if _holds(c.get("when"), values)), None)] if sec.get("choose") else []) + \
                [m for m in sec.get("always", [])]:
            if not choice:
                continue
            mod = mods.get(choice["module"])
            if not mod:
                raise ComposeError(f"module {choice['module']} is not in the rulebook")
            if mod.get("status") != "freigegeben":
                raise ComposeError(f"module {choice['module']} is not approved (status: {mod.get('status', '—')})")
            text = _fill(mod["body"], values, missing)
            after = (" " + _fill(choice["after"], values, missing)) if choice.get("after") else ""
            body.append(f"> **[{mod['id']} · {mod.get('title', '')}, Fassung {mod.get('version', '?')}]** {text}{after}")
            used.append({"module": mod["id"], "version": mod.get("version"), "section": sec["title"], "rule": choice.get("rule", "")})
        if body:
            out += [f"## {sec['title']}", *body, ""]
    if spec.get("footer"):
        out += [_fill(spec["footer"], values, missing), ""]
    if missing:
        raise ComposeError((spec.get("words") or {}).get("missing", "still missing in the result: {fields}").format(fields=", ".join(words.get(k, k) for k in sorted(missing))))
    trail = ", ".join(f"{u['module']} (F{u['version']})" for u in used)
    out += [f"*{(spec.get('words') or {}).get('trail', 'Composed from approved modules')}: {trail}.*", ""]
    return "\n".join(out), used


def compile_document(store: FsStore, config: DomainConfig, case_id: str) -> dict:
    """Compose the case's document from its newest result and leave it beside it as the next version of the target."""
    from .assets import next_name
    spec = structure(store, config)
    source, target = spec.get("source", "ergebnis.json"), spec.get("target", "document.md")
    stage = store.find(case_id)
    files = store.files(case_id)
    versions = sorted((split_version(f)[1], f) for f in files if split_version(f)[0] == source)
    if not versions:
        raise ComposeError(f"the result ({source}) is missing")
    text, used = compose(store.read_json(f"{stage}/{case_id}/{versions[-1][1]}"), spec, modules(store, spec.get("modules", "_bausteine")))
    name = next_name(files, target)
    store.write_atomic(f"{stage}/{case_id}/{name}", text)
    return {"file": name, "modules": [u["module"] for u in used]}
