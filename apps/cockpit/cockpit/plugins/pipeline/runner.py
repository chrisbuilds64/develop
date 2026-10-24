#!/usr/bin/env python3
"""The runner: takes queued skill runs from _runs/ and executes them in a headless agent session.

    runner.py --workspace ~/work --data ~/mnt/pressroom/flow [--claude /path/to/claude] [--once] [--interval 10]

What a run may do — where it may write, which tools, how long, the web or not —
comes from `run-policy.json` at the pipeline root, per skill. The runner carries
no rights of its own; without the policy it runs nothing.

Kind `claude-code`: the skill runs as `claude -p "/<skill> <container>"` in the
workspace — the same session type, the same skills and canon the person uses
at the keyboard, started by a file instead of a prompt. It runs on the person's
own machine with their own subscription, or as a service per stage on the
server; that is why the queue is a directory and not a service: the runner
may be off, and the order waits.

What the session knows beyond the skill: `--pull` refreshes the shared
checkouts (canon, control) before every run, so the rules are today's; the
order's stage, skill, container and orderer travel as PRESSROOM_* variables;
and `--context-script` (control/claude/hooks/runner-context.py) turns the
context manifest into a file that goes to the session as an appended system
prompt — the same files /session-start reads at the keyboard. That is how a
run from the button knows what a session at the keyboard knows. (A SessionStart
hook cannot carry it: Claude Code keeps hook output above a few kilobytes out
of the context, observed 2026-10-24.)

Claiming is a `mkdir` next to the order — atomic on a network mount, so two
runners never take the same job. The transcript goes to _runs/<id>.log, the
outcome back into the order file, and a review entry into the container.
"""
import argparse
import datetime as dt
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIND = "claude-code"
log = logging.getLogger("pressroom-runner")


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_policy(data: Path) -> dict | None:
    p = data / "run-policy.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def policy_for(policy: dict, skill: str) -> dict:
    """The skill's entry over the default — a skill lists only what differs."""
    return {**policy.get("default", {}), **policy.get("skills", {}).get(skill, {})}


WEB_TOOLS = ["WebFetch", "WebSearch"]


def accounting(data: dict) -> dict:
    """What the run cost, from Claude Code's JSON: dollars, the model that did the work, turns, seconds.

    Every order carries its own bill from here on. Without this the number existed for a moment
    on stdout and was gone; the one run of 2026-09-26 has no price for that reason.
    """
    out = {}
    if isinstance(data.get("total_cost_usd"), (int, float)):
        out["cost_usd"] = round(float(data["total_cost_usd"]), 4)
    models = data.get("modelUsage") or {}
    if isinstance(models, dict) and models:
        out["model"] = max(models, key=lambda m: float((models[m] or {}).get("costUSD", 0) or 0))
    if isinstance(data.get("num_turns"), int):
        out["turns"] = data["num_turns"]
    if isinstance(data.get("duration_ms"), (int, float)):
        out["duration_s"] = round(float(data["duration_ms"]) / 1000, 1)
    return out


