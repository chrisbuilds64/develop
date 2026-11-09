"""One step on a case, from a helper's run — through the core, like every other writer (ADR-013, ADR-027).

    python -m casefile.cli.step <case-id> <action> --config <domain-dir> [--file F ...] [--note TEXT] [--text TEXT]

The pipeline root is COCKPIT_DATA_DIR, which the runner sets for every run. The step is made as the run's agent
(PRESSROOM_AGENT) and as nobody else: the name must be a person of kind "agent" in the domain's people, so a helper
can never step for a person — a gate held by a person stays with that person. The step id is the run's id, the
action and what it carries, so the same run asking twice for the same thing changes nothing (C-03).

Prints the outcome as one JSON line; exit 0 when the step went through, 1 when it was refused, 2 for a wrong call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from ..config import DomainConfig
from ..domain import step as stepping
from ..models import StepRequest
from ..store import FsStore


def _agent(config: DomainConfig) -> str:
    name = os.environ.get("PRESSROOM_AGENT", "").strip()
    if not name:
        raise SystemExit("PRESSROOM_AGENT is not set: a step from the command line is a helper's step, made in its run")
    match = next((p for p in config.people if name.lower() in (p.id.lower(), p.name.lower())), None)
    if match is None:
        raise SystemExit(f"'{name}' is not a person of this domain")
    if match.kind != "agent":
        raise SystemExit(f"'{match.id}' is a person, not an agent: a person's steps are made by that person, in the surface")
    return match.id


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="casefile step", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case")
    p.add_argument("action")
    p.add_argument("--config", required=True, help="the domain's configuration directory")
    p.add_argument("--file", action="append", default=[], help="a file in the case, delivered with this step (repeatable)")
    p.add_argument("--note", default="", help="the reason, for an action that asks for one")
    p.add_argument("--text", default="", help="the text of a note or a delivery")
    p.add_argument("--title", default="")
    p.add_argument("--for", dest="for_", default="", help="the person a note is for (their move until they answer)")
    a = p.parse_args(argv)

    root = os.environ.get("COCKPIT_DATA_DIR", "").strip()
    if not root:
        print("COCKPIT_DATA_DIR is not set", file=sys.stderr)
        return 2
    root_path = Path(root)
    config = DomainConfig.load(Path(a.config), root_path)
    try:
        by = _agent(config)
    except SystemExit as refusal:
        print(str(refusal), file=sys.stderr)
        return 2

    payload: dict = {}
    if a.file:
        payload["files"] = a.file
    if a.note:
        payload["note"] = a.note
    if a.text:
        payload["text"] = a.text
    if a.title:
        payload["title"] = a.title
    if a.for_:
        payload["for"] = a.for_
    run = os.environ.get("PRESSROOM_RUN_ID", "").strip() or "cli"
    digest = hashlib.sha1(json.dumps([a.case, a.action, payload], sort_keys=True).encode()).hexdigest()[:8]
    step_id = re.sub(r"[^A-Za-z0-9_-]", "-", f"{run}"[-60:] + f"-{a.action}-{digest}")[-80:]
    result = stepping.step(FsStore(root_path), config, a.case, StepRequest(action=a.action, step_id=step_id, payload=payload), by)
    print(json.dumps(result.model_dump(by_alias=True), ensure_ascii=False))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
