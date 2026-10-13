#!/usr/bin/env python3
"""Ask the agent to work on a piece: one review entry addressed to it, and one run order with the same words.

    ask_agent.py <stage/container> --by chris --role operator --title "…" [--skill interpret] < text

The entry is the record (who asked what, when), the order is the work. The skill is the policy's
agent's job on this piece: /derive when the piece begins with finished material in 10-ideas,
/interpret otherwise — or the one named. Both halves go through the tools that own the files
(review_append.py, run_request.py); nothing is written here.

Works in COCKPIT_DATA_DIR (the pipeline root).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = re.compile(r"^\d{2}-")
PRIMARY = ("script.md", "substack.md", "linkedin-post.txt")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ask_agent.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container"); p.add_argument("--by", required=True); p.add_argument("--role", required=True)
    p.add_argument("--title", required=True); p.add_argument("--skill", default="")
    a = p.parse_args(argv)
    text = sys.stdin.read().strip()
    if not text:
        sys.exit("say what the agent should do — the text is empty")
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = a.container.strip().strip("/").split("/")[-1]
    stages = sorted(x.name for x in root.iterdir() if x.is_dir() and STAGE.match(x.name))
    here = [s for s in stages if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else "exists in more than one stage"))
    stage = here[0]
    policy = json.loads((root / "run-policy.json").read_text(encoding="utf-8")) if (root / "run-policy.json").exists() else {}
    agent = policy.get("default", {}).get("agent", "Axel")
    skill = a.skill.strip()
    if not skill:
        has_primary = any((root / stage / name / f).exists() or list((root / stage / name).glob(f.rsplit(".", 1)[0] + ".v*." + f.rsplit(".", 1)[1])) for f in PRIMARY)
        skill = "derive" if stage == "10-ideas" and has_primary else "interpret"
    env = dict(os.environ, COCKPIT_DATA_DIR=str(root))
    r = subprocess.run([sys.executable, str(HERE / "review_append.py"), f"{stage}/{name}", "--by", a.by, "--title", a.title,
                        "--status", "open", "--for", agent], input=text, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit((r.stdout + r.stderr).strip())
    entry = r.stdout.split()[0] if r.stdout else "REV-?"
    r2 = subprocess.run([sys.executable, str(HERE / "run_request.py"), f"{stage}/{name}", "--skill", skill, "--by", a.by, "--role", a.role,
                         "--note", f"{entry} — {a.title}: {text}"], capture_output=True, text=True, env=env)
    if r2.returncode != 0:
        print(f"{entry} appended, but the order was refused: {(r2.stdout + r2.stderr).strip()}")
        return 1
    print(f"{entry} appended for {agent}, /{skill} {r2.stdout.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
