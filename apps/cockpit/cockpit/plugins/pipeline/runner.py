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

Sessions (ADR-020): with `--accounts` the runner also serves every person's session queue for this
stage — a message (`chat`) or the closing turn (`end`) with one of their agents. The agent comes from
the person's team (hired from a template in `--agents`): rights from the template cut to the hire,
identity from the template's folder, memory from the hire. A session's place (a workspace the person
may open) gives it a pipeline; without one it has none. The conversation is a chain of `--resume` in
a HOME that lives as long as the session, because the engines keep a session's transcript there. The
closing turn writes the log into the person's folder; then the lease is released.

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


def run_home(args, data: Path | None, workspace_id: str, run_id: str) -> tuple[Path, Path]:
    home = args.workspace / "tmp" / "homes" / run_id
    if (home / "ChrisBuilds64" / "CLAUDE.md").is_file():
        return home, home / "ChrisBuilds64"           # a session's HOME, built at its first turn and kept until its end
    return _build_home(args, data, workspace_id, run_id)


def _build_home(args, data: Path | None, workspace_id: str, run_id: str) -> tuple[Path, Path]:
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
    if data is not None:
        (ws / "pressroom").symlink_to(data.parent if data.name == "flow" else data)
    for name in ("skills", "agents"):
        src = base / ".claude" / name
        if src.exists():
            (ws / ".claude" / name).symlink_to(src.resolve())
    if (base / ".claude" / "settings.json").is_file():
        shutil.copy(base / ".claude" / "settings.json", ws / ".claude" / "settings.json")
    text = (base / "CLAUDE.md").read_text(encoding="utf-8") if (base / "CLAUDE.md").is_file() else ""
    text += (f"\n- **Workspace of this run:** `{workspace_id}` — its pipeline is `~/ChrisBuilds64/pressroom/flow/` here ({data}). Nothing else is this run's.\n"
             if data is not None else "\n- **No workspace in this run:** it was opened outside one; there is no pipeline to work on.\n")
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


# -------------------------------------------------------------------- sessions (ADR-019)

def _accounts(args):
    try:
        from cockpit.account import Accounts
    except ImportError:                                   # run from the source tree, outside the cockpit's interpreter
        sys.path.insert(0, str(HERE.parents[2]))
        from cockpit.account import Accounts
    return Accounts(args.accounts)


def _cockpit():
    try:
        from cockpit.workspaces import Workspaces
    except ImportError:                                   # run from the source tree, outside the cockpit's interpreter
        sys.path.insert(0, str(HERE.parents[2]))
        from cockpit.workspaces import Workspaces
    return Workspaces


def _templates(args):
    try:
        from cockpit.agents import Catalog
    except ImportError:
        sys.path.insert(0, str(HERE.parents[2]))
        from cockpit.agents import Catalog
    return Catalog.load(args.agents)


def session_queues(args) -> list[tuple]:
    """(person, store) for every account with a session queue on this stage."""
    if not args.accounts:
        return []
    acc, stage = _accounts(args), os.environ.get("PRESSROOM_ENV", "local")
    out = []
    for person in acc.people():
        store = acc.store(person, stage)
        if (store.dir / "queue").is_dir():
            out.append((person, store))
    return out


def session_place(args, person: str, s):
    """(workspace id, pipeline root) for the session's place — only a live workspace the person may open."""
    wid = s.place.get("workspace") if s.place else None
    if not wid or not args.workspaces:
        return "", None
    try:
        reg = _cockpit()(args.workspaces, args.workspaces.parent)
    except Exception:                                     # noqa: BLE001
        return "", None
    w = reg.get(wid)
    if w is None or w.mode != "live" or not w.visible_to(person):
        return "", None
    pipe = reg.component(w, "pipeline")
    return w.id, (pipe.write_path or pipe.path)


def place_text(s) -> str:
    p = s.place or {}
    return " · ".join(x for x in (p.get("workspace"), p.get("application"), p.get("item")) if x) or p.get("title") or "Cockpit"


def end_prompt(log_path: Path, notes: Path | None, s) -> str:
    notes_line = (f"If this session taught you something about how the collaboration works, add one dated observation to "
                  f"your working notes at `{notes}` in their format; otherwise leave them untouched. " if notes else
                  "Your working notes are read-only here; put what you learned into the log's last section instead. ")
    return (f"End this session now. Write the session log to `{log_path}` — Markdown, in German (internal documentation). "
            f"Structure: `# Session {s.started[:10]} — <title>`, then Datum, Instanz, Ort `{place_text(s)}`, Thema "
            f"„{s.topic}“; `## Was wurde gemacht`; `## Entscheidungen`; `## Offene Punkte`; `## Continuation Thread` with "
            "the open tension and the next natural sentence. Only what this conversation contains — no invented work. "
            f"{notes_line}Touch no other file. Then answer in two lines: the log's path and the next natural sentence.")


