#!/usr/bin/env python3
"""The write guard of a helper run (REQ-001 A-05): a PreToolUse hook that lets a helper write in the case only the
files its action delivers (`produces` in the run order), their versions (`task.v2.md`) and the thread (`review.md`).

    write_guard.py <guard.json>        reads the tool call on stdin, prints the decision

The runner writes guard.json into the run's HOME (`install`): the container, the files, the policy's other write
directories and the pipeline root. Inside the container only the named files pass; elsewhere in the pipeline only what
a write directory covers; outside the pipeline the guard has no say (the permission mode decides, as before). Every
refusal is a line in the refusal log, so the runner can say in the thread which file was refused and why.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
THREAD = "review.md"
VERSION = re.compile(r"^(?P<stem>.+)\.v\d+(?P<ext>\.[^./]+)?$")


def unversioned(rel: str) -> str:
    """`task.v2.md` → `task.md`: a version is the file it versions (pressroom/CONTRIBUTING.md, rule 1)."""
    head, _, name = rel.rpartition("/")
    m = VERSION.match(name)
    if m:
        name = m.group("stem") + (m.group("ext") or "")
    return f"{head}/{name}" if head else name


def _inside(p: str, root: str) -> bool:
    return p == root or p.startswith(root.rstrip(os.sep) + os.sep)


def install(home: Path, run: dict, rules: dict, data: Path, python: str, here: Path) -> Path | None:
    """The guard for a run whose order names its deliveries: guard.json and the hook in the run's HOME settings.
    Returns the refusal log, or None when the order names none (nothing is guarded, as before)."""
    if not isinstance(run.get("produces"), list):
        return None
    container = data / run["container"]
    subst = {"{data}": str(data), "{container}": str(container)}
    dirs = [os.path.realpath(subst.get(w, w)) for w in rules.get("write", []) if w != "{container}"]
    files = [str(f) for f in run["produces"]]
    refused = home / ".claude" / "write-guard.refused.jsonl"
    guard = {"container": os.path.realpath(container), "data": os.path.realpath(data), "dirs": dirs,
             "files": files + [THREAD] if files else [], "log": str(refused)}
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    gfile = home / ".claude" / "write-guard.json"
    gfile.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    hook = {"type": "command", "command": " ".join(shlex.quote(x) for x in (python, str(here / "write_guard.py"), str(gfile)))}
    settings = {"hooks": {"PreToolUse": [{"matcher": "|".join(WRITE_TOOLS), "hooks": [hook]}]}}
    (home / ".claude" / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return refused


def decide(guard: dict, tool: str, inp: dict) -> str | None:
    """None when the write may happen, else the reason the helper reads."""
    if tool not in WRITE_TOOLS:
        return None
    path = inp.get("file_path") or inp.get("notebook_path")
    if not path:
        return None
    p = os.path.realpath(os.path.abspath(str(path)))
    if _inside(p, guard["container"]):
        rel = os.path.relpath(p, guard["container"]).replace(os.sep, "/")
        if unversioned(rel) in guard["files"]:
            return None
        if not guard["files"]:
            return (f"`{rel}` refused: this helper delivers no file — it reads and answers. Put the answer in your closing "
                    "text; the runner writes it into the thread.")
        named = ", ".join(f for f in guard["files"] if f != THREAD)
        return (f"`{rel}` refused: this action delivers {named} (and the thread, {THREAD}), nothing else in the case. "
                "Say in your closing text what else is needed; a person orders it.")
    if any(_inside(p, d) for d in guard["dirs"]):
        return None
    if _inside(p, guard["data"]):
        return f"`{os.path.relpath(p, guard['data'])}` refused: it is outside the case this helper was ordered for."
    return None


def main(argv: list[str]) -> int:
    guard = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    call = json.loads(sys.stdin.read() or "{}")
    tool, inp = str(call.get("tool_name", "")), call.get("tool_input") or {}
    why = decide(guard, tool, inp)
    if why is None:
        return 0
    try:
        with open(guard["log"], "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"tool": tool, "path": inp.get("file_path") or inp.get("notebook_path"), "why": why}) + "\n")
    except OSError:
        pass                                                  # the refusal holds even when it cannot be logged
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": why}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
