"""A helper's answer in a gate protocol (ADR-029 decision 5) — through the core, as the run's agent and nobody else.

    python -m casefile.cli.protocol <case-id> <template> start   --config <domain-dir>
    python -m casefile.cli.protocol <case-id> <template> answer  --config <domain-dir> --item ID (--yes | --no | --value V | --na)
                                                                   [--note TEXT] [--evidence E ...]
    python -m casefile.cli.protocol <case-id> <template> show    --config <domain-dir>

The pipeline root is COCKPIT_DATA_DIR; the agent is PRESSROOM_AGENT and must be a person of kind "agent". An agent decides
only items marked objective (`agent: true`); on every other item its answer is kept as an observation beside the item, and
the person decides. An agent never seals. Prints one JSON line; exit 0 when it went through, 1 when refused, 2 for a wrong call.
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
from ..domain import cases as reading
from ..domain import protocol as gate
from ..store import FsStore
from .step import _agent


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="casefile protocol", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case")
    p.add_argument("template")
    p.add_argument("op", choices=("start", "answer", "show"))
    p.add_argument("--config", required=True)
    p.add_argument("--item", default="")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--yes", action="store_true")
    g.add_argument("--no", action="store_true")
    g.add_argument("--value", default=None)
    g.add_argument("--na", action="store_true")
    p.add_argument("--note", default="")
    p.add_argument("--evidence", action="append", default=[])
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
    store = FsStore(root_path)
    try:
        if a.op == "start":
            print(json.dumps({"ok": True, "file": gate.start(store, config, a.case, a.template, by)}))
            return 0
        if a.op == "show":
            case = reading.load(store, config, a.case)
            doc = (case.data or {}).get(f"protocol-{a.template}.json")
            print(json.dumps({"ok": bool(doc), "items": [{k: i.get(k) for k in ("id", "type", "must", "agent", "criterion", "origin")}
                                                          for i in gate.live(doc)] if doc else [], "state": gate.state(doc) if doc else None},
                             ensure_ascii=False))
            return 0
        if not a.item:
            print("--item is required for answer", file=sys.stderr)
            return 2
        value = True if a.yes else False if a.no else a.value
        if isinstance(value, str):
            try:
                value = float(value) if re.fullmatch(r"-?\d+(\.\d+)?", value) else value
            except ValueError:
                pass
        run = os.environ.get("PRESSROOM_RUN_ID", "").strip() or "cli"
        digest = hashlib.sha1(json.dumps([a.case, a.template, a.item, value, a.na, a.note], sort_keys=True).encode()).hexdigest()[:8]
        step_id = re.sub(r"[^A-Za-z0-9_-]", "-", f"{run}"[-50:] + f"-pc-{a.item}-{digest}")[-80:]
        doc = gate.answer(store, config, a.case, a.template, by, a.item, step_id, value=value, na=a.na, note=a.note, evidence=a.evidence)
        decided = a.item in (doc.get("answers") or {}) and (doc["answers"][a.item].get("by") == by)
        print(json.dumps({"ok": True, "decided": decided, "observed": not decided, "state": gate.state(doc)}, ensure_ascii=False))
        return 0
    except (gate.ProtocolError, KeyError) as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
