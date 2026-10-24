"""One directory per stage: the code at its reference, the cockpit, and the runner's own HOME.

    <envs_root>/<stage>/
      develop/                   checkout of chrisbuilds64/develop at the stage's ref — code is staged
      cockpit/                   cockpit.toml, audit log, plugins/, .venv (installed from develop/ above)
      home/                      HOME of this stage's runner process
        .claude.json             trust for the workspace below
        ChrisBuilds64/           the workspace a headless session starts in
          CLAUDE.md              the slim runner instructions, with the stage named
          .claude/settings.json  permissions (the operating context arrives as an appended system prompt, built
                                 by the runner from control/shared-context/context-manifest.json)
          .claude/skills, .claude/agents  → shared control/claude
          canon, control         → shared checkouts (rules and state are not staged)
          develop                → ../../develop
          pressroom              → the stage's davfs2 mount
          tmp/

Why a HOME per stage: the skills address the pipeline as `~/ChrisBuilds64/pressroom/flow`. With its own
HOME each runner resolves that to its own stage, and the skills stay untouched — they are the same
files the person uses at the keyboard.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from .config import Env, OpsError, Settings
from .shell import run

log = logging.getLogger("pressroom-env")
TEMPLATES = Path(__file__).parent / "templates"


def _render(name: str, **vars) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    if "{{" in text:
        raise OpsError(f"template {name}: unfilled placeholder near {text[text.index('{{'):][:40]!r}")
    return text


def _own(path: Path, user: str) -> None:
    shutil.chown(path, user, user)


def _link(target: Path | str, link: Path, user: str) -> None:
    if link.is_symlink() or link.exists():
        if link.is_symlink() and os.readlink(link) == str(target):
            return
        if link.is_dir() and not link.is_symlink():
            raise OpsError(f"{link} is a real directory, expected a symlink — remove it by hand first")
        link.unlink()
    link.symlink_to(target)
    os.lchown(link, *_ids(user))


def _ids(user: str) -> tuple[int, int]:
    import pwd
    p = pwd.getpwnam(user)
    return p.pw_uid, p.pw_gid


def _mkdir(path: Path, user: str, mode: int = 0o755) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)
    _own(path, user)
    return path


def deploy_code(settings: Settings, env: Env, ref: str | None = None) -> str:
    """develop at the stage's reference, then the cockpit venv from it. Returns the commit."""
    s, ref = settings.server, ref or env.ref
    d = env.dir(s)
    _mkdir(d, s.runner_user)
    dev = d / "develop"
    if not (dev / ".git").is_dir():
        run(["git", "clone", "--no-checkout", s.develop_repo, str(dev)], user=s.runner_user)
    run(["git", "-C", str(dev), "fetch", "--quiet", "origin", ref], user=s.runner_user)
    run(["git", "-C", str(dev), "checkout", "--quiet", "--force", "FETCH_HEAD"], user=s.runner_user)
    commit = run(["git", "-C", str(dev), "log", "-1", "--format=%h %cd %s", "--date=short"], user=s.runner_user, quiet=True).stdout.strip()
    log.info("%s: develop at %s → %s", env.name, ref, commit)

    cp = _mkdir(d / "cockpit", s.runner_user)
    _mkdir(cp / "plugins", s.runner_user)
    venv = cp / ".venv"
    if not (venv / "bin" / "python").exists():
        run(["python3", "-m", "venv", str(venv)], user=s.runner_user)
    run([str(venv / "bin" / "pip"), "install", "--quiet", "--upgrade", "pip"], user=s.runner_user, quiet=True)
    run([str(venv / "bin" / "pip"), "install", "--quiet", "-e", str(dev / "apps" / "cockpit")], user=s.runner_user)
    version = run([str(venv / "bin" / "python"), "-c", "import cockpit; print(cockpit.__version__)"], user=s.runner_user, quiet=True).stdout.strip()
    log.info("%s: cockpit %s installed", env.name, version)
    return commit


def write_cockpit_config(settings: Settings, env: Env, folder_id: int) -> Path:
    s = settings.server
    cp = env.dir(s) / "cockpit"
    toml = _render("cockpit.toml", env=env.name, label=env.label, port=env.port, base_path=env.base_path,
                   users_json=s.users_json, cookie_secret=s.cookie_secret,
                   data=s.groupfolders_data / str(folder_id) / "files" / "flow", mount=env.mount / "flow")
    p = cp / "cockpit.toml"
    p.write_text(toml, encoding="utf-8"); _own(p, s.runner_user)
    for f in (s.users_json, s.cookie_secret):
        if not f.exists():
            raise OpsError(f"{f} is missing — the cockpits share one users file and one cookie secret; create them first")
    return p


def build_home(settings: Settings, env: Env, trust_from: Path | None = None) -> Path:
    """The runner's HOME for this stage, with the workspace inside."""
    s, u = settings.server, settings.server.runner_user
    home = _mkdir(env.dir(s) / "home", u, 0o750)
    _mkdir(home / ".claude", u)
    ws = _mkdir(home / "ChrisBuilds64", u)
    _mkdir(ws / "tmp", u)
    _mkdir(ws / ".claude", u)
    for name in ("canon", "control"):
        if not (s.shared / name).is_dir():
            raise OpsError(f"shared checkout {s.shared / name} is missing")
        _link(s.shared / name, ws / name, u)
    _link(Path("../../develop"), ws / "develop", u)
    _link(env.mount, ws / "pressroom", u)
    _link(Path("../control/claude/skills"), ws / ".claude" / "skills", u)
    _link(Path("../control/claude/agents"), ws / ".claude" / "agents", u)

    p = ws / "CLAUDE.md"
    p.write_text(_render("CLAUDE.md", env=env.name, label=env.label, mount=env.mount), encoding="utf-8"); _own(p, u)
    p = ws / ".claude" / "settings.json"
    p.write_text(_render("settings.json"), encoding="utf-8"); _own(p, u)

    # Trust: Claude Code ignores a workspace's settings.json until the project is marked trusted in
    # ~/.claude.json. Start from the runner's existing file when there is one, keep only the project list.
    trust = home / ".claude.json"
    data: dict = {}
    if trust.exists():
        data = json.loads(trust.read_text(encoding="utf-8"))
    elif trust_from and trust_from.exists():
        data = {k: v for k, v in json.loads(trust_from.read_text(encoding="utf-8")).items() if k != "projects"}
    data.setdefault("projects", {})[str(ws)] = {**data.get("projects", {}).get(str(ws), {}), "hasTrustDialogAccepted": True}
    trust.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8"); trust.chmod(0o600); _own(trust, u)
    log.info("%s: workspace %s ready (HOME %s)", env.name, ws, home)
    return ws