def context_file(run: dict, env: dict, args) -> Path | None:
    """The operating context for this run, written by the context script into the workspace's tmp/.

    Returns None when there is no script or it fails — the run then goes on with CLAUDE.md and the canon,
    and the log says so. A missing context is a worse run, not a refused one.
    """
    script = args.context_script
    if not script or not script.is_file():
        return None
    out = args.workspace / "tmp" / f"run-context_{run['id']}.md"
    try:
        out.parent.mkdir(exist_ok=True)
        r = subprocess.run([sys.executable, str(script), "--plain"], cwd=args.workspace, env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("context script failed: %s", exc)
        return None
    if r.returncode != 0 or not r.stdout.strip():
        log.warning("context script returned %s: %s", r.returncode, (r.stderr or "").strip()[-200:])
        return None
    out.write_text(r.stdout, encoding="utf-8")
    first = r.stdout.splitlines()[:3]
    log.info("context: %s chars → %s (%s)", len(r.stdout), out.name, next((l for l in first if l.startswith("Domain")), "")[:80])
    return out


def command_for(run: dict, rules: dict, args, context: Path | None = None) -> list[str]:
    """The headless session, shaped by the policy: what it may write, which tools, how long.

    Every right the session gets is a line in run-policy.json — nothing here by default.
    """
    subst = {"{data}": str(args.data), "{container}": str(args.data / run["container"])}
    cmd = [args.claude, "-p", prompt_for(run, rules.get("agent", "the agent")), "--output-format", "json",
           "--permission-mode", rules.get("permission_mode", "acceptEdits")]
    if context:
        cmd += ["--append-system-prompt-file", str(context)]
    if rules.get("model"):
        cmd += ["--model", rules["model"]]                # the policy's choice per skill; without it, Claude Code's default
    for w in rules.get("write", []):
        cmd += ["--add-dir", subst.get(w, w)]           # writable beyond the workspace: named, per skill
    for d in args.add_dir:
        cmd += ["--add-dir", str(d)]                    # the shared checkouts (canon, control): the skills and rules the
                                                        # workspace links to resolve there, and a link outside is refused
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


def refresh(repos: list[Path]) -> None:
    """`git pull --ff-only` on the shared checkouts. A failure is logged and the run goes on with what is there:
    stale rules are a worse outcome than no run only when they are silently stale, and this is not silent."""
    for repo in repos:
        if not (repo / ".git").exists():
            log.warning("pull: %s is not a git checkout", repo)
            continue
        r = subprocess.run(["git", "-C", str(repo), "pull", "--ff-only", "--quiet"], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            log.warning("pull %s failed: %s", repo.name, (r.stderr or r.stdout).strip().splitlines()[-1:] or "?")
        else:
            head = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%h %s"], capture_output=True, text=True).stdout.strip()
            log.info("pull %s: %s", repo.name, head[:80])


def session_env(run: dict, rules: dict, args) -> dict:
    """What the headless session learns about its order, for the SessionStart hook and the skills."""
    return dict(os.environ,
                COCKPIT_DATA_DIR=str(args.data), CONTEXT_LOOP_DIR=str(args.data),
                PRESSROOM_ENV=os.environ.get("PRESSROOM_ENV", "local"),
                PRESSROOM_SKILL=str(run["skill"]), PRESSROOM_CONTAINER=str(run["container"]),
                PRESSROOM_ORDERED_BY=str(run.get("requested_by", "")), PRESSROOM_AGENT=str(rules.get("agent", "agent")),
                PRESSROOM_RUN_ID=str(run["id"]))


def billing_for(run: dict, env: dict, args) -> tuple[dict, str, str]:
    """The orderer's account decides how the run is billed: their subscription token when they brought one,
    the shared API key otherwise. Returns the environment, the mode, and one line for the log."""
    if not args.accounts:
        return env, "api-key", "shared API key (no accounts directory)"
    try:
        from cockpit.account import Accounts
    except ImportError:                                   # run from the source tree, outside the cockpit's interpreter
        sys.path.insert(0, str(HERE.parents[2]))
        from cockpit.account import Accounts
    b = Accounts(args.accounts).billing(str(run.get("requested_by", "")).lower(), env)
    return b.env, b.mode, b.source


def execute(f: Path, run: dict, rules: dict, args) -> None:
    queue = f.parent
    transcript = queue / (f.stem + ".log")
    if args.pull:
        refresh(args.pull)
    env = session_env(run, rules, args)
    env, billing, billed_by = billing_for(run, env, args)
    log.info("billing: %s", billed_by)
    context = context_file(run, env, args)
    cmd = command_for(run, rules, args, context)
    timeout = int(rules.get("timeout", 1800))
    with transcript.open("w", encoding="utf-8") as out:
        out.write(f"# {run['id']} — started {run['started']} by {run['taken_by']}\n$ {' '.join(cmd[:2])} … {' '.join(cmd[3:])}\n\n")
        out.flush()
        try:
            r = subprocess.run(cmd, cwd=args.workspace, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            code, stdout, stderr = r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = 124, (exc.stdout or ""), f"timed out after {timeout}s"
        result, session, spent = "", "", {}
        try:
            data = json.loads(stdout)
            result, session = str(data.get("result", "")), str(data.get("session_id", ""))
            spent = accounting(data)
        except Exception:
            result = stdout.strip()[-1500:]
        out.write(result + ("\n\n[stderr]\n" + stderr if stderr.strip() else "") + "\n")
    run.update(status="done" if code == 0 else "failed", finished=now(), exit=code, log=f"_runs/{transcript.name}",
               result=result.strip()[:4000], stage=env["PRESSROOM_ENV"], billing=billing)
    if session:
        run["session"] = session
    run.update(spent)
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
    p.add_argument("--pull", default="", help="comma-separated git checkouts to `pull --ff-only` before every run (canon, control)")
    p.add_argument("--log-level", default=os.environ.get("RUNNER_LOG_LEVEL", "INFO"))
    p.add_argument("--add-dir", action="append", default=[],
                   help="a directory the session may read beyond the workspace — the shared checkouts the workspace links to")
    p.add_argument("--accounts", default="", help="the cockpit's accounts directory — the orderer's token decides the billing; '' = always the shared key")
    p.add_argument("--context-script", default="control/claude/hooks/runner-context.py",
                   help="script (relative to the workspace) that prints the run's operating context; '' for none")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S", stream=sys.stdout)
    args.workspace = Path(args.workspace).expanduser().resolve()
    args.data = Path(args.data).expanduser().resolve()
    args.pull = [Path(x.strip()).expanduser() for x in args.pull.split(",") if x.strip()]
    args.add_dir = [Path(x).expanduser().resolve() for x in args.add_dir]
    args.accounts = Path(args.accounts).expanduser() if args.accounts else None
    args.context_script = (args.workspace / args.context_script) if args.context_script else None
    if args.context_script and not args.context_script.is_file():
        log.warning("no context script at %s — runs get CLAUDE.md and the canon only", args.context_script)
    queue = args.data / "_runs"
    stage = os.environ.get("PRESSROOM_ENV", "local")
    me = f"{os.environ.get('USER', 'runner')}@{socket.gethostname().split('.')[0]}/{stage}"
    log.info("runner %s (%s) — queue %s, workspace %s, %s%s", me, KIND, queue, args.workspace, platform.system(),
             f", pull {', '.join(p.name for p in args.pull)}" if args.pull else "")
    warned = False
    while True:
        policy = load_policy(args.data)                   # re-read every round: a changed line applies to the next run
        if policy is None:
            if not warned:
                log.error("no run-policy.json at %s — nothing runs without a declared policy", args.data)
                warned = True
            if args.once:
                return 1
            time.sleep(args.interval)
            continue
        if warned:
            log.info("run-policy.json found at %s — runs resume", args.data)
            warned = False
        queue.mkdir(exist_ok=True)
        job = take(queue, me)
        if job:
            f, run = job
            log.info("taking %s (by %s)", run["id"], run.get("requested_by", "?"))
            try:
                execute(f, run, policy_for(policy, run["skill"]), args)
            except Exception as exc:                      # the loop survives one broken order; the order records why
                log.exception("run %s crashed in the runner itself", run["id"])
                run.update(status="failed", finished=now(), exit=-1, result=f"runner error: {exc}")
                f.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log.info("%s %s (exit %s, %s turns, %s USD, %s s)", run["status"], run["id"], run.get("exit"),
                     run.get("turns", "?"), run.get("cost_usd", "?"), run.get("duration_s", "?"))
            continue
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
