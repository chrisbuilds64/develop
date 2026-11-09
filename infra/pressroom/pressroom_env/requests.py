"""Deploy requests (ADR-028): a helper asks, the server checks the gate on the case, then deploys.

A helper's run cannot deploy: the runner has no privileges (NoNewPrivileges) and must not get any. It writes a request
into the spool instead —

    {"stage": "test", "tag": "v2026.11.2", "space_stage": "prod", "space": "shipyard",
     "case": "SW-2026-001-split-the-api", "run": "<the release run's id>"}

— and a root service started by a path unit takes it. The service believes nothing the request says about the gate.
It reads the case in the space's tree itself: the case must stand in the stage whose configuration says
`"deploys": "<stage>"`, which only the product owner's acceptance reaches. The tag must point at a commit on `main`,
which only the product owner's merge puts there. A space may deploy only to its own stage or below (ENTW < TEST <
PROD), so a trial change on ENTW can never reach production.

Then `deploy <stage> --ref <tag>` runs as its own process. Its outcome is written next to the request (done/) and
handed back to the case as an order for the `shipyard-verify` helper — the queue is a directory, so the report waits for a
runner even when the deploy restarted the very runner that asked.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

from .config import Env, Settings
from .shell import OpsError, run

log = logging.getLogger("pressroom-env")

SPOOL = Path("/var/lib/pressroom/deploy-requests")
ORDER = ("entw", "test", "prod")
TAG = re.compile(r"^v\d{4}\.\d{2}\.\d{1,3}$")
CASE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _rank(stage: str) -> int:
    return ORDER.index(stage) if stage in ORDER else -1


def check(settings: Settings, req: dict) -> tuple[Env, Env, object, Path]:
    """The request against the server's own view. Returns (target stage, source stage, space, case dir) or raises."""
    target, source = str(req.get("stage", "")), str(req.get("space_stage", ""))
    tag, case, space_id = str(req.get("tag", "")), str(req.get("case", "")), str(req.get("space", ""))
    if target not in settings.envs or source not in settings.envs:
        raise OpsError(f"unknown stage: {target or '?'} from {source or '?'}")
    if _rank(target) < 0 or _rank(source) < 0 or _rank(target) > _rank(source):
        raise OpsError(f"a space of {source} may not deploy to {target}")
    if not TAG.match(tag):
        raise OpsError(f"'{tag}' is not a release tag (vYYYY.MM.N)")
    if not CASE.match(case):
        raise OpsError(f"'{case}' is not a case id")
    src = settings.env(source)
    space = next((sp for sp in src.spaces if sp.id == space_id), None)
    if space is None:
        raise OpsError(f"{source} has no space '{space_id}'")
    cfg = src.dir(settings.server) / "develop" / "apps" / "casefile" / "config" / space.application / "stages.json"
    gate = next((s["folder"] for s in json.loads(cfg.read_text(encoding="utf-8"))["stages"] if s.get("deploys") == target), None)
    if gate is None:
        raise OpsError(f"{space.application} names no stage that deploys {target}")
    here = space.mount / "flow" / gate / case
    if not here.is_dir():
        raise OpsError(f"{case} is not in {gate}: the release to {target} has not been accepted")
    return settings.env(target), src, space, here


def on_main(settings: Settings, env: Env, tag: str) -> str:
    """The tag's commit, if it is on origin/main; raises otherwise."""
    dev, user = str(env.dir(settings.server) / "develop"), settings.server.runner_user
    run(["git", "-C", dev, "fetch", "--quiet", "--tags", "origin", "main"], user=user)
    commit = run(["git", "-C", dev, "rev-parse", f"refs/tags/{tag}^{{commit}}"], user=user).stdout.strip()
    if run(["git", "-C", dev, "merge-base", "--is-ancestor", commit, "origin/main"], user=user, check=False).returncode != 0:
        raise OpsError(f"{tag} ({commit[:10]}) is not on main")
    return commit


def report(settings: Settings, space, case_dir: Path, req: dict, result: dict) -> str:
    """The outcome back into the case: an order for `shipyard-verify`, with the report as its note. Written as the runner."""
    now = dt.datetime.now().astimezone()
    case = case_dir.name
    rid = f"{now.strftime('%Y%m%d-%H%M%S')}_shipyard-verify_{case}"
    order = {"id": rid, "skill": "shipyard-verify", "container": f"{case_dir.parent.name}/{case}",
             "requested_by": str(req.get("requested_by") or "axel"), "runner": "claude-code", "status": "queued",
             "created": now.isoformat(timespec="seconds"), "lang": "en",
             "note": "Deploy report from the server:\n\n" + json.dumps(result, ensure_ascii=False, indent=2)}
    path = space.mount / "flow" / "_runs" / f"{rid}.json"
    run(["sh", "-c", 'mkdir -p "$(dirname "$1")" && cat > "$1"', "sh", str(path)], user=settings.server.runner_user,
        input=json.dumps(order, ensure_ascii=False, indent=2) + "\n")
    return rid


def serve(settings: Settings, spool: Path = SPOOL, deploy=None, config: Path | None = None) -> list[dict]:
    """Take every waiting request once. Returns the results (also written to spool/done/)."""
    done = spool / "done"
    done.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(spool.glob("*.json")):
        try:
            req = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            req = {"unreadable": str(exc)}
        result = {"request": req, "received": _now()}
        target = space = case_dir = None
        try:
            target, _src, space, case_dir = check(settings, req)
            result["commit"] = on_main(settings, target, req["tag"])
            r = (deploy or _deploy)(target.name, req["tag"], config)
            result.update(outcome="deployed" if r.returncode == 0 else "failed", exit=r.returncode,
                          log_tail=(r.stdout + r.stderr).strip().splitlines()[-15:])
        except OpsError as exc:
            result.update(outcome="refused", reason=str(exc))
            space, case_dir = _locate(settings, req)
        result["finished"] = _now()
        f.rename(done / f.name)
        (done / f"{f.stem}.result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log.info("request %s: %s %s", f.name, result["outcome"], result.get("reason", ""))
        if space is not None and case_dir is not None:
            result["verify_order"] = report(settings, space, case_dir, req, result)
        out.append(result)
    return out


def _locate(settings: Settings, req: dict):
    """Where to report a refusal: the case in the named space, whatever stage it stands in. (None, None) if not found."""
    try:
        src = settings.env(str(req.get("space_stage", "")))
    except (OpsError, KeyError):
        return None, None
    space = next((sp for sp in src.spaces if sp.id == str(req.get("space", ""))), None)
    case = str(req.get("case", ""))
    if space is None or not CASE.match(case):
        return None, None
    hit = next((d for d in sorted((space.mount / "flow").glob(f"*/{case}")) if d.is_dir()), None)
    return (space, hit) if hit else (None, None)


def _deploy(stage: str, tag: str, config: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pressroom_env", *(["--config", str(config)] if config else []), "deploy", stage, "--ref", tag],
                          capture_output=True, text=True, timeout=1800, cwd=str(Path(__file__).resolve().parents[1]))
