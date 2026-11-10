"""One application instance over several data points (ADR-032 decisions 2 and 3, REQ-005 PV).

An instance binds its slot for cases to more than one data point — a person's private folder, a team's shared one. This
store puts them together for one viewer: it reads the cases of every data point the viewer may read, and only those;
it writes only where the viewer may write. Everything that belongs to the instance rather than to a case (its lists,
people, journals, runs) lives in the *home* tree, as in a single tree.

The protection itself is the data point's: a private Nextcloud folder is shared with its owner only, so its files are
out of reach outside this process too. Inside, this store is the one gate — a case of an unreadable data point is not
found, not listed, not numbered over by anyone who could learn its title.

    MultiStore(home, [DataPoint("chris", FsStore(...), readers={"chris"}, writers={"chris"}), ...], viewer="chris")

A case lives in exactly one data point; a case id twice across data points is a broken binding and refused. Numbers
count over all data points (`everything`), so a private SYS-148 and a shared SYS-148 cannot both come into being.

Where each case lies is read once per store — one listing of every stage of every data point — and kept until a case
moves, opens or changes data point. The store lives for one request, so the index never outlives what it saw.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path

from .fs import STAGE, FsStore, StoreError


@dataclass
class DataPoint:
    name: str
    store: FsStore
    readers: set[str] = field(default_factory=set)       # person ids; "*" = every member of the instance
    writers: set[str] = field(default_factory=set)
    label: str = ""                                       # what the surface calls it ("Private", "Team")

    def may_read(self, who: str | None) -> bool:
        return "*" in self.readers or (who is not None and (who in self.readers or who in self.writers))

    def may_write(self, who: str | None) -> bool:
        return "*" in self.writers or (who is not None and who in self.writers)


class MultiStore:
    def __init__(self, home: FsStore, points: list[DataPoint], viewer: str | None, create_in: str | None = None,
                 unscoped: bool = False):
        names = [p.name for p in points]
        if len(set(names)) != len(names):
            raise StoreError("two data points share a name")
        self.home, self.all_points, self.viewer = home, points, viewer
        self.points = points if unscoped else [p for p in points if p.may_read(viewer)]
        self.create_in = create_in
        self.root, self.write_root = home.root, home.write_root
        self._index: dict[str, list[tuple[DataPoint, str]]] | None = None

    def _where(self) -> dict[str, list[tuple[DataPoint, str]]]:
        """case id -> [(data point, stage)], from one listing of every readable data point."""
        if self._index is None:
            idx: dict[str, list[tuple[DataPoint, str]]] = {}
            for p in self.points:
                for stage in p.store.stages():
                    for case in p.store.cases(stage):
                        idx.setdefault(case, []).append((p, stage))
            self._index = idx
        return self._index

    def _forget(self) -> None:
        self._index = None

    # ------------------------------------------------------------------ scopes
    @property
    def everything(self) -> "MultiStore":
        """Every data point, readable or not — for numbering and uniqueness only, never for showing."""
        return MultiStore(self.home, self.all_points, self.viewer, self.create_in, unscoped=True)

    def point(self, name: str) -> DataPoint:
        p = next((x for x in self.all_points if x.name == name), None)
        if p is None:
            raise StoreError(f"no data point '{name}'")
        return p

    def _located(self, case_id: str) -> tuple[DataPoint, str] | None:
        here = self._where().get(case_id) or []
        if len({p.name for p, _ in here}) > 1:
            raise StoreError(f"'{case_id}' exists in more than one data point: {', '.join(sorted({p.name for p, _ in here}))}")
        if len(here) > 1:
            raise StoreError(f"'{case_id}' exists in more than one stage: {', '.join(s for _, s in here)} — fix that by hand first")
        return here[0] if here else None

    def point_of(self, case_id: str) -> DataPoint | None:
        at = self._located(case_id)
        return at[0] if at else None

    def _writable(self, case_id: str) -> FsStore:
        p = self.point_of(case_id)
        if p is None:
            raise StoreError(f"case '{case_id}' not found in any stage")
        if not p.may_write(self.viewer):
            raise StoreError(f"{self.viewer or 'nobody'} may not write in '{p.name}'")
        return p.store

    def _route(self, rel: str, write: bool = False) -> tuple[FsStore, str]:
        """A path relative to the instance: `<stage>/<case>/…` goes to the case's data point, anything else home."""
        parts = Path(rel).parts
        if len(parts) >= 2 and STAGE.match(parts[0]) and not parts[1].startswith(("_", ".")):
            p = self.point_of(parts[1])
            if p is not None:
                if write and not p.may_write(self.viewer):
                    raise StoreError(f"{self.viewer or 'nobody'} may not write in '{p.name}'")
                return p.store, rel
            if write:
                raise StoreError(f"case '{parts[1]}' not found in any stage")
        return self.home, rel

    # ------------------------------------------------------------------ layout
    def stages(self) -> list[str]:
        out = set(self.home.stages())
        for p in self.points:
            out.update(p.store.stages())
        return sorted(out)

    def cases(self, stage: str) -> list[str]:
        return sorted(c for c, at in self._where().items() if any(s == stage for _, s in at))

    def find(self, case_id: str) -> str | None:
        if "/" in case_id or case_id.startswith("."):
            raise StoreError(f"'{case_id}' is not a case name")
        at = self._located(case_id)
        return at[1] if at else None

    def case_dir(self, case_id: str) -> Path:
        at = self._located(case_id)
        if at is None:
            raise StoreError(f"case '{case_id}' not found in any stage")
        return at[0].store.root / at[1] / case_id

    def files(self, case_id: str) -> list[str]:
        return sorted(p.name for p in self.case_dir(case_id).iterdir() if p.is_file() and not p.name.startswith("."))

    def size(self, case_id: str, name: str) -> int:
        return (self.case_dir(case_id) / name).stat().st_size

    # ------------------------------------------------------------------ reading
    def read_text(self, rel: str) -> str:
        st, r = self._route(rel)
        return st.read_text(r)

    def read_json(self, rel: str) -> dict:
        st, r = self._route(rel)
        return st.read_json(r)

    def exists(self, rel: str) -> bool:
        st, r = self._route(rel)
        return st.exists(r)

    def case_text(self, case_id: str, name: str) -> str:
        return (self.case_dir(case_id) / name).read_text(encoding="utf-8")

    def case_json(self, case_id: str, name: str) -> dict:
        import json
        return json.loads(self.case_text(case_id, name))

    # ------------------------------------------------------------------ writing
    def write_atomic(self, rel: str, text: str) -> None:
        st, r = self._route(rel, write=True)
        st.write_atomic(r, text)

    def write_json(self, rel: str, doc: dict) -> None:
        st, r = self._route(rel, write=True)
        st.write_json(r, doc)

    def append(self, rel: str, text: str, head: str = "") -> None:
        st, r = self._route(rel, write=True)
        st.append(r, text, head)

    def put_file(self, case_id: str, name: str, src: Path) -> int:
        return self._writable(case_id).put_file(case_id, name, src)

    def put_bytes(self, case_id: str, name: str, data: bytes) -> int:
        return self._writable(case_id).put_bytes(case_id, name, data)

    def move(self, case_id: str, to_stage: str) -> tuple[str, str]:
        st = self._writable(case_id)
        if to_stage not in st.stages():
            (st.root / to_stage).mkdir(exist_ok=True)               # a data point may not hold every stage folder yet
            if st.write_root != st.root:
                (st.write_root / to_stage).mkdir(exist_ok=True)
        try:
            return st.move(case_id, to_stage)
        finally:
            self._forget()

    def mkcase(self, stage: str, case_id: str) -> Path:
        if self.everything.find(case_id) is not None:
            raise StoreError(f"'{case_id}' already exists")
        if not self.create_in:
            raise StoreError("no data point to start a case in")
        p = self.point(self.create_in)
        if not p.may_write(self.viewer):
            raise StoreError(f"{self.viewer or 'nobody'} may not write in '{p.name}'")
        (p.store.write_root / stage).mkdir(exist_ok=True)
        try:
            return p.store.mkcase(stage, case_id)
        finally:
            self._forget()

    def transfer(self, case_id: str, to_point: str) -> tuple[str, str]:
        """The case moves, folder and all, into another data point (share, REQ-005 PV-04): the viewer must be able to
        write both. Returns (from point, to point)."""
        src = self.point_of(case_id)
        if src is None:
            raise StoreError(f"case '{case_id}' not found in any stage")
        dst = self.point(to_point)
        if src.name == dst.name:
            raise StoreError(f"'{case_id}' is already in '{to_point}'")
        for p in (src, dst):
            if not p.may_write(self.viewer):
                raise StoreError(f"{self.viewer or 'nobody'} may not write in '{p.name}'")
        stage = src.store.find(case_id)
        target = dst.store.write_root / stage / case_id
        if target.exists():
            raise StoreError(f"'{case_id}' already exists in '{to_point}'")
        target.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.move(str(src.store.write_root / stage / case_id), str(target))
        self._forget()
        return src.name, dst.name

    # ------------------------------------------------------------------ journals and runs: the instance's
    def journals(self) -> list[str]:
        return self.home.journals()

    def runs(self) -> list[str]:
        return self.home.runs()

    @contextlib.contextmanager
    def lock(self, case_id: str):
        with self.home.lock(case_id):            # one lock per case id for the instance, wherever the case lies
            yield
