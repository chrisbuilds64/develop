#!/usr/bin/env python3
"""Append one entry to a container's review.md — append only, never rewrite.

    review_append.py <container> --by <name>          text on stdin

The entry gets a heading with the date, the author and the stage the container
is in, so a reader two months later knows who said it and where the piece
stood. Existing text is never touched: the tool opens the file for appending
and writes at the end. If review.md does not exist, it is created with a title.

Works in COCKPIT_DATA_DIR (the pipeline root).
"""
import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

STAGE = re.compile(r"^\d{2}-")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="review_append.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container"); p.add_argument("--by", required=True)
    a = p.parse_args(argv)
    text = sys.stdin.read().strip()
    if not text:
        sys.exit("nothing to append")
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = a.container.strip().strip("/").split("/")[-1]  # "stage/name" from the surface, "name" from the shell
    if not name or name.startswith("."):
        sys.exit(f"'{name}' is not a container name")
    here = [s for s in sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name)) if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else f"exists in more than one stage: {', '.join(here)}"))
    target = root / here[0] / name / "review.md"
    stamp = dt.datetime.now().astimezone()
    if not target.exists():
        target.write_text(f"# Review — {name}\n\n*Append only. Newest at the bottom, never edited afterwards.*\n", encoding="utf-8")
    block = (f"\n---\n\n## {stamp.strftime('%Y-%m-%d %H:%M')} — {a.by} · in `{here[0]}`\n\n{text}\n")
    with target.open("a", encoding="utf-8") as fh:
        fh.write(block)
    print(f"appended to {here[0]}/{name}/review.md — {len(text)} chars by {a.by}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
