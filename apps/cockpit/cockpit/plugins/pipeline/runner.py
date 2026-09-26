#!/usr/bin/env python3
"""The runner: takes queued skill runs from _runs/ and executes them in a headless agent session.

    runner.py --workspace ~/work --data ~/fundus/flow [--claude /path/to/claude] [--once] [--interval 10]

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


def prompt_for(run: dict) -> str:
    head = ("You are Axel, in a PressRoom session started by a run order from the cockpit — no conversation, "
            f"one task. Work on the container `{run['container']}` and nothing else. Write review entries and "
            "your closing summary in English: review.md is read by people who do not read German. When done, "
            "say in five lines what you changed and what is open.\n\n")
    line = f"/{run['skill']} {run['container'].split('/')[-1]}"
    if run.get("note"):
        line += f"\n\n{run['note']}"
    return head + line


def execute(f: Path, run: dict, args) -> None:
    queue = f.parent
    log = queue / (f.stem + ".log")
    cmd = [args.claude, "-p", prompt_for(run), "--output-format", "json", "--permission-mode", args.permission_mode,
           "--add-dir", str(args.data)]                    # the fundus is outside the workspace; Write/Edit need it named
    if args.allowed_tools:
        cmd += ["--allowedTools", args.allowed_tools]
    env = dict(os.environ, COCKPIT_DATA_DIR=str(args.data), CONTEXT_LOOP_DIR=str(args.data))
    with log.open("w", encoding="utf-8") as out:
        out.write(f"# {run['id']} — started {run['started']} by {run['taken_by']}\n$ {' '.join(cmd[:2])} … {' '.join(cmd[3:])}\n\n")
        out.flush()
        try:
            r = subprocess.run(cmd, cwd=args.workspace, env=env, capture_output=True, text=True, timeout=args.timeout, stdin=subprocess.DEVNULL)
            code, stdout, stderr = r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = 124, (exc.stdout or ""), f"timed out after {args.timeout}s"
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
    subprocess.run([sys.executable, str(HERE / "review_append.py"), run["container"], "--by", "Axel", "--title", title,
                    "--status", "info"], input=text, capture_output=True, text=True, env=env)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="runner.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", required=True, help="where the skills and CLAUDE.md live — the session's cwd")
    p.add_argument("--data", required=True, help="the pipeline root with _runs/")
    p.add_argument("--claude", default=os.environ.get("CLAUDE_BIN", "claude"))
    p.add_argument("--permission-mode", default="acceptEdits")
    p.add_argument("--allowed-tools", default="Bash(python3:*),Bash(git:*),Bash(mv:*),Bash(mkdir:*),Bash(cp:*),Bash(ls:*),Bash(cat:*),WebFetch,WebSearch")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--interval", type=int, default=10)
    p.add_argument("--once", action="store_true", help="process what is queued, then exit")
    args = p.parse_args(argv)
    args.workspace = Path(args.workspace).expanduser().resolve()
    args.data = Path(args.data).expanduser().resolve()
    queue = args.data / "_runs"
    me = f"{os.environ.get('USER', 'runner')}@{socket.gethostname().split('.')[0]}"
    print(f"runner {me} ({KIND}) — queue {queue}, workspace {args.workspace}, {platform.system()}")
    while True:
        queue.mkdir(exist_ok=True)
        job = take(queue, me)
        if job:
            f, run = job
            print(f"{now()} taking {run['id']}")
            execute(f, run, args)
            print(f"{now()} {run['status']} {run['id']} (exit {run.get('exit')})")
            continue
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
