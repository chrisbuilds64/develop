"""The file-system store: the one place the core touches the folders.

Everything the domain does goes through this adapter, so a WebDAV or S3 adapter can replace it
without the domain noticing. Writes are atomic where the file system allows it (write to a
temporary name, rename), appends are real appends, and a per-case lock guards every step: a
threading lock inside the process plus an advisory file lock across processes.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path

STAGE = re.compile(r"^(\d{2})-(.+)$")


class StoreError(Exception):
    """Something the store refuses to do; the message says why in one sentence."""


class FsStore:
    def __init__(self, root: Path, write_root: Path | None = None):
        """`root` is where the tree is read. `write_root`, when given, is the same tree reached through another
        path — a WebDAV mount of the folder Nextcloud serves — and every write goes there, so the sync server
        sees the change. Reading stays on the disk, where it is fast. Without it, both are the same place."""
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise StoreError(f"pipeline root {self.root} is not a directory")
        self.write_root = Path(write_root).resolve() if write_root else self.root
        if not self.write_root.is_dir():
            raise StoreError(f"write root {self.write_root} is not a directory")
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _w(self, rel_or_path) -> Path:
        """The write-side path of something addressed relative to the root."""
        p = Path(rel_or_path)
        if p.is_absolute():
            try:
                p = p.relative_to(self.root)
            except ValueError:
                return p
        return self.write_root / p

    # ------------------------------------------------------------------ layout
    def stages(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir() and STAGE.match(p.name))

    def cases(self, stage: str) -> list[str]:
        d = self.root / stage
        if not d.is_dir():
            return []
        return sorted(p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))

    def find(self, case_id: str) -> str | None:
        """The stage a case stands in, or None. Two stages at once is a broken tree and refused."""
        if "/" in case_id or case_id.startswith("."):
            raise StoreError(f"'{case_id}' is not a case name")
        here = [s for s in self.stages() if (self.root / s / case_id).is_dir()]
        if len(here) > 1:
            raise StoreError(f"'{case_id}' exists in more than one stage: {', '.join(here)} — fix that by hand first")
        return here[0] if here else None

    def case_dir(self, case_id: str) -> Path:
        stage = self.find(case_id)
        if stage is None:
            raise StoreError(f"case '{case_id}' not found in any stage")
        return self.root / stage / case_id

    def files(self, case_id: str) -> list[str]:
        d = self.case_dir(case_id)
        return sorted(p.name for p in d.iterdir() if p.is_file() and not p.name.startswith("."))

    def size(self, case_id: str, name: str) -> int:
        return (self.case_dir(case_id) / name).stat().st_size

    # ------------------------------------------------------------------ reading
    def read_text(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def read_json(self, rel: str) -> dict:
        return json.loads(self.read_text(rel))

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def case_text(self, case_id: str, name: str) -> str:
        return (self.case_dir(case_id) / name).read_text(encoding="utf-8")

    def case_json(self, case_id: str, name: str) -> dict:
        return json.loads(self.case_text(case_id, name))

    # ------------------------------------------------------------------ writing
    def write_atomic(self, rel: str, text: str) -> None:
        p = self._w(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f".{p.name}.tmp-{os.getpid()}")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, p)

    def write_json(self, rel: str, doc: dict) -> None:
        self.write_atomic(rel, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")

    def append(self, rel: str, text: str, head: str = "") -> None:
        """A real append. `head` is written first when the file does not exist yet."""
        p = self._w(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() and head:
            p.write_text(head, encoding="utf-8")
        with p.open("a", encoding="utf-8") as fh:
            fh.write(text)

    def put_file(self, case_id: str, name: str, src: Path) -> int:
        """Copy a file into the case under `name`; refuses to overwrite. Returns the size."""
        target = self.case_dir(case_id) / name
        if target.exists():
            raise StoreError(f"{target.name} already exists — nothing overwritten")
        shutil.copyfile(src, self._w(target))
        return self._w(target).stat().st_size

    def put_bytes(self, case_id: str, name: str, data: bytes) -> int:
        target = self.case_dir(case_id) / name
        if target.exists():
            raise StoreError(f"{target.name} already exists — nothing overwritten")
        self._w(target).write_bytes(data)
        return len(data)

    def move(self, case_id: str, to_stage: str) -> tuple[str, str]:
        """Rename the case folder into another stage. Returns (from, to)."""
        if to_stage not in self.stages():
            raise StoreError(f"stage '{to_stage}' does not exist")
        src = self.case_dir(case_id)
        dst = self.root / to_stage / case_id
        if src == dst:
            raise StoreError(f"'{case_id}' is already in {to_stage}")
        if dst.exists():
            raise StoreError(f"{to_stage}/{case_id} already exists — nothing overwritten")
        self._w(src).rename(self._w(dst))
        return src.parent.name, to_stage

    def mkcase(self, stage: str, case_id: str) -> Path:
        if self.find(case_id) is not None:
            raise StoreError(f"'{case_id}' already exists")
        d = self.root / stage / case_id
        self._w(d).mkdir(parents=True, exist_ok=False)
        return d

    # ------------------------------------------------------------------ journals and runs
    def journals(self) -> list[str]:
        d = self.root / "_steps"
        return sorted(p.name for p in d.glob("*.json")) if d.is_dir() else []

    def runs(self) -> list[str]:
        d = self.root / "_runs"
        return sorted(p.name for p in d.glob("*.json")) if d.is_dir() else []

    # ------------------------------------------------------------------ locking
    def _lock_dir(self) -> Path:
        """Where the advisory lock files live. Beside the journals when the tree is written where it is read; on
        the local disk when writes go through a mount — the read side may be read-only for this process, and a
        WebDAV mount does not hold a flock. One cockpit per tree holds the thread lock anyway; the file lock is
        for a second process on the same machine."""
        if self.write_root == self.root:
            d = self.root / "_steps"
        else:
            d = Path(tempfile.gettempdir()) / ("casefile-locks-" + hashlib.sha1(str(self.root).encode()).hexdigest()[:12])
        d.mkdir(parents=True, exist_ok=True)
        return d

    @contextlib.contextmanager
    def lock(self, case_id: str):
        """One step at a time per case: a thread lock in the process, an advisory lock across processes."""
        with self._locks_guard:
            tl = self._locks.setdefault(case_id, threading.Lock())
        with tl:
            d = self._lock_dir()
            lock_path = d / f".lock-{case_id}"
            with lock_path.open("a+") as fh:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
