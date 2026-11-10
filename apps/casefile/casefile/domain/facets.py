"""Facets: what the surface may filter by, sort by and show on a card — for every application, from its configuration.

Nothing here names a domain. The facets come from what an application already declares:

    every value list (lists.json)          kind "list"    — the entries, with their words and colours
    every declared field (theme.fields)    kind "person", "date", "text", or "list" when the field takes a list
    the data points of an instance         kind "point"   — "Private", "Team" (ADR-032), only when there are several
    the stages                             kind "stage"   — always; the board shows them as columns, the table filters by them

What each does on the surface has a default by kind, and a list or a field may say otherwise with `view`:

    "priority": {"list": "priority", "view": {"filter": true, "sort": true, "card": true}}
    lists.json: "origin": {"field": "origin_kind", "view": {"card": false}, "entries": [...]}

    kind     filter  sort  card
    list     yes     yes   yes      sorted by the order of the list's entries
    person   yes     yes   yes      sorted by name
    point    yes     no    yes
    stage    yes     yes   no       sorted by the order of the stages; `theme.stage_view` may say otherwise
    date     no      yes   yes      a date is narrowed by the surface's own switches ("overdue"), not by a choice
    text     no      no    no       the title search covers text

The value a case carries for a facet is its meta field; the label lives on the case itself (`case.label`).
"""

from __future__ import annotations

from ..config import DomainConfig
from . import fields as declared_fields
from . import lists as value_lists

DEFAULTS = {
    "list": {"filter": True, "sort": True, "card": True},
    "person": {"filter": True, "sort": True, "card": True},
    "point": {"filter": True, "sort": False, "card": True},
    "stage": {"filter": True, "sort": True, "card": False},
    "date": {"filter": False, "sort": True, "card": True},
    "text": {"filter": False, "sort": False, "card": False},
}
POINT = "data_point"
STAGE = "stage"


def _view(kind: str, over) -> dict:
    out = dict(DEFAULTS[kind])
    for k in out:
        if isinstance(over, dict) and isinstance(over.get(k), bool):
            out[k] = over[k]
    return out


def facets(config: DomainConfig, lang: str, points: list | None = None) -> list[dict]:
    """[{key, word, kind, filter, sort, card, values: [{key, word, color}]}] in the order: lists, then fields, then the
    data point. A facet that does nothing (no filter, no sort, no card) is left out."""
    out: list[dict] = []
    seen: set[str] = set()
    specs = declared_fields.declared(config)
    for lst in config.lists.values():
        key = lst["field"]
        spec = specs.get(key) or {}
        over = {**(lst.get("view") or {}), **(spec.get("view") or {})}
        out.append({"key": key, "word": value_lists.list_word(lst, lang, config.vocabulary), "kind": "list", **_view("list", over),
                    "values": [{"key": e["key"], "word": value_lists.in_lang(e["word"], lang, e["key"]), "color": e["color"]}
                               for e in lst["entries"]]})
        seen.add(key)
    for key, spec in specs.items():
        if key in seen or key == "title":
            continue
        kind = "list" if spec.get("list") else str(spec.get("kind") or "text")
        if kind not in DEFAULTS:
            continue
        values = []
        if kind == "person":
            values = [{"key": p.id, "word": p.name, "color": ""} for p in config.people]
        elif kind == "list":
            lst = config.lists.get(str(spec["list"]))
            values = [{"key": e["key"], "word": value_lists.in_lang(e["word"], lang, e["key"]), "color": e["color"]}
                      for e in (lst or {}).get("entries", [])]
        out.append({"key": key, "word": config.word("fields", key, lang, key), "kind": kind, **_view(kind, spec.get("view")), "values": values})
        seen.add(key)
    if points and len(points) > 1:
        over = (config.theme.get("data_points") or {}).get("view") if isinstance(config.theme.get("data_points"), dict) else None
        out.append({"key": POINT, "word": config.word("fields", POINT, lang, "Data point" if lang != "de" else "Datenpunkt"), "kind": "point",
                    **_view("point", over), "values": [{"key": p.name, "word": p.label or p.name, "color": ""} for p in points]})
    out.append({"key": STAGE, "word": config.word("fields", STAGE, lang, "Stufe" if lang == "de" else "Stage"), "kind": "stage",
                **_view("stage", config.theme.get("stage_view")),
                "values": [{"key": st.folder, "word": config.word("stages", st.folder, lang, st.key), "color": ""} for st in config.stages]})
    return [f for f in out if f["filter"] or f["sort"] or f["card"]]


def keys(config: DomainConfig) -> list[str]:
    """The meta fields a card carries values for: every list's field and every declared field but text."""
    out = [l["field"] for l in config.lists.values()]
    for k, spec in declared_fields.declared(config).items():
        if k not in out and (spec.get("list") or spec.get("kind") in ("person", "date")):
            out.append(k)
    return out + [POINT, STAGE]


def values_of(case, keys: list[str], point: str = "") -> dict[str, str]:
    """What one case carries for each facet, as text; empty when it carries nothing."""
    out: dict[str, str] = {}
    for k in keys:
        if k == POINT:
            v = point
        elif k == STAGE:
            v = case.stage
        elif k == "label":
            v = case.label or case.meta.get("label") or ""
        else:
            v = case.meta.get(k)
        if v not in (None, ""):
            out[k] = str(v)
    return out
