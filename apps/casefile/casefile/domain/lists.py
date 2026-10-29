"""Value lists (SYS-105): the fixed values a case's meta may carry — a format, a series, a class of insurance, a channel.

The core knows only *list* and *entry*. Which lists a domain has, which meta field each fills and whether a new case asks
for it, all of that lives in `lists.json`; nothing here names a particular list. Two places feed it, like the vocabulary:
the domain's `config/<domain>/lists.json` and the tree's own `lists.json` at the pipeline root, the tree adding to and
winning over the domain. A change from the surface is written to the tree's file only, never to the configuration in
the repository, and leaves one line in `_lists/log.jsonl`.

    {"lists": {"<id>": {"word": {"de", "en"}, "field": "<meta key>", "on_create": true|false,
                        "entries": [{"key", "word": {"de", "en"}, "color"?, "description"?, "status": "planned|active|retired"}]}}}

The older places stay readable: a domain's `vocabulary.<lang>.labels` and `theme.covers.colors` are translated into a list
when the configuration is loaded (`legacy()`), so a domain without `lists.json` keeps working as before and the logic
below sees only lists. A retired entry stays in its list: cases that carry it still show its name and colour; it is only
no longer offered for a new case.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

STATUSES = ("planned", "active", "retired")
OFFERED = ("active", "planned")                    # what a new case may choose
NEW_KEY = re.compile(r"^[A-Z0-9]{1,16}$")          # a new entry's key: capitals and digits
LIST_ID = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
CORE_FIELDS = ("title", "number", "created", "created_by", "configVersion")   # what the core itself writes into a new case's meta
LOG = "_lists/log.jsonl"
TREE_FILE = "lists.json"


class ListError(Exception):
    """A change that is refused; the message is the sentence the person reads."""


# ----------------------------------------------------------------------------- reading
def _read(p: Path | None) -> dict:
    if p is None or not p.is_file():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def legacy(vocabulary: dict, theme: dict) -> dict:
    """The older shape as a list: `vocabulary.<lang>.labels` (the words of meta `label`) and the colours of
    `theme.covers` for the key it colours by. The only place that reads the older shape; the rest sees lists."""
    words: dict[str, dict] = {}
    for lang, v in (vocabulary or {}).items():
        if isinstance(v, dict) and isinstance(v.get("labels"), dict):
            for key, word in v["labels"].items():
                words.setdefault(str(key), {})[lang] = str(word)
    out: dict = {}
    if words:
        out["label"] = {"field": "label", "entries": [{"key": k, "word": w, "status": "active"} for k, w in words.items()]}
    covers = (theme or {}).get("covers") or {}
    colors = covers.get("colors") or {}
    if colors:
        by = str(covers.get("by") or "label")
        lst = out.setdefault(by, {"field": by, "entries": []})
        known = {e["key"]: e for e in lst["entries"]}
        for key, color in colors.items():
            if key in known:
                known[key]["color"] = color
            else:
                lst["entries"].append({"key": str(key), "word": {}, "color": color, "status": "active"})
    return out


def _merge_list(base: dict, over: dict) -> dict:
    out = {**base, **{k: v for k, v in over.items() if k != "entries"}}
    if isinstance(base.get("word"), dict) and isinstance(over.get("word"), dict):
        out["word"] = {**base["word"], **over["word"]}
    entries = {e["key"]: dict(e) for e in base.get("entries", []) if isinstance(e, dict) and e.get("key")}
    order = list(entries)
    for e in over.get("entries", []) or []:
        if not isinstance(e, dict) or not e.get("key"):
            continue
        k = str(e["key"])
        if k in entries:
            merged = {**entries[k], **e}
            if isinstance(entries[k].get("word"), dict) and isinstance(e.get("word"), dict):
                merged["word"] = {**entries[k]["word"], **e["word"]}
            entries[k] = merged
        else:
            entries[k] = dict(e)
            order.append(k)
    out["entries"] = [entries[k] for k in order]
    return out


def merge(*docs: dict) -> dict:
    """Lists by id, entries by key; a later document adds to and wins over an earlier one."""
    out: dict = {}
    for doc in docs:
        for lid, lst in (doc or {}).items():
            if isinstance(lst, dict) and not str(lid).startswith("$"):
                out[lid] = _merge_list(out.get(lid, {}), lst)
    return out


def _norm(lid: str, lst: dict) -> dict:
    return {"id": lid, "word": dict(lst.get("word") or {}), "field": str(lst.get("field") or lid), "on_create": bool(lst.get("on_create", False)),
            "entries": [{"key": str(e["key"]), "word": dict(e.get("word") or {}), "color": str(e.get("color") or ""),
                         "description": e.get("description") or "", "status": e.get("status") if e.get("status") in STATUSES else "active"}
                        for e in lst.get("entries", [])]}


def build(vocabulary: dict, theme: dict, domain_doc: dict, tree_doc: dict) -> dict[str, dict]:
    merged = merge(legacy(vocabulary, theme), (domain_doc or {}).get("lists") or {}, (tree_doc or {}).get("lists") or {})
    return {lid: _norm(lid, lst) for lid, lst in merged.items()}


def load(domain_dir: Path | None, root: Path | None, vocabulary: dict, theme: dict) -> dict[str, dict]:
    return build(vocabulary, theme, _read(Path(domain_dir) / TREE_FILE if domain_dir else None), _read(Path(root) / TREE_FILE if root else None))


# ----------------------------------------------------------------------------- looking up
def in_lang(words, lang: str, fallback: str = "") -> str:
    """A word in the language, else English, else any, else the fallback. A plain string stands for every language."""
    if isinstance(words, str):
        return words or fallback
    if not isinstance(words, dict):
        return fallback
    return words.get(lang) or words.get("en") or next((v for v in words.values() if v), "") or fallback


def entry(lists: dict, list_id: str, key) -> dict | None:
    lst = lists.get(list_id)
    return next((e for e in lst["entries"] if e["key"] == str(key)), None) if lst and key not in (None, "") else None


def for_field(lists: dict, field: str) -> dict | None:
    """The list that fills this meta field."""
    return next((l for l in lists.values() if l["field"] == field), None)


def list_word(lst: dict, lang: str, vocabulary: dict | None = None) -> str:
    v = (vocabulary or {}).get(lang) or (vocabulary or {}).get("en") or {}
    return in_lang(lst.get("word"), lang) or str((v.get("meta") or {}).get(lst["field"]) or "") or lst["id"]


def value_word(lists: dict, field: str, value, lang: str, fallback: str | None = None) -> str:
    """The word for a meta value through the list that fills its field; the value itself when no list knows it."""
    lst = for_field(lists, field)
    e = entry(lists, lst["id"], value) if lst else None
    word = in_lang(e["word"], lang) if e else ""
    return word or (fallback if fallback is not None else str(value or ""))


def tint(lists: dict, theme: dict, meta: dict) -> str:
    """A case's cover colour. `theme.covers.by` names a list (or, as before, a meta key): the entry's colour first,
    then `covers.colors`, then `covers.fallback`. No covers in the theme, no colour."""
    covers = (theme or {}).get("covers") or {}
    if not covers:
        return ""
    by = str(covers.get("by") or "label")
    lst = lists.get(by) or for_field(lists, by)
    value = str((meta or {}).get(lst["field"] if lst else by) or "")
    e = entry(lists, lst["id"], value) if lst else None
    return (e or {}).get("color") or str((covers.get("colors") or {}).get(value) or covers.get("fallback") or "")


def offered(lst: dict) -> list[dict]:
    return [e for e in lst["entries"] if e["status"] in OFFERED]


def on_create(lists: dict) -> list[dict]:
    return [l for l in lists.values() if l["on_create"]]


def counts(store, lists: dict) -> dict[str, dict[str, int]]:
    """How many cases carry each entry, over every stage folder (the archive too: a retired entry still has its cases)."""
    out = {lid: {} for lid in lists}
    fields = {l["field"]: lid for lid, l in lists.items()}
    for stage in store.stages():
        for cid in store.cases(stage):
            try:
                meta = store.read_json(f"{stage}/{cid}/meta.json")
            except (OSError, ValueError):
                continue
            for field, lid in fields.items():
                v = meta.get(field)
                for val in (v if isinstance(v, list) else [v]):
                    if val not in (None, ""):
                        out[lid][str(val)] = out[lid].get(str(val), 0) + 1
    return out


def validate_choice(lists: dict, values: dict) -> dict:
    """What a new case may carry from the lists that ask for it: {field: key}. Refuses an unknown field, an unknown
    key and a retired entry."""
    asking = {l["field"]: l for l in on_create(lists)}
    out = {}
    for field, key in (values or {}).items():
        if key in (None, ""):
            continue
        lst = asking.get(field)
        if lst is None:
            raise ListError(f"'{field}' is not chosen from a list when a case starts")
        e = entry(lists, lst["id"], key)
        if e is None:
            raise ListError(f"'{key}' is not in the list '{lst['id']}'")
        if e["status"] not in OFFERED:
            raise ListError(f"'{key}' is retired and no longer offered")
        out[field] = e["key"]
    return out


# ----------------------------------------------------------------------------- changing: the tree's file, one log line
def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _replayed(store, step_id: str) -> dict | None:
    if not store.exists(LOG):
        return None
    for line in store.read_text(LOG).splitlines():
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if doc.get("step_id") == step_id:
            return doc
    return None


def _tree(store) -> dict:
    doc = _read(store.root / TREE_FILE)
    doc.setdefault("lists", {})
    return doc


def _words(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v).strip()[:80] for k, v in raw.items() if isinstance(v, str) and v.strip() and re.match(r"^[a-z]{2}$", str(k))}


def _write(store, config, tree: dict, line: dict) -> dict:
    store.write_json(TREE_FILE, tree)
    store.append(LOG, json.dumps(line, ensure_ascii=False) + "\n")
    config.lists = build(config.vocabulary, config.theme, _read(config.dir / TREE_FILE if config.dir else None), tree)
    return line


def put_list(store, config, by: str, list_id: str, word: dict | None, field: str | None, on_create_: bool | None, step_id: str) -> dict:
    """Start a list, or change an existing one's words or whether a new case asks for it. Its field is fixed once set."""
    with store.lock("_lists"):
        prior = _replayed(store, step_id)
        if prior is not None:
            return prior
        if not LIST_ID.match(list_id or ""):
            raise ListError("A list's id is lower-case letters, digits and '-', starting with a letter.")
        existing = config.lists.get(list_id)
        word = _words(word)
        if existing is None:
            field = (field or "").strip()
            if not FIELD.match(field):
                raise ListError("Name the field of the case this list fills: letters, digits and '_'.")
            if field in CORE_FIELDS:
                raise ListError(f"'{field}' is written by the core itself and cannot come from a list.")
            if for_field(config.lists, field):
                raise ListError(f"The field '{field}' is already filled by the list '{for_field(config.lists, field)['id']}'.")
            if not word:
                raise ListError("Give the list a name.")
        elif field and field != existing["field"]:
            raise ListError(f"The list '{list_id}' fills '{existing['field']}'; a list's field does not change.")
        tree = _tree(store)
        head = tree["lists"].setdefault(list_id, {})
        change = {}
        if existing is None:
            change["field"] = field
        if word:
            change["word"] = word
        if on_create_ is not None:
            change["on_create"] = bool(on_create_)
        head.update(change)
        head.setdefault("entries", [])
        return _write(store, config, tree, {"at": _now(), "by": by, "step_id": step_id, "list": list_id, "what": "list" if existing is None else "list-change", "change": change})


