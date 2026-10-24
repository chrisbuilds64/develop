#!/usr/bin/env python3
"""The runner: takes queued skill runs from _runs/ and executes them in a headless agent session.

    runner.py --workspace ~/work --data ~/mnt/pressroom/flow [--claude /path/to/claude] [--once] [--interval 10]
    runner.py --workspace ~/work --workspaces /path/to/workspaces.json …      every workspace's queue, one runner

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
import shutil
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


def context_file(run: dict, env: dict, args, ws: Path) -> Path | None:
    """The operating context for this run, written by the context script into the run's workspace tmp/.

    Returns None when there is no script or it fails — the run then goes on with CLAUDE.md and the canon,
    and the log says so. A missing context is a worse run, not a refused one.
    """
    script = args.context_script
    if not script or not script.is_file():
        return None
    out = ws / "tmp" / f"run-context_{run['id']}.md"
    try:
        out.parent.mkdir(exist_ok=True)
        r = subprocess.run([sys.executable, str(script), "--plain"], cwd=ws, env=env, capture_output=True, text=True, timeout=60)
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


def command_for(run: dict, rules: dict, args, data: Path, context: Path | None = None) -> list[str]:
    """The headless session, shaped by the policy: what it may write, which tools, how long.

    Every right the session gets is a line in run-policy.json — nothing here by default.
    """
    subst = {"{data}": str(data), "{container}": str(data / run["container"])}
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


def session_env(run: dict, rules: dict, args, data: Path, workspace_id: str, home: Path | None) -> dict:
    """What the headless session learns about its order, for the context script and the skills."""
    return dict(os.environ,
                **({"HOME": str(home)} if home else {}),
                COCKPIT_DATA_DIR=str(data), CONTEXT_LOOP_DIR=str(data),
                PRESSROOM_WORKSPACE=workspace_id,
                PRESSROOM_ENV=os.environ.get("PRESSROOM_ENV", "local"),
                PRESSROOM_SKILL=str(run["skill"]), PRESSROOM_CONTAINER=str(run["container"]),
                PRESSROOM_ORDERED_BY=str(run.get("requested_by", "")), PRESSROOM_AGENT=str(rules.get("agent", "agent")),
                PRESSROOM_RUN_ID=str(run["id"]))


def billing_for(run: dict, rules: dict, env: dict, args) -> tuple[dict, str, str]:
    """The orderer's account decides how the run is billed: their subscription token or their own API key.
    Nothing of their own and no `shared_billing: true` in the policy → mode "none", and the run does not start.
    Returns the environment, the mode, and one line for the log."""
    allow_shared = bool(rules.get("shared_billing", False))
    if not args.accounts:
        if allow_shared:
            return env, "api-key", "shared API key (no accounts directory, allowed by policy)"
        return {}, "none", "no accounts directory and the shared key is not allowed"
    try:
        from cockpit.account import Accounts
    except ImportError:                                   # run from the source tree, outside the cockpit's interpreter
        sys.path.insert(0, str(HERE.parents[2]))
        from cockpit.account import Accounts
    b = Accounts(args.accounts).billing(str(run.get("requested_by", "")).lower(), env, allow_shared=allow_shared)
    return b.env, b.mode, b.source


def run_home(args, data: Path, workspace_id: str, run_id: str) -> tuple[Path, Path]:
    """A HOME for this one run, so that `~/ChrisBuilds64/pressroom` points at the workspace the order belongs to.

    The skills address the pipeline as ~/ChrisBuilds64/pressroom/flow and are the same files the person uses at
    the keyboard; they are not rewritten per workspace. Instead every run gets a small HOME under the stage
    workspace's tmp/: a ChrisBuilds64/ with links to the shared canon, control and develop, `pressroom` → the
    workspace's tree, CLAUDE.md and .claude/ copied from the stage workspace, trust for that path. Removed after
    the run. Returns (home, workspace dir inside it).
    """
    base = args.workspace
    home = base / "tmp" / "homes" / run_id
    ws = home / "ChrisBuilds64"
    (ws / "tmp").mkdir(parents=True, exist_ok=True)
    (ws / ".claude").mkdir(exist_ok=True)
    (home / ".claude").mkdir(exist_ok=True)
    for name in ("canon", "control", "develop"):
        if (base / name).exists():
            (ws / name).symlink_to((base / name).resolve())
    (ws / "pressroom").symlink_to(data.parent if data.name == "flow" else data)
    for name in ("skills", "agents"):
        src = base / ".claude" / name
        if src.exists():
            (ws / ".claude" / name).symlink_to(src.resolve())
    if (base / ".claude" / "settings.json").is_file():
        shutil.copy(base / ".claude" / "settings.json", ws / ".claude" / "settings.json")
    text = (base / "CLAUDE.md").read_text(encoding="utf-8") if (base / "CLAUDE.md").is_file() else ""
    text += f"\n- **Workspace of this run:** `{workspace_id}` — its pipeline is `~/ChrisBuilds64/pressroom/flow/` here ({data}). Nothing else is this run's.\n"
    (ws / "CLAUDE.md").write_text(text, encoding="utf-8")
    trust: dict = {}
    real = Path(os.environ.get("HOME", str(Path.home()))) / ".claude.json"
    if real.is_file():
        try:
            trust = {k: v for k, v in json.loads(real.read_text(encoding="utf-8")).items() if k != "projects"}
        except ValueError:
            trust = {}
    trust["projects"] = {str(ws): {"hasTrustDialogAccepted": True}}
    (home / ".claude.json").write_text(json.dumps(trust) + "\n", encoding="utf-8")
    return home, ws


def refuse(f: Path, run: dict, rules: dict, why: str, env_for_tools: dict) -> None:
    """An order that cannot be billed to anybody does not run. The record says why, and the orderer reads it
    where they look anyway: as a review entry in the container, addressed to them."""
    text = (f"This run did not start: {why}.\n\nAdd a subscription token (`claude setup-token`) or a personal API key to your "
            f"account — `cockpit account set-secret <you> CLAUDE_CODE_OAUTH_TOKEN` — and order the run again.")
    run.update(status="failed", finished=now(), exit=78, result=text, billing="none", stage=os.environ.get("PRESSROOM_ENV", "local"))
    f.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "review_append.py"), run["container"], "--by", rules.get("agent", "agent"),
                    "--title", f"Run /{run['skill']}: not started — no billing on your account", "--status", "open",
                    "--for", str(run.get("requested_by", ""))], input=text, capture_output=True, text=True, env=env_for_tools)


def execute(f: Path, run: dict, rules: dict, args, data: Path, workspace_id: str = "default") -> None:
    queue = f.parent
    transcript = queue / (f.stem + ".log")
    if args.pull:
        refresh(args.pull)
    plain_env = session_env(run, rules, args, data, workspace_id, None)
    env, billing, billed_by = billing_for(run, rules, plain_env, args)
    log.info("billing: %s", billed_by)
    if billing == "none":
        refuse(f, run, rules, billed_by, env_for_tools=plain_env)
        return
    home, ws = run_home(args, data, workspace_id, run["id"])
    env["HOME"] = str(home)
    context = context_file(run, env, args, ws)
    cmd = command_for(run, rules, args, data, context)
    timeout = int(rules.get("timeout", 1800))
    with transcript.open("w", encoding="utf-8") as out:
        out.write(f"# {run['id']} — started {run['started']} by {run['taken_by']} in workspace {workspace_id}\n$ {' '.join(cmd[:2])} … {' '.join(cmd[3:])}\n\n")
        out.flush()
        try:
            r = subprocess.run(cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
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
               result=result.strip()[:4000], stage=env["PRESSROOM_ENV"], billing=billing, workspace=workspace_id)
    shutil.rmtree(home, ignore_errors=True)                  # the run's HOME was for this run only; the transcript stays in _runs
    if session:
        run["session"] = session
    run.update(spent)
    f.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # The record in the container: one review entry, info, in the runner's own words.
    title = f"Run /{run['skill']}: {'done' if code == 0 else 'failed'}"
    body = (result.strip() or "(no output)")
    text = (body[:1800] + (" …" if len(body) > 1800 else "")) + f"\n\n*Run {run['id']}, transcript in `{run['log']}`.*"
    subprocess.run([sys.executable, str(HERE / "review_append.py"), run["container"], "--by", rules.get("agent", "agent"), "--title", title,
                    "--status", "info"], input=text, capture_output=True, text=True, env=plain_env)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="runner.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", required=True, help="where the skills and CLAUDE.md live — the session's cwd")
    p.add_argument("--data", help="one pipeline root with _runs/")
    p.add_argument("--workspaces", help="the cockpit's workspaces.json: every workspace's queue is served (write_root wins over root)")
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
    if not args.data and not args.workspaces:
        p.error("--data or --workspaces is required")
    args.data = Path(args.data).expanduser().resolve() if args.data else None
    args.workspaces = Path(args.workspaces).expanduser() if args.workspaces else None
    args.pull = [Path(x.strip()).expanduser() for x in args.pull.split(",") if x.strip()]
    args.add_dir = [Path(x).expanduser().resolve() for x in args.add_dir]
    args.accounts = Path(args.accounts).expanduser() if args.accounts else None
    args.context_script = (args.workspace / args.context_script) if args.context_script else None
    if args.context_script and not args.context_script.is_file():
        log.warning("no context script at %s — runs get CLAUDE.md and the canon only", args.context_script)
    stage = os.environ.get("PRESSROOM_ENV", "local")
    me = f"{os.environ.get('USER', 'runner')}@{socket.gethostname().split('.')[0]}/{stage}"
    log.info("runner %s (%s) — %s, workspace %s, %s%s", me, KIND,
             f"registry {args.workspaces}" if args.workspaces else f"queue {args.data / '_runs'}", args.workspace, platform.system(),
             f", pull {', '.join(p.name for p in args.pull)}" if args.pull else "")
    warned: set[str] = set()
    while True:
        roots = queues(args)                               # re-read every round: a new workspace is served from its next order on
        took = False
        for wid, data in roots:
            policy = load_policy(data)                     # re-read every round: a changed line applies to the next run
            if policy is None:
                if wid not in warned:
                    log.error("%s: no run-policy.json at %s — nothing runs there without a declared policy", wid, data)
                    warned.add(wid)
                continue
            if wid in warned:
                log.info("%s: run-policy.json found — runs resume", wid)
                warned.discard(wid)
            queue = data / "_runs"
            queue.mkdir(exist_ok=True)
            job = take(queue, me)
            if not job:
                continue
            took = True
            f, run = job
            log.info("taking %s in %s (by %s)", run["id"], wid, run.get("requested_by", "?"))
            try:
                execute(f, run, policy_for(policy, run["skill"]), args, data, wid)
            except Exception as exc:                      # the loop survives one broken order; the order records why
                log.exception("run %s crashed in the runner itself", run["id"])
                run.update(status="failed", finished=now(), exit=-1, result=f"runner error: {exc}")
                f.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log.info("%s %s (exit %s, %s turns, %s USD, %s s)", run["status"], run["id"], run.get("exit"),
                     run.get("turns", "?"), run.get("cost_usd", "?"), run.get("duration_s", "?"))
            break                                          # one run, then look at every queue again
        if took:
            continue
        if args.once:
            return 1 if (warned or not roots) else 0      # --once says in its exit code whether anything could run at all
        time.sleep(args.interval)


def queues(args) -> list[tuple[str, Path]]:
    """(workspace id, pipeline root) for every queue this runner serves. The registry wins when both are given."""
    if args.workspaces:
        try:
            doc = json.loads(args.workspaces.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("workspaces registry unreadable: %s", exc)
            return [("default", args.data)] if args.data else []
        base = args.workspaces.parent
        out = []
        for w in doc.get("workspaces", []):
            if w.get("mode", "live") != "live":            # replay worlds are served by their own app, never by Claude
                continue
            raw = w.get("write_root") or w.get("root")
            if not raw:
                continue
            p = Path(raw).expanduser()
            out.append((str(w.get("id", "?")), p if p.is_absolute() else (base / p)))
        return out
    return [("default", args.data)]


if __name__ == "__main__":
    raise SystemExit(main())