OPENAI_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")


def openai_call(key: str, model: str, instructions: str, messages: list[dict], timeout: int) -> tuple[str, dict]:
    """One answer from the Responses API: the text and the usage. Raises RuntimeError with the API's sentence."""
    import urllib.error
    import urllib.request
    body = json.dumps({"model": model, "instructions": instructions,
                       "input": [{"role": m["role"], "content": m["content"]} for m in messages]}).encode()
    req = urllib.request.Request(f"{OPENAI_BASE}/responses", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise RuntimeError(f"{exc.code} {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"no answer from the API: {exc}") from exc
    text = data.get("output_text") or "".join(
        c.get("text", "") for o in data.get("output", []) if o.get("type") == "message" for c in o.get("content", []) if c.get("type") == "output_text")
    return text.strip(), dict(data.get("usage") or {}, model=data.get("model", model))


NOTES_HEAD = "## Für die Working Notes"


def openai_end_prompt(s) -> str:
    return (f"End this session now and write its log. Answer with the log only, Markdown, in German (internal documentation). "
            f"Structure: `# Session {s.started[:10]} — <title>`, then Datum, Instanz, Ort `{place_text(s)}`, Thema „{s.topic}“; "
            "`## Was wurde gemacht`; `## Entscheidungen`; `## Offene Punkte`; `## Continuation Thread` with the open tension and the "
            f"next natural sentence; last `{NOTES_HEAD}` with one dated observation about how the collaboration works, if this "
            "session taught you one, otherwise a single dash. Only what this conversation contains — no invented work.")


def execute_openai(f: Path, order: dict, s, agent, store, rules: dict, context: Path | None, args, finish, notes: Path | None) -> None:
    """A turn on the openai engine: the conversation so far as input, the context as instructions, no tools. The closing
    turn's answer is the log; its last section goes into the working notes when they are writable."""
    key = _accounts(args).openai_key(s.user) if args.accounts else None
    if not key:
        text = (f"This message was not answered: {s.user} has no OpenAI API key on their account. {agent.label} runs on OpenAI; "
                "add OPENAI_API_KEY on your account page (it is billed by OpenAI's API, not by a ChatGPT plan).")
        store.add_turn(s.id, "system", text)
        finish("failed", text, exit=78, billing="none")
        if order.get("type") == "end":
            store.close(s.id, None)
        return
    messages = [{"role": t["role"], "content": t["text"]} for t in store.transcript(s.id) if t["role"] in ("user", "assistant")]
    if order.get("type") == "end":
        messages.append({"role": "user", "content": openai_end_prompt(s) + (f"\n\nNote from {s.user}: {order['text']}" if order.get("text") else "")})
    instructions = context.read_text(encoding="utf-8") if context else f"You are {agent.label}."
    timeout = int(rules.get("timeout", 600))
    text, usage, err = "", {}, ""
    for model in [m for m in (rules.get("model"), rules.get("fallback_model")) if m]:
        try:
            text, usage = openai_call(key, model, instructions, messages, timeout)
            break
        except RuntimeError as exc:
            err = f"{model}: {exc}"
            log.warning("openai %s failed: %s", model, str(exc)[:200])
    if not text:
        store.add_turn(s.id, "system", f"no answer — {err or 'no model configured'}")
        finish("failed", err or "no model configured", exit=1, billing="api-key")
        if order.get("type") == "end":
            store.close(s.id, None)                        # an end that cannot write its log still releases the lease
        return
    spent = {"model": usage.get("model"), "turns": 1}
    if isinstance(usage.get("input_tokens"), int):
        spent.update(input_tokens=usage["input_tokens"], output_tokens=usage.get("output_tokens"))
    if order.get("type") == "end":
        log_path = store.log_path(s)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(text + "\n", encoding="utf-8")
        learned = text.split(NOTES_HEAD, 1)[1].strip() if NOTES_HEAD in text else ""
        if notes and learned and learned.strip("-– ").strip():
            with notes.open("a", encoding="utf-8") as fh:
                fh.write(f"\n### {s.started[:10]} — {s.topic} (Session im Cockpit)\n\n{learned}\n")
        store.add_turn(s.id, "assistant", f"Log geschrieben: `{log_path.name}`", by=agent.id, model=spent.get("model"))
        finish("done", text, exit=0, billing="api-key", **spent)
        store.close(s.id, log_path)
        return
    store.add_turn(s.id, "assistant", text, by=agent.id, model=spent.get("model"))
    store.update(s.id, turns=s.turns + 1)
    finish("done", text, exit=0, billing="api-key", **spent)


def codex_events(stdout: str) -> tuple[str, dict]:
    """The thread id and the usage from `codex exec --json` (one JSON event per line)."""
    thread, usage = "", {}
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "thread.started":
            thread = str(ev.get("thread_id", ""))
        elif ev.get("type") == "turn.completed" and isinstance(ev.get("usage"), dict):
            usage = ev["usage"]
    return thread, usage


def execute_codex(f: Path, order: dict, s, agent, store, rules: dict, context: Path | None, args, finish, wsdir: Path,
                  env: dict, log_path: Path | None, notes: Path | None) -> None:
    """A turn on the codex engine: `codex exec` in the session's HOME, resumed by thread id, signed in with the person's
    ChatGPT plan (their CODEX_HOME) — or, without one, their own OpenAI key. The context goes with the first message;
    the resumed thread keeps it."""
    acc = _accounts(args) if args.accounts else None
    home = acc.codex_home(s.user) if acc else None
    key = acc.openai_key(s.user) if acc else None
    env = {k: v for k, v in env.items() if k not in ("OPENAI_API_KEY", "CODEX_API_KEY")}
    if home:
        env["CODEX_HOME"], billing = str(home), "subscription"
    elif key:
        env["CODEX_HOME"], env["CODEX_API_KEY"], billing = str(wsdir.parent / ".codex"), key, "api-key"
        Path(env["CODEX_HOME"]).mkdir(exist_ok=True)
    else:
        text = (f"This message was not answered: {s.user} has no Codex sign-in and no OpenAI API key. {agent.label} runs on Codex; "
                "sign in once with `codex login --device-auth` for your account, or add OPENAI_API_KEY on your account page.")
        store.add_turn(s.id, "system", text)
        finish("failed", text, exit=78, billing="none")
        if order.get("type") == "end":
            store.close(s.id, None)
        return
    end = order.get("type") == "end"
    if end:
        prompt = end_prompt(log_path, notes, s) + (f"\n\nNote from {s.user}: {order['text']}" if order.get("text") else "")
    else:
        prompt = order["text"]
    if not s.claude_session and context:                  # the thread starts with the operating context, as Claude's system prompt does
        prompt = f"<operating-context>\n{context.read_text(encoding='utf-8')}\n</operating-context>\n\n{prompt}"
    writes = "Edit" in rules.get("tools", []) or "Write" in rules.get("tools", []) or end
    roots = [str(log_path.parent)] if end and log_path else []
    if end and notes:
        roots.append(str(notes.parent))
    out = f.parent / (f.stem + ".answer.txt")
    conf = ["-c", f'sandbox_mode="{"workspace-write" if writes else "read-only"}"']
    if roots:
        conf += ["-c", "sandbox_workspace_write.writable_roots=" + json.dumps(roots)]
    timeout = int(rules.get("timeout", 1800))
    code, stdout, stderr, model_used = 1, "", "", None
    for model in [m for m in (rules.get("model"), rules.get("fallback_model")) if m] or [None]:
        cmd = [args.codex, "exec", "--json", "--skip-git-repo-check", "-o", str(out), *conf, *(["-m", model] if model else [])]
        cmd += (["resume", s.claude_session, prompt] if s.claude_session else [prompt])
        try:
            r = subprocess.run(cmd, cwd=wsdir, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            code, stdout, stderr = r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = 124, (exc.stdout or ""), f"timed out after {timeout}s"
        model_used = model
        if code == 0:
            break
        log.warning("codex %s failed (%s): %s", model, code, (stderr or stdout).strip()[-200:])
    (f.parent / (f.stem + ".log")).write_text(f"# {order['id']}\n$ codex exec … ({billing})\n\n{stdout}\n[stderr]\n{stderr}\n", encoding="utf-8")
    thread, usage = codex_events(stdout)
    text = out.read_text(encoding="utf-8").strip() if out.is_file() else ""
    if code != 0 or not text:
        why = (stderr or stdout).strip()[-600:] or "no answer"
        store.add_turn(s.id, "system", f"no answer — {why}")
        finish("failed", why, exit=code or 1, billing=billing)
        if end:
            store.close(s.id, None)
        return
    spent = {k: v for k, v in {"model": model_used, "turns": 1, "input_tokens": usage.get("input_tokens"),
                                "output_tokens": usage.get("output_tokens")}.items() if v is not None}
    store.add_turn(s.id, "assistant", text, by=agent.id, model=model_used)
    if not end:
        store.update(s.id, claude_session=thread or s.claude_session, turns=s.turns + 1)
    finish("done", text, exit=0, billing=billing, **spent)
    if end:
        store.close(s.id, log_path)


def notes_sync(args) -> None:
    """Before a turn: the notes worktree follows control's main, so an agent learns on top of today's rules.
    A rebase that does not apply is aborted and logged; the agent then works on the notes it has."""
    repo = args.notes_repo
    if not repo:
        return
    r = subprocess.run(["git", "-C", str(repo), "fetch", "--quiet", "origin", "main"], capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=cockpit runner", "-c", "user.email=agents@chrisbuilds64.com",
                            "rebase", "--quiet", "origin/main"], capture_output=True, text=True, timeout=120)   # the runner user has no git identity
        if r.returncode != 0:
            subprocess.run(["git", "-C", str(repo), "rebase", "--abort"], capture_output=True)
    if r.returncode != 0:
        log.warning("notes: could not follow main: %s", (r.stderr or r.stdout).strip()[-200:])


def notes_commit(args, label: str, s, paths: list) -> str | None:
    """After the closing turn: what the session left inside the notes worktree — the agent's memory, the log when the
    person's log folder is there — becomes one commit on the stage's notes branch, pushed to the notes remote.
    Nothing reaches control's main without Chris' merge. Returns the commit, or None."""
    repo = args.notes_repo
    if not repo:
        return None
    rels = []
    for p in paths:
        if p is None:
            continue
        try:
            rels.append(str(Path(p).resolve().relative_to(repo.resolve())))
        except ValueError:
            continue                                      # outside the worktree: the person's own folder, not ours to commit
    if not rels or not subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", *rels], capture_output=True, text=True).stdout.strip():
        return None
    branch = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    msg = f"notes({os.environ.get('PRESSROOM_ENV', 'local')}): {label} — {s.topic}\n\nSession {s.id}, for {s.user}. Learned in a cockpit session; reaches main only by merge."
    run = lambda *c: subprocess.run(["git", "-C", str(repo), *c], capture_output=True, text=True, timeout=120)
    run("add", "--", *rels)
    r = run("-c", f"user.name={label} (cockpit)", "-c", "user.email=agents@chrisbuilds64.com", "commit", "--quiet", "-m", msg)
    if r.returncode != 0:
        log.warning("notes: commit failed: %s", (r.stderr or r.stdout).strip()[-200:])
        return None
    sha = run("rev-parse", "--short", "HEAD").stdout.strip()
    r = run("push", "--quiet", "--force-with-lease", args.notes_remote, f"HEAD:refs/heads/{branch}")
    if r.returncode != 0:
        log.warning("notes: %s committed but not pushed: %s", sha, (r.stderr or r.stdout).strip()[-200:])
    else:
        log.info("notes: %s pushed to %s %s", sha, args.notes_remote, branch)
    return sha


def execute_session(f: Path, order: dict, person: str, store, args) -> None:
    """One turn of a session: a message, or the closing turn that writes the log and releases the lease."""
    sid, kind = order["session"], order.get("type")

    def finish(status: str, text: str, **extra) -> None:
        order.update(status=status, finished=now(), result=text[:4000], **extra)
        f.write_text(json.dumps(order, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    notes_sync(args)                                       # the agents' folders follow main before the agent is read
    s = store.get(sid)
    stage = os.environ.get("PRESSROOM_ENV", "local")
    team = _accounts(args).team(person, _templates(args), stage)
    agent = team.get(order.get("agent", ""))
    if s is None or s.status == "closed" or agent is None or kind not in ("chat", "end") or s.user != person:
        why = "the session is not running" if s is None or s.status == "closed" else (
            f"'{order.get('agent')}' is not on {person}'s team" if agent is None else f"unknown order type '{kind}'")
        finish("failed", why, exit=78)
        return
    wid, data = session_place(args, person, s)
    policy = (load_policy(data) if data else None) or {}
    rules = {**policy.get("default", {}), **agent.rules_for(None)}       # the agent's ceiling is the conversation's rule
    if args.pull:
        refresh(args.pull)
    plain_env = dict(os.environ, **({"COCKPIT_DATA_DIR": str(data), "CONTEXT_LOOP_DIR": str(data)} if data else {}), PRESSROOM_WORKSPACE=wid,
                     PRESSROOM_ENV=os.environ.get("PRESSROOM_ENV", "local"), PRESSROOM_SKILL="",
                     PRESSROOM_SESSION=sid, PRESSROOM_TOPIC=s.topic, PRESSROOM_ORDERED_BY=s.user, PRESSROOM_PLACE=place_text(s),
                     PRESSROOM_AGENT=agent.context or agent.id, PRESSROOM_AGENT_LABEL=agent.label,
                     PRESSROOM_AGENT_DIR=str(agent.dir),
                     PRESSROOM_AGENT_SIGNATURE=str(agent.signature_path or ""), PRESSROOM_AGENT_NOTES=str(agent.notes_path or ""),
                     PRESSROOM_SESSION_LOG=s.starts_from or "",
                     PRESSROOM_RUN_ID=order["id"])
    memory = agent.notes_path.parent if agent.notes_path else None
    if memory is not None:
        memory.mkdir(parents=True, exist_ok=True)
    notes_writable = bool(memory is not None and os.access(memory, os.W_OK))
    if agent.engine == "codex":
        home, wsdir = run_home(args, data, wid, f"session-{sid}")
        cenv = dict(plain_env, HOME=str(home))
        context = context_file(order, cenv, args, wsdir) if not s.claude_session else None
        log_path = store.log_path(s) if kind == "end" else None
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("session %s %s — codex engine, %s", sid, kind, rules.get("model"))
        execute_codex(f, order, s, agent, store, rules, context, args, finish, wsdir, cenv, log_path,
                      agent.notes_path if notes_writable else None)
        if kind == "end":
            shutil.rmtree(home, ignore_errors=True)
            notes_commit(args, agent.label, s, [agent.notes_path if notes_writable else None, log_path])
        return
    if agent.engine == "openai":
        home, wsdir = run_home(args, data, wid, f"session-{sid}")
        context = context_file(order, dict(plain_env, HOME=str(home)), args, wsdir)
        log.info("session %s %s — openai engine, %s", sid, kind, rules.get("model"))
        execute_openai(f, order, s, agent, store, rules, context, args, finish, agent.notes_path if notes_writable else None)
        if kind == "end":
            shutil.rmtree(home, ignore_errors=True)
            closed = store.get(sid)
            notes_commit(args, agent.label, s, [agent.notes_path if notes_writable else None, closed.log if closed else None])
        return
    env, billing, billed_by = billing_for(order, rules, plain_env, args)
    log.info("session %s %s — billing: %s", sid, kind, billed_by)
    if billing == "none":
        text = (f"This message was not answered: {billed_by}. Add a subscription token (`claude setup-token`) or a personal "
                "API key on your account page, then send it again.")
        store.add_turn(sid, "system", text)
        finish("failed", text, exit=78, billing="none")
        if kind == "end":
            store.close(sid, None)
        return

    home, wsdir = run_home(args, data, wid, f"session-{sid}")
    env["HOME"] = str(home)
    context = context_file(order, env, args, wsdir)
    log_path, notes = None, None
    if kind == "end":
        log_path = store.log_path(s)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        notes = agent.notes_path if notes_writable else None
        prompt = end_prompt(log_path, notes, s) + (f"\n\nNote from {s.user}: {order['text']}" if order.get("text") else "")
    else:
        prompt = order["text"]
    cmd = [args.claude, "-p", prompt, "--output-format", "json", "--permission-mode", rules.get("permission_mode", "acceptEdits")]
    if s.claude_session:
        cmd += ["--resume", s.claude_session]
    if context:
        cmd += ["--append-system-prompt-file", str(context)]
    if rules.get("model"):
        cmd += ["--model", rules["model"]]                # assigned to the agent, else the stage's default from run-policy.json
    if rules.get("fallback_model") and rules.get("fallback_model") != rules.get("model"):
        cmd += ["--fallback-model", rules["fallback_model"]]
    subst = {"{data}": str(data), "{container}": str(data)} if data else {}
    dirs = [subst.get(x, x) for x in rules.get("write", []) if not x.startswith("{") or x in subst] + [str(d) for d in args.add_dir]
    tools = list(rules.get("tools", [])) + (WEB_TOOLS if rules.get("web") else [])
    if kind == "end":
        dirs.append(str(log_path.parent))
        if notes:
            dirs.append(str(notes.parent))
        tools += [t for t in ("Write", "Edit") if t not in tools]       # the log has to be written, whatever the ceiling
    for d in dict.fromkeys(dirs):
        cmd += ["--add-dir", d]
    if tools:
        cmd += ["--allowedTools", ",".join(dict.fromkeys(tools))]
    transcript = f.parent / (f.stem + ".log")
    timeout = int(rules.get("timeout", 1800))
    try:
        r = subprocess.run(cmd, cwd=wsdir, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        code, stdout, stderr = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, (exc.stdout or ""), f"timed out after {timeout}s"
    transcript.write_text(f"# {order['id']}\n$ {' '.join(cmd[:2])} … {' '.join(cmd[3:])}\n\n{stdout}\n[stderr]\n{stderr}\n", encoding="utf-8")
    result, session, spent = "", "", {}
    try:
        out = json.loads(stdout)
        result, session, spent = str(out.get("result", "")), str(out.get("session_id", "")), accounting(out)
    except Exception:
        result = (stdout.strip() or stderr.strip())[-1500:]
    store.add_turn(sid, "assistant" if code == 0 else "system", result or "(no answer)", by=agent.id,
                   cost_usd=spent.get("cost_usd"), model=spent.get("model"))
    if code == 0 and session:
        store.update(sid, claude_session=session, turns=s.turns + 1)
    finish("done" if code == 0 else "failed", result, exit=code, billing=billing, log=f"queue/{transcript.name}", **spent)
    if kind == "end":
        closed = store.close(sid, log_path)
        shutil.rmtree(home, ignore_errors=True)
        notes_commit(args, agent.label, s, [notes, log_path])   # the session's HOME ends with the session; the log and transcript stay
        log.info("session %s closed — log %s", sid, closed.log or "not written")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="runner.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", required=True, help="where the skills and CLAUDE.md live — the session's cwd")
    p.add_argument("--data", help="one pipeline root with _runs/")
    p.add_argument("--workspaces", help="the cockpit's workspaces.json: every workspace's queue is served (write_root wins over root)")
    p.add_argument("--claude", default=os.environ.get("CLAUDE_BIN", "claude"))
    p.add_argument("--codex", default=os.environ.get("CODEX_BIN", str(Path.home() / ".local" / "bin" / "codex")))
    p.add_argument("--interval", type=int, default=10)
    p.add_argument("--once", action="store_true", help="process what is queued, then exit")
    p.add_argument("--pull", default="", help="comma-separated git checkouts to `pull --ff-only` before every run (canon, control)")
    p.add_argument("--log-level", default=os.environ.get("RUNNER_LOG_LEVEL", "INFO"))
    p.add_argument("--add-dir", action="append", default=[],
                   help="a directory the session may read beyond the workspace — the shared checkouts the workspace links to")
    p.add_argument("--accounts", default="", help="the cockpit's accounts directory — the orderer's token decides the billing; '' = always the shared key")
    p.add_argument("--agents", default="", help="the organisation's agent templates (ADR-020); people's teams are hired from these")
    p.add_argument("--notes-repo", default="", help="a git worktree on the stage's notes branch that holds the agents' folders; "
                   "what an agent learns is committed there and pushed to --notes-remote ('' = notes are not committed)")
    p.add_argument("--notes-remote", default="notes", help="the remote the notes branch is pushed to — never control's main")
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
    args.notes_repo = Path(args.notes_repo).expanduser() if args.notes_repo else None
    args.agents = Path(args.agents).expanduser() if args.agents else None
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
        if not took:
            for person, store in session_queues(args):
                job = take(store.dir / "queue", me)
                if not job:
                    continue
                took = True
                f, order = job
                log.info("taking %s %s for %s", order.get("type"), order["session"], person)
                try:
                    execute_session(f, order, person, store, args)
                except Exception as exc:                  # noqa: BLE001 — the loop survives one broken turn
                    log.exception("session order %s crashed in the runner itself", order["id"])
                    order.update(status="failed", finished=now(), exit=-1, result=f"runner error: {exc}")
                    f.write_text(json.dumps(order, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    store.add_turn(order["session"], "system", f"runner error: {exc}")
                break
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