def put_entry(store, config, by: str, list_id: str, key: str, word: dict | None, color: str | None, description, status: str | None, step_id: str) -> dict:
    """Add an entry to a list, or change one: its words, colour, description or status. Nothing is ever removed."""
    with store.lock("_lists"):
        prior = _replayed(store, step_id)
        if prior is not None:
            return prior
        lst = config.lists.get(list_id)
        if lst is None:
            raise ListError(f"There is no list '{list_id}'.")
        key = (key or "").strip()
        existing = entry(config.lists, list_id, key)
        word = _words(word)
        if existing is None:
            if not NEW_KEY.match(key):
                raise ListError("A key is 1 to 16 capital letters or digits.")
            if key.upper() in {e["key"].upper() for e in lst["entries"]}:
                raise ListError(f"'{key}' is already in this list.")
            if not word:
                raise ListError("Give the entry a name.")
        if status is not None and status not in STATUSES:
            raise ListError("The status is planned, active or retired.")
        if color and not COLOR.match(color):
            raise ListError("A colour is written #rrggbb.")
        change: dict = {}
        if word:
            change["word"] = word
        if color is not None:
            change["color"] = color
        if description is not None:
            change["description"] = _words(description) if isinstance(description, dict) else str(description).strip()[:300]
        if status is not None or existing is None:
            change["status"] = status or "active"
        if existing is not None and not change:
            raise ListError("Nothing to change.")
        tree = _tree(store)
        head = tree["lists"].setdefault(list_id, {})
        entries = head.setdefault("entries", [])
        mine = next((e for e in entries if e.get("key") == key), None)
        if mine is None:
            entries.append({"key": key, **change})
        else:
            mine.update(change)
        return _write(store, config, tree, {"at": _now(), "by": by, "step_id": step_id, "list": list_id, "key": key,
                                             "what": "entry" if existing is None else "entry-change", "change": change})
