#!/usr/bin/env python3
"""The runner: takes queued skill runs from _runs/ and executes them in a headless agent session.

    runner.py --workspace ~/work --data ~/mnt/pressroom/flow [--claude /path/to/claude] [--once] [--interval 10]

What a run may do — where it may write, which tools, how long, the web or not —
comes from `run-policy.json` at the pipeline root, per skill. The runner carries
no rights of its own; without the policy it runs nothing.

Kind `claude-code`: the skill runs as `claude -p "/<skill> <container>"` in the
workspace — the same session type, the same skills and canon the person uses
at the keyboard, started by a file instead of a prompt. It runs on the person's
own machine with their own subscription; that is why the queue is a directory
and not a service: the runner may be off, and the order waits.

Claiming is a `mkdir` next to the order — atomic on a network mount, so two
runners never take the same job. The transcript goes to _runs/<id>.log, the
outcome back into the order file, and a review entry into the container.
"""
import argparse
import datetime as dt
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIND = "claude-code"


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_policy(data: Path) -> dict | None:
    p = data / "run-policy.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def policy_for(policy: dict, skill: str) -> dict:
    """The skill's entry over the default — a skill lists only what differs."""
    return {**policy.get("default", {}), **policy.get("skills", {}).get(skill, {})}


WEB_TOOLS = ["WebFetch", "WebSearch"]


def command_for(run: dict, rules: dict, args) -> list[str]:
    """The headless session, shaped by the policy: what it may write, which tools, how long.

    Every right the session gets is a line in run-policy.json — nothing here by default.
    """
    subst = {"{data}": str(args.data), "{container}": str(args.data / run["container"])}
    cmd = [args.claude, "-p", prompt_for(run, rules.get("agent", "the agent")), "--output-format", "json",
           "--permission-mode", rules.get("permission_mode", "acceptEdits")]
    for w in rules.get("write", []):
        cmd += ["--add-dir", subst.get(w, w)]           # writable beyond the workspace: named, per skill
    tools = list(rules.get("tools", [])) + (WEB_TOOLS if rules.get("web") else [])
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    return cmd


def take(queue: Path, me: str) -> tuple[Path, dict] | None:
    for f in sorted(queue.glob("*.json")):
        try:
            run = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if run.get("status") != "queued" or run.get("runner") != KIND:
            continue
        try:
            (queue / (f.stem + ".claim")).mkdir()          # the lock: exists → somebody else has it
        except FileExistsError:
            continue
        run.update(status="running", started=now(), taken_by=me)
        f.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return f, run
    return None


def prompt_for(run: dict, agent: str) -> str:
    head = (f"You are {agent}, in a PressRoom session started by a run order from the cockpit — no conversation, "
            f"one task. Work on the container `{run['container']}` and nothing else. Write review entries and "
            "your closing summary in English: review.md is read by people who do not read German. A review "
            "entry's For names one person from people.json, never two. When done, say in five lines what you "
            "changed and what is open.\n\n")
    line = f"/{run['skill']} {run['container'].split('/')[-1]}"
    if run.get("note"):
        line += f"\n\n{run['note']}"
    return head + line


def execute(f: Path, run: dict, rules: dict, args) -> None:
    queue = f.parent
    log = queue / (f.stem + ".log")
    cmd = command_for(run, rules, args)
    timeout = int(rules.get("timeout", 1800))
    env = dict(os.environ, COCKPIT_DATA_DIR=str(args.data), CONTEXT_LOOP_DIR=str(args.data))
    with log.open("w", encoding="utf-8") as out:
        out.write(f"# {run['id']} — started {run['started']} by {run['taken_by']}\n$ {' '.join(cmd[:2])} … {' '.join(cmd[3:])}\n\n")
        out.flush()
        try:
            r = subprocess.run(cmd, cwd=args.workspace, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            code, stdout, stderr = r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = 124, (exc.stdout or ""), f"timed out after {timeout}s"
        result, session = "", ""
        try:
            data = json.loads(stdout)
            result, session = str(data.get("result", "")), str(data.get("session_id", ""))
        except Exception:
            result = stdout.strip()[-1500:]
        out.write(result + ("\n\n[stderr]\n" + stderr if stderr.strip() else "") + "\n")
    run.update(status="done" if code == 0 else "failed", finished=now(), exit=code, log=f"_runs/{log.name}",
               result=result.strip()[:4000])
    if session:
        run["session"] = session
    f.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # The record in the container: one review entry, info, in the runner's own words.
    title = f"Run /{run['skill']}: {'done' if code == 0 else 'failed'}"
    body = (result.strip() or "(no output)")
    text = (body[:1800] + (" …" if len(body) > 1800 else "")) + f"\n\n*Run {run['id']}, transcript in `{run['log']}`.*"
    subprocess.run([sys.executable, str(HERE / "review_append.py"), run["container"], "--by", rules.get("agent", "agent"), "--title", title,
                    "--status", "info"], input=text, capture_output=True, text=True, env=env)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="runner.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", required=True, help="where the skills and CLAUDE.md live — the session's cwd")
    p.add_argument("--data", required=True, help="the pipeline root with _runs/")
    p.add_argument("--claude", default=os.environ.get("CLAUDE_BIN", "claude"))
    p.add_argument("--interval", type=int, default=10)
    p.add_argument("--once", action="store_true", help="process what is queued, then exit")
    args = p.parse_args(argv)
    args.workspace = Path(args.workspace).expanduser().resolve()
    args.data = Path(args.data).expanduser().resolve()
    queue = args.data / "_runs"
    me = f"{os.environ.get('USER', 'runner')}@{socket.gethostname().split('.')[0]}"
    print(f"runner {me} ({KIND}) — queue {queue}, workspace {args.workspace}, {platform.system()}")
    while True:
        policy = load_policy(args.data)                   # re-read every round: a changed line applies to the next run
        if policy is None:
            print(f"{now()} no run-policy.json at {args.data} — nothing runs without a declared policy")
            if args.once:
                return 1
            time.sleep(args.interval)
            continue
        queue.mkdir(exist_ok=True)
        job = take(queue, me)
        if job:
            f, run = job
            print(f"{now()} taking {run['id']}")
            execute(f, run, policy_for(policy, run["skill"]), args)
            print(f"{now()} {run['status']} {run['id']} (exit {run.get('exit')})")
            continue
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
