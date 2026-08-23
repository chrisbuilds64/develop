"""Model traffic log.

Every outbound call is written here before it is sent, so a call that
fails still leaves a record of what left the machine. The log lives in
the instance directory next to the answers: it is client material and
inherits the same protection.

One append-only JSONL file. Readable with any text editor, diffable
under version control, and impossible to silently rewrite.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, instance_path: Path) -> None:
        self._path = instance_path / "audit.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def record(self, **fields: Any) -> None:
        entry = {"at": datetime.now(timezone.utc).isoformat(), **fields}
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def entries(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
