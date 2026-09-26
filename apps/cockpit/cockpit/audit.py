"""Access log: one JSON line per attempt, refused ones included.

Append-only, never rewritten. What is not in this file did not happen — the
same rule Gatehouse applies to model calls, applied here to file reads. A
refused access is recorded with its reason, because "who tried to see what"
is the question a rights concept will ask first.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Iterator


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def record(self, role: str, source: str, name: str, action: str,
               ok: bool = True, reason: str | None = None, ip: str | None = None) -> None:
        entry = {
            "ts": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "role": role,
            "source": source,
            "name": name,
            "action": action,
            "ok": ok,
        }
        if reason:
            entry["reason"] = reason
        if ip:
            entry["ip"] = ip
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def entries(self) -> Iterator[dict]:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)
