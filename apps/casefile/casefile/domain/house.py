"""The house's canon at one glance: every document placed by layer (who wins) and depth (how concrete), with its scope,
status, owner, origin and what carries it out (canonical-hierarchy: Depth, Every rule carries).

The source is `_kanon/index.json` at the pipeline root, written by whoever keeps the canon — never by this app:

    {"house", "lead", "areas": [{"id", "title", "lead"}],
     "docs":    [{"file", "title", "layer": basis|marke|bereich, "area", "depth": 0-5, "kind", "scope", "status",
                  "evidence", "open", "owner", "implements": [..], "lead", "note", "origin": {...}}],
     "gaps":    [{"layer", "area", "depth", "title", "lead"}],
     "records": [{"title", "case", "file", "uses": [doc file, ..], "lead"}]}

`file` is relative to `_kanon/`. An area canon a Gatehouse elicitation compiled (`canon.md` in a case) joins as a
document of its area by itself: approved once compiled, a proposal while it is still being decided. Without an
index the overview still stands — the basis and brand files and the elicitations are enough.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..store import FsStore, StoreError
from . import cases as reading
from .interview import CANON_DIR, canon_layer

LAYERS = ("basis", "marke", "bereich")
SAFE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]{0,200}$")


def _index(root: Path) -> dict:
    f = root / CANON_DIR / "index.json"
    if not f.is_file():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def overview(store: FsStore) -> dict:
    """The index, completed by what the tree itself holds: the basis and brand files, and every elicitation's area canon."""
    root = Path(store.root)
    ix = _index(root)
    docs = [dict(d) for d in ix.get("docs", []) if d.get("layer") in LAYERS]
    areas = [dict(a) for a in ix.get("areas", [])]
    known = {d.get("file") for d in docs}
    for name, layer in (("basis.md", "basis"), ("marke.md", "marke")):        # an index names its own documents
        if not ix and name not in known and (root / CANON_DIR / name).is_file():
            l = canon_layer(root, name[:-3])
            docs.append({"file": name, "title": l["title"], "layer": layer, "depth": 1, "kind": "Grundsatz", "status": "freigegeben",
                         "scope": "ganzes Haus" if layer == "basis" else "Marke", "lead": f"{l['rules']} Grundsätze" if l["rules"] else ""})
    area_ids = {a["id"] for a in areas}
    for stage in store.stages():
        for cid in store.cases(stage):
            try:
                meta = store.case_json(cid, "meta.json")
            except (StoreError, OSError, ValueError):
                continue
            if not meta.get("pack"):
                continue
            title = str(meta.get("area") or meta.get("title") or cid)
            aid = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or cid
            if aid not in area_ids:
                areas.append({"id": aid, "title": title, "lead": str(meta.get("subtitle") or "")})
                area_ids.add(aid)
            canon = reading.newest_versions(store.files(cid)).get("canon.md")
            docs.append({"case": cid, "title": f"Bereichskanon {str(meta.get('title') or cid)}", "layer": "bereich", "area": aid, "depth": 2,
                         "kind": "Prozess und Verfahren", "scope": f"Bereich {title}", "owner": "Entscheider der Erhebung",
                         "status": "freigegeben" if canon else "vorgeschlagen",
                         "version": max(1, reading.split_version(canon)[1]) if canon else 0,
                         "lead": "aus der Erhebung, Zeile für Zeile entschieden" if canon else "Erhebung läuft, noch nichts beschlossen",
                         "origin": {"kind": "erhoben", "text": f"Erhebung {cid}"}})
    return {"house": str(ix.get("house") or ""), "lead": str(ix.get("lead") or ""), "updated": str(ix.get("updated") or ""),
            "areas": areas, "docs": docs, "gaps": list(ix.get("gaps", [])), "records": list(ix.get("records", []))}


def doc_text(store: FsStore, file: str) -> str:
    """One document of the house canon, by its path under `_kanon/`. Nothing outside that folder is readable here."""
    if not SAFE.match(file) or ".." in file.split("/"):
        raise FileNotFoundError(file)
    base = (Path(store.root) / CANON_DIR).resolve()
    p = (base / file).resolve()
    if base not in p.parents or not p.is_file() or p.suffix not in (".md", ".txt"):
        raise FileNotFoundError(file)
    return p.read_text(encoding="utf-8", errors="replace")
