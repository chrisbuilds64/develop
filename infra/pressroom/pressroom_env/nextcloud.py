"""Nextcloud team folders through occ — the storage adapter.

A stage's data is a team folder. This module knows how to list, create, share and rescan one, and
where its files sit on the disk. Nothing else in the tool speaks occ; if the storage changes
(another Nextcloud, a plain directory), this is the file that changes.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .config import OpsError, Server
from .shell import run

log = logging.getLogger("pressroom-env")


class TeamFolders:
    def __init__(self, server: Server):
        self.s = server

    def _occ(self, *args: str, check: bool = True):
        return run([self.s.php, str(self.s.occ), *args], user=self.s.nextcloud_user, check=check)

    def list(self) -> dict[str, int]:
        """{name: id} of every team folder."""
        r = self._occ("groupfolders:list", "--output=json", check=False)
        if r.returncode == 0:
            try:
                data = json.loads(r.stdout)
                items = data.values() if isinstance(data, dict) else data
                return {str(x["mount_point"]): int(x["id"]) for x in items}
            except (ValueError, KeyError, TypeError):
                pass
        # the table form: | id | name | groups | …
        r = self._occ("groupfolders:list")
        out: dict[str, int] = {}
        for line in r.stdout.splitlines():
            m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", line)
            if m:
                out[m.group(2)] = int(m.group(1))
        return out

    def create(self, name: str) -> int:
        """Create the team folder and give the group full rights. Returns the id."""
        existing = self.list()
        if name in existing:
            log.info("team folder %s exists (id %d)", name, existing[name])
            return existing[name]
        r = self._occ("groupfolders:create", name)
        m = re.search(r"\d+", r.stdout)
        if not m:
            raise OpsError(f"groupfolders:create printed no id: {r.stdout.strip()!r}")
        fid = int(m.group())
        self._occ("groupfolders:group", str(fid), self.s.nextcloud_group, "write", "share", "delete")
        log.info("team folder %s created (id %d), group %s", name, fid, self.s.nextcloud_group)
        return fid

    def scan(self, fid: int) -> None:
        """Tell Nextcloud about files that arrived on the disk behind its back."""
        self._occ("groupfolders:scan", str(fid))

    def files(self, fid: int) -> Path:
        """Where the folder's files sit on the disk."""
        return self.s.groupfolders_data / str(fid) / "files"

    def dav_url(self, name: str) -> str:
        return f"{self.s.dav_base}/{name}"
