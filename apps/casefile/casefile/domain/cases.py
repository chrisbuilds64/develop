"""Reading a case: the folder, as `turn()` and the surface need it. Pure reads."""

from __future__ import annotations

import json
import re

from ..config import DomainConfig
from ..models import Case, FileVersion, Run, Slot
from ..store import FsStore
from . import entries as thread

VERSION = re.compile(r"\.v(\d+)\.")


def split_version(name: str) -> tuple[str, int]:
    """'thumbnail-16x9.v2.png' → ('thumbnail-16x9.png', 2); 'substack.md' → ('substack.md', 0)."""
    m = VERSION.search(name)
    if not m:
        return name, 0
    return name.replace(m.group(0), ".", 1), int(m.group(1))


SHAPES = {".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".gif": "image", ".pdf": "pdf", ".mp4": "video", ".mov": "video", ".webm": "video",
          ".md": "text", ".txt": "text", ".json": "text", ".html": "text", ".csv": "text"}
HIDDEN = {"meta.json", "review.md"}


def shape_of(name: str) -> str:
    return SHAPES.get("." + name.rsplit(".", 1)[-1].lower() if "." in name else "", "other")


def slots_for(config: DomainConfig, label: str, files: list[str], sizes: dict[str, int] | None = None) -> list[Slot]:
    """The matrix's slots first, filled or empty; then every other file the folder holds — the case shows what is there,
    the matrix only lends words, shapes and due stages to what it knows."""
    present: dict[str, list[FileVersion]] = {}
    for f in files:
        if f.startswith("."):
            continue
        base, v = split_version(f)
        present.setdefault(base, []).append(FileVersion(name=f, version=v, size=(sizes or {}).get(f, 0)))
    out, known = [], set()
    for d in config.deliverables(label):
        versions = sorted(present.get(d.file, []), key=lambda x: x.version)
        out.append(Slot(file=d.file, shape=d.shape, required=d.required, due_stage=d.stage, by=d.by, versions=versions))
        known.add(d.file)
    for base, versions in present.items():
        if base in known or base in HIDDEN:
            continue
        out.append(Slot(file=base, shape=shape_of(base), required=False, due_stage="", by="human", versions=sorted(versions, key=lambda x: x.version)))
    return out


def load_runs(store: FsStore, case_ref: str) -> list[Run]:
    out = []
    for name in store.runs():
        try:
            doc = store.read_json(f"_runs/{name}")
        except (OSError, json.JSONDecodeError):
            continue
        if doc.get("container") == case_ref or doc.get("container", "").split("/")[-1] == case_ref.split("/")[-1]:
            try:
                out.append(Run.model_validate(doc))
            except Exception:
                continue
    return out


def load(store: FsStore, config: DomainConfig, case_id: str) -> Case:
    stage = store.find(case_id)
    if stage is None:
        raise KeyError(case_id)
    files = store.files(case_id)
    meta = store.case_json(case_id, "meta.json") if "meta.json" in files else {}
    label = str(meta.get("label") or case_id.split("-", 1)[0])
    sizes = {f: store.size(case_id, f) for f in files}
    entries = thread.parse(store.case_text(case_id, "review.md")) if "review.md" in files else []
    runs = load_runs(store, f"{stage}/{case_id}")
    since = ""
    for e in reversed(entries):
        if e.to == stage or (e.stage == stage and e.step):
            since = e.date
            break
    if not since:
        since = entries[-1].date if entries else str(meta.get("created") or "")
    return Case(id=case_id, stage=stage, meta=meta, files=files, slots=slots_for(config, label, files, sizes),
                entries=entries, runs=runs, since=since)


def load_all(store: FsStore, config: DomainConfig) -> list[Case]:
    out = []
    for stage in store.stages():
        for cid in store.cases(stage):
            try:
                out.append(load(store, config, cid))
            except KeyError:
                continue
    return out
