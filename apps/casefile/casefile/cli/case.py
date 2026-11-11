"""An agent opens a case — through the core, under its own name, the same way the surface does (REQ-001 C-10).

    python -m casefile.cli.case new --config <domain-dir> --title TEXT [--description TEXT | --description-file F]
                                    [--attach FILE ...] [--label L] [--value FIELD=KEY ...] [--step-id ID]

The pipeline root is COCKPIT_DATA_DIR; the agent is PRESSROOM_AGENT and must be a person of kind "agent" holding a role
the application lets open cases (`theme.create.roles`). Prints one JSON line with the case id and its stage; exit 0 when
it went through, 1 when refused, 2 for a wrong call. The same step id twice opens nothing new.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from ..config import DomainConfig
from ..domain import opening
from ..store import FsStore
from .step import _agent


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="casefile case", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("op", choices=("new",))
    p.add_argument("--config", required=True)
    p.add_argument("--title", required=True)
    d = p.add_mutually_exclusive_group()
    d.add_argument("--description", default="")
    d.add_argument("--description-file", default="")
    p.add_argument("--attach", action="append", default=[])
    p.add_argument("--label", default=None)
    p.add_argument("--value", action="append", default=[], help="FIELD=KEY, for the fields and lists a new case asks for")
    p.add_argument("--step-id", default="")
    a = p.parse_args(argv)

    root = os.environ.get("COCKPIT_DATA_DIR", "").strip()
    if not root:
        print("COCKPIT_DATA_DIR is not set", file=sys.stderr)
        return 2
    config = DomainConfig.load(Path(a.config), Path(root))
    try:
        by = _agent(config)
    except SystemExit as refusal:
        print(str(refusal), file=sys.stderr)
        return 2
    text = Path(a.description_file).read_text(encoding="utf-8") if a.description_file else a.description
    attached = [(Path(f).name, Path(f).read_bytes()) for f in a.attach]
    values = dict(v.split("=", 1) for v in a.value if "=" in v)
    step_id = a.step_id or ("cli-new-" + hashlib.sha1(json.dumps([by, a.title, text], sort_keys=True).encode()).hexdigest()[:12])
    try:
        cid, stage = opening.open_case(FsStore(Path(root)), config, by, a.title, step_id, label=a.label, values=values,
                                       description=text, attached=attached)
    except (opening.NotHere, opening.Refused) as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "case": cid, "stage": stage}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
