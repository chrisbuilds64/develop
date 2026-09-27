#!/usr/bin/env python3
"""Order a skill run on a container — the cockpit's button, the runner's job.

    run_request.py <stage/container> --skill interpret --by chris [--runner claude-code] [--note "…"]

Writes one file into _runs/ at the pipeline root, status queued, checked
against run.schema.json before it is written. Nothing runs here: a runner on
somebody's machine polls _runs/ and takes what is addressed to its kind. The
file is the order, the queue and, later, the record.

Works in COCKPIT_DATA_DIR (the pipeline root).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

try:
    from cockpit.schema import check as schema_check
except ImportError:                                   # run by hand from the source tree, outside the cockpit's interpreter
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from cockpit.schema import check as schema_check

STAGE = re.compile(r"^\d{2}-")


def load_schema(root: Path) -> dict | None:
    p = root / "run.schema.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def check(run: dict, schema: dict | None) -> list[str]:
    return schema_check(run, schema)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="run_request.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container"); p.add_argument("--skill", required=True); p.add_argument("--by", required=True)
    p.add_argument("--runner", default="claude-code"); p.add_argument("--note", default="")
    a = p.parse_args(argv)

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = a.container.strip().strip("/").split("/")[-1]
    stages = sorted(x.name for x in root.iterdir() if x.is_dir() and STAGE.match(x.name))
    here = [s for s in stages if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else "exists in more than one stage"))

    now = dt.datetime.now().astimezone()
    run = {
        "id": f"{now.strftime('%Y%m%d-%H%M%S')}_{a.skill.strip()}_{name}",
        "skill": a.skill.strip(), "container": f"{here[0]}/{name}",
        "requested_by": a.by.strip(), "runner": a.runner.strip(),
        "status": "queued", "created": now.isoformat(timespec="seconds"),
    }
    if a.note.strip():
        run["note"] = a.note.strip()
    problems = check(run, load_schema(root))
    if problems:
        sys.exit("refused — " + "; ".join(problems))

    queue = root / "_runs"
    queue.mkdir(exist_ok=True)
    target = queue / f"{run['id']}.json"
    if target.exists():
        sys.exit(f"{target.name} already exists")
    target.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    waiting = sum(1 for f in queue.glob("*.json") if json.loads(f.read_text(encoding="utf-8")).get("status") == "queued")
    print(f"queued {run['id']} for a {run['runner']} runner — {waiting} waiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
