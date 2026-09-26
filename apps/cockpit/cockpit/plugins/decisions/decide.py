#!/usr/bin/env python3
"""Append one decision to decisions.md — the plugin's own tool.

    decide.py "<what>" --why "<reason>" [--instead "<rejected alternative>"]

Writes into the directory named by COCKPIT_DATA_DIR (the cockpit sets it to
the signed-in user's context), or the current directory. Appends only; it
never edits an existing entry, because the file's own rule says so.
"""
import argparse
import datetime as dt
import os
import sys
from pathlib import Path

HEADER = """# Decisions

*One entry per decision, newest at the bottom, never edited afterwards.*

---
"""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="decide.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("what"); p.add_argument("--why", required=True); p.add_argument("--instead", default="")
    p.add_argument("--date", default=dt.date.today().isoformat())
    a = p.parse_args(argv)
    if not a.what.strip() or not a.why.strip():
        sys.exit("a decision needs a what and a why")
    target = Path(os.environ.get("COCKPIT_DATA_DIR") or os.environ.get("CONTEXT_LOOP_DIR") or ".") / "decisions.md"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(HEADER, encoding="utf-8")
    entry = f"\n## {a.date} — {a.what.strip()}\n**Why:** {a.why.strip()}\n"
    if a.instead.strip():
        entry += f"**Instead of:** {a.instead.strip()}\n"
    with target.open("a", encoding="utf-8") as fh:
        fh.write(entry)
    print(f"recorded: {a.date} — {a.what.strip()}  →  {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
