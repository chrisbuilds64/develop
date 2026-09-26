#!/usr/bin/env python3
"""Move a container to another stage — the PressRoom move, as a tool.

    move.py <container> <to-stage>

Works in the directory named by COCKPIT_DATA_DIR (the pipeline root). Finds the
container in whatever stage it is in, refuses if the target stage does not
exist, if a container of that name is already there, or if it is already in
the target. Prints one line saying what moved from where to where. The stage
folder is the status; nothing inside the container is touched.
"""
import os
import re
import sys
from pathlib import Path

STAGE = re.compile(r"^\d{2}-")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        sys.exit(__doc__)
    name, to_stage = argv[0].strip().strip("/"), argv[1].strip().strip("/")
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    if "/" in name or name.startswith("."):
        sys.exit(f"'{name}' is not a container name")
    stages = sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name))
    if to_stage not in stages:
        sys.exit(f"stage '{to_stage}' does not exist — one of: {', '.join(stages)}")
    here = [s for s in stages if (root / s / name).is_dir()]
    if not here:
        sys.exit(f"container '{name}' not found in any stage")
    if len(here) > 1:
        sys.exit(f"container '{name}' exists in more than one stage: {', '.join(here)} — fix that by hand first")
    src = root / here[0] / name
    dst = root / to_stage / name
    if src == dst:
        sys.exit(f"'{name}' is already in {to_stage}")
    if dst.exists():
        sys.exit(f"{to_stage}/{name} already exists — nothing overwritten")
    src.rename(dst)
    print(f"moved {name}: {here[0]} → {to_stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
