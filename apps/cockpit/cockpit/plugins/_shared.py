"""One reader per module, each about thirty lines.

A reader turns what a tool leaves on disk into a panel. It reads only through
the access layer, never opens a path of its own, and reports `as_of` as the
time of the data — a file's modification time, a timestamp inside it — not
the time of reading. That is what makes the staleness check mean something.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path


def mtime_iso(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> dt.date:
    return dt.date.today()
