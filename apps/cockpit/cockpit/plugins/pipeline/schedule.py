#!/usr/bin/env python3
"""Put a piece on a day: writes publishDate into its meta.json.

    schedule.py <stage/container> <YYYY-MM-DD>

publishDate is the one date — planned while the piece stands before 60-published,
actual from there on. So this tool refuses a piece that is already published (the
date is a record then, not a plan), refuses a day another piece already holds when
calendar.json says one_per_day, and says so when the day is not one of the slots —
but does not refuse it: the rhythm is a guideline, not a contract.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

STAGE = re.compile(r"^(\d{2})-")


def load_calendar(root: Path) -> dict:
    p = root / "calendar.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def dated(root: Path, stages: list[str]) -> list[tuple[str, str, str]]:
    """(date, stage, name) for every piece with a publishDate."""
    out = []
    for s in stages:
        for d in sorted((root / s).iterdir()):
            m = d / "meta.json"
            if d.is_dir() and m.is_file():
                try:
                    v = json.loads(m.read_text(encoding="utf-8")).get("publishDate")
                except Exception:
                    continue
                if v:
                    out.append((str(v)[:10], s, d.name))
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        sys.exit(__doc__)
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = argv[0].strip().strip("/").split("/")[-1]
    day = argv[1].strip()
    try:
        when = dt.date.fromisoformat(day)
    except ValueError:
        sys.exit(f"'{day}' is not a date — YYYY-MM-DD")
    stages = sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name))
    here = [s for s in stages if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else "exists in more than one stage"))
    stage = here[0]
    if int(STAGE.match(stage).group(1)) >= 60:
        sys.exit(f"{name} stands in {stage} — its date is a record now, not a plan")
    cal = load_calendar(root)
    if cal.get("one_per_day", True):
        taken = [(s, n) for d, s, n in dated(root, stages) if d == day and n != name]
        if taken:
            sys.exit(f"{day} already has {taken[0][1]} ({taken[0][0]}) — one piece per day")
    m = root / stage / name / "meta.json"
    meta = json.loads(m.read_text(encoding="utf-8")) if m.is_file() else {}
    before = meta.get("publishDate")
    meta["publishDate"] = day
    meta.pop("scheduled", None)
    m.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    slots = cal.get("slots", [])
    weekday = when.strftime("%a")
    note = "" if not slots or weekday in slots else f" — note: {weekday} is not a slot ({', '.join(slots)})"
    print(f"{name} planned for {day} ({weekday})" + (f", was {before}" if before else "") + note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
