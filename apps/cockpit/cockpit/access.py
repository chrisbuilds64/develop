"""The one place in the program that opens a file.

Grants come from the configuration. Nothing else in the cockpit touches the
file system — readers ask here, and here every request is checked against the
source's release list, the role's sensitivity ceiling and the source's root,
then recorded. A path that escapes its root through `..` or a symlink is
refused before anything is read.

Writing is not implemented. The cockpit shows what tools know; the tool that
owns a file is the only thing that changes it.
"""

from __future__ import annotations

import json
from pathlib import Path

from .audit import AuditLog
from .config import Config, Role, Source


class Denied(Exception):
    """Refused, with a reason an operator can read."""


class Missing(Denied):
    """Refused because the thing is not there — a gap in the setup, not a rule."""


def _released(src: Source, name: str) -> bool:
    """A name is released if the list is empty, names it, or names a folder above it."""
    if not src.include:
        return True
    name = name.strip("/")
    return any(name == inc.strip("/") or name.startswith(inc.strip("/") + "/") for inc in src.include)


class Access:
    def __init__(self, config: Config, audit: AuditLog, variables: dict | None = None):
        """`variables` fills placeholders in source paths — `{user.context}` for the signed-in user."""
        self._audit = audit
        self._vars = variables or {}
        self._config = config
        self._sources = {sid: self._bind(src) for sid, src in config.sources.items()}

    def _bind(self, src: Source) -> Source:
        text = str(src.path)
        if "{" not in text:
            return src
        for k, v in self._vars.items():
            text = text.replace("{" + k + "}", str(v))
        if "{" in text:
            return src          # unresolved placeholder: resolve() will report the path as missing
        import dataclasses
        return dataclasses.replace(src, path=self._config.bind_path(Path(text)))

    # ------------------------------------------------------------------ core
    def resolve(self, source_id: str, name: str, role: Role) -> Path:
        """Return a path inside a released source, or raise Denied.

        Order matters: the cheapest, most explicit checks first, the file
        system last — a refused request should not even touch the disk.
        """
        src = self._sources.get(source_id)
        if src is None:
            raise self._deny(role, source_id, name, f"source '{source_id}' is not defined")
        if not role.may_see(src.sensitivity):
            raise self._deny(role, source_id, name,
                             f"role '{role.id}' may not read '{src.sensitivity}' data")
        if not _released(src, name):
            raise self._deny(role, source_id, name, f"'{name}' is not released from '{source_id}'")
        if Path(name).is_absolute():
            raise self._deny(role, source_id, name, "absolute paths are not allowed")

        try:
            root = src.path.resolve(strict=True)
        except FileNotFoundError:
            raise self._deny(role, source_id, name, f"source '{source_id}' points nowhere: {src.path}", Missing)
        try:
            target = (root / name).resolve(strict=True)
        except FileNotFoundError:
            raise self._deny(role, source_id, name, f"'{name}' does not exist in '{source_id}'", Missing)
        if not target.is_relative_to(root):
            raise self._deny(role, source_id, name, f"'{name}' escapes '{source_id}'")

        self._audit.record(role.id, source_id, name, "read")
        return target

    # --------------------------------------------------------------- helpers
    def newest(self, source_id: str, role: Role, subdir: str = ".", depth: int = 2) -> float:
        """The latest modification time under a released directory, `depth` levels down.

        Directory mtimes change when entries come and go, file mtimes when
        content does — together they say when the data last moved. One audit
        line for the whole walk: it is a read of the listing, not of files.
        """
        src = self._sources.get(source_id)
        if src is None or not role.may_see(src.sensitivity):
            raise self._deny(role, source_id, subdir, f"role '{role.id}' may not read '{source_id}'")
        try:
            root = src.path.resolve(strict=True)
            where = (root / subdir).resolve(strict=True)
        except FileNotFoundError:
            raise self._deny(role, source_id, subdir, f"'{subdir}' does not exist in '{source_id}'", Missing)
        if not where.is_relative_to(root):
            raise self._deny(role, source_id, subdir, f"'{subdir}' escapes '{source_id}'")
        latest = where.stat().st_mtime
        frontier = [where]
        for _ in range(depth):
            nxt = []
            for d in frontier:
                for p in d.iterdir():
                    if p.name.startswith("."):
                        continue
                    try:
                        latest = max(latest, p.stat().st_mtime)
                    except OSError:
                        continue
                    if p.is_dir():
                        nxt.append(p)
            frontier = nxt
        self._audit.record(role.id, source_id, subdir, "stat")
        return latest

    def read_text(self, source_id: str, name: str, role: Role) -> str:
        return self.resolve(source_id, name, role).read_text(encoding="utf-8")

    def read_json(self, source_id: str, name: str, role: Role):
        return json.loads(self.read_text(source_id, name, role))

    def listdir(self, source_id: str, role: Role, subdir: str = ".") -> list[str]:
        """Names inside a released source, respecting the release list.

        With an `include` list, only listed names are returned even if more
        exist — the listing must not reveal what the release withholds.
        """
        src = self._sources.get(source_id)
        if src is None:
            raise self._deny(role, source_id, subdir, f"source '{source_id}' is not defined")
        if not role.may_see(src.sensitivity):
            raise self._deny(role, source_id, subdir,
                             f"role '{role.id}' may not read '{src.sensitivity}' data")
        if subdir != "." and not _released(src, subdir):
            raise self._deny(role, source_id, subdir, f"'{subdir}' is not released from '{source_id}'")
        try:
            root = src.path.resolve(strict=True)
            where = (root / subdir).resolve(strict=True)
        except FileNotFoundError:
            raise self._deny(role, source_id, subdir, f"'{subdir}' does not exist in '{source_id}'", Missing)
        if not where.is_relative_to(root):
            raise self._deny(role, source_id, subdir, f"'{subdir}' escapes '{source_id}'")
        prefix = "" if subdir == "." else subdir.rstrip("/") + "/"
        names = sorted(p.name for p in where.iterdir() if not p.name.startswith("."))
        if src.include:
            names = [n for n in names if _released(src, prefix + n)]
        self._audit.record(role.id, source_id, subdir, "list")
        return names

    def source(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    # ---------------------------------------------------------------- deny
    def _deny(self, role: Role, source_id: str, name: str, reason: str, kind=Denied) -> Denied:
        self._audit.record(role.id, source_id, name, "read", ok=False, reason=reason)
        return kind(reason)
