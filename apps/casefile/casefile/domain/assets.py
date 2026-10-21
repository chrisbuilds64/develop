"""Putting a file into a slot: a new version beside the old ones, never a replacement.

A deliverable starts unversioned (`substack.md`); the first revision becomes `.v2` beside it; the
version counter only goes up. Images and videos do the same (`thumbnail-16x9.v2.png`).
"""

from __future__ import annotations

from pathlib import Path

from ..config import DomainConfig
from ..store import FsStore, StoreError
from .cases import split_version

ALLOWED = {"image": ("png", "jpg", "jpeg", "webp"), "video": ("mp4", "mov", "webm"), "pdf": ("pdf",), "text": ("md", "txt", "html")}


def next_name(files: list[str], slot_file: str) -> str:
    stem, _, ext = slot_file.rpartition(".")
    versions = [split_version(f)[1] for f in files if split_version(f)[0] == slot_file]
    if not versions:
        return slot_file
    return f"{stem}.v{max(max(versions), 1) + 1}.{ext}"


def put(store: FsStore, config: DomainConfig, case_id: str, slot_file: str, data: bytes | Path, original_name: str = "") -> str:
    """Store `data` (bytes or a path) as the next version of `slot_file`. Returns the name written."""
    stage = store.find(case_id)
    if stage is None:
        raise StoreError(f"case '{case_id}' not found")
    meta = store.case_json(case_id, "meta.json") if store.exists(f"{stage}/{case_id}/meta.json") else {}
    label = str(meta.get("label") or case_id.split("-", 1)[0])
    deliverable = next((d for d in config.deliverables(label) if d.file == slot_file), None)
    if deliverable is None:
        raise StoreError(f"'{slot_file}' is not a deliverable of a {label} case")
    ext = slot_file.rpartition(".")[2].lower()
    family = next((k for k, exts in ALLOWED.items() if ext in exts), None)
    if original_name:
        oext = original_name.rpartition(".")[2].lower()
        if oext == "jpeg":
            oext = "jpg"
        if family and oext not in ALLOWED[family] and not (oext == "jpg" and "jpeg" in ALLOWED[family]):
            raise StoreError(f"'{original_name}' is not a {family} file; {slot_file} takes {', '.join(ALLOWED[family])}")
    name = next_name(store.files(case_id), slot_file)
    if isinstance(data, Path):
        store.put_file(case_id, name, data)
    else:
        if not data:
            raise StoreError("the file is empty")
        store.put_bytes(case_id, name, data)
    return name
