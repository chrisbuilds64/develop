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


WORLDS_LATER = ("gatehouse", "gatehouse-live", "gatehouse-demo", "posteingang", "posteingang-live", "angebot", "angebot-live",
                "bestandsakte", "aenderungsakte", "pressroom-muster")       # ADR-021: the elicitation sample world and the empty tree a live elicitation starts from


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
    run([str(venv / "bin" / "pip"), "install", "--quiet", "-e", str(dev / "apps" / "casefile")], user=s.runner_user)
    run([str(venv / "bin" / "pip"), "install", "--quiet", "-e", str(dev / "apps" / "cockpit")], user=s.runner_user)
    version = run([str(venv / "bin" / "python"), "-c", "import cockpit, casefile; print(cockpit.__version__, casefile.__version__)"], user=s.runner_user, quiet=True).stdout.strip()
    log.info("%s: cockpit + casefile %s installed", env.name, version)
    # the help must match the screen before the stage serves it: an anchor without a topic, or the other way round, stops here
    r = run([str(venv / "bin" / "cockpit"), "help", "check"], user=s.runner_user, check=False)
    if r.returncode != 0:
        raise OpsError(f"{env.name}: the help does not match the screen — fix it in the same commit:\n{(r.stdout or r.stderr).strip()}")
    log.info("%s: help in step with the screen", env.name)
    # colour, type and radius come from the tokens: a raw value beyond the baseline stops here (tools/design_guard.py)
    r = run([str(venv / "bin" / "python"), str(dev / "tools" / "design_guard.py")], user=s.runner_user, check=False)
    if r.returncode != 0:
        raise OpsError(f"{env.name}: a raw design value outside the tokens — use a token:\n{(r.stdout or r.stderr).strip()}")
    log.info("%s: design within the tokens", env.name)
    # the core does not import the edge (canon: architecture guidelines AG-4)
    r = run([str(venv / "bin" / "python"), str(dev / "tools" / "arch_guard.py")], user=s.runner_user, check=False)
    if r.returncode != 0:
        raise OpsError(f"{env.name}: the core reaches out to the edge:\n{(r.stdout or r.stderr).strip()}")
    log.info("%s: architecture boundaries hold", env.name)
    worlds = d / "worlds"
    seeded = Path("/opt/casefile/demo/worlds")
    if not (worlds / "claims").is_dir():                   # the sample worlds, once: the richer seed when it is on the machine, else the built-in ones
        if (seeded / "claims").is_dir():
            run(["cp", "-a", str(seeded), str(worlds)])
            run(["chown", "-R", f"{s.runner_user}:{s.runner_user}", str(worlds)])
            log.info("%s: sample worlds copied from %s", env.name, seeded)
        else:
            run([str(venv / "bin" / "python"), "-m", "casefile.demo.worlds", str(worlds)], user=s.runner_user)
            log.info("%s: sample worlds built", env.name)
    for name in WORLDS_LATER:                              # worlds that came after the first seed: added when the seed has them
        if not (worlds / name).is_dir() and (seeded / name).is_dir():
            run(["cp", "-a", str(seeded / name), str(worlds / name)])
            run(["chown", "-R", f"{s.runner_user}:{s.runner_user}", str(worlds / name)])
            log.info("%s: world %s copied from %s", env.name, name, seeded)
    return commit


def notes_worktree(settings: Settings, env: Env) -> Path | None:
    """The stage's notes branch as a worktree of the shared control (ADR-019): the agents' folders the stage writes
    into. Built once; from then on the runner keeps it on top of main and pushes what agents learn to the notes
    remote. Control's main is never written from here. None when the stage has no notes branch."""
    s = settings.server
    if not env.notes_branch:
        return None
    tree = env.dir(s) / "notes"
    control = s.shared / "control"
    if s.notes_remote:
        if run(["git", "-C", str(control), "remote", "get-url", "notes"], user=s.runner_user, check=False).returncode != 0:
            run(["git", "-C", str(control), "remote", "add", "notes", s.notes_remote], user=s.runner_user)
        else:
            run(["git", "-C", str(control), "remote", "set-url", "notes", s.notes_remote], user=s.runner_user)
    if (tree / ".git").exists():
        return tree
    run(["git", "-C", str(control), "fetch", "--quiet", "origin", "main"], user=s.runner_user)
    start = "origin/main"
    if s.notes_remote and run(["git", "-C", str(control), "fetch", "--quiet", "notes", env.notes_branch], user=s.runner_user, check=False).returncode == 0:
        start = "FETCH_HEAD"                           # what this stage learned before survives a rebuilt worktree
    run(["git", "-C", str(control), "worktree", "add", "--quiet", "-B", env.notes_branch, str(tree), start], user=s.runner_user)
    log.info("%s: notes worktree %s on %s (from %s)", env.name, tree, env.notes_branch, start)
    return tree


def seed_workspaces(settings: Settings, env: Env, folder_id: int) -> Path:
    """The registry of this stage: the applications from the checkout, the shared PressRoom on the team folder
    (read from the disk, written through the mount), and — on a showcase stage — the sample and demo workspaces from
    the worlds. Written once; the workspaces are added whenever they are missing (idempotent)."""
    s = settings.server
    d = env.dir(s)
    cp = d / "cockpit"
    reg = cp / "workspaces.json"
    cfg = d / "develop" / "apps" / "casefile" / "config"
    if not reg.exists():
        doc = {
            "$comment": "Seeded by pressroom-env; from here on `cockpit workspace …` and the cockpit itself edit it.",
            "applications": {
                "pressroom": {"label": "PressRoom", "config_dir": str(cfg / "pressroom"), "mode": "live"},
                "claims": {"label": "Schadenakte", "config_dir": str(cfg / "claims-demo"), "template": str(d / "worlds" / "claims"), "mode": "replay"},
                "egutachten": {"label": "Gutachtenakte", "config_dir": str(cfg / "egutachten"), "template": str(d / "worlds" / "egutachten"), "mode": "replay"},
            },
            "workspaces": [
                {"id": "pressroom", "application": "pressroom", "label": "PressRoom", "shared": True, "members": ["chris", "akhil"],
                 "root": str(s.groupfolders_data / str(folder_id) / "files" / "flow"), "write_root": str(env.mount / "flow"), "mode": "live"},
            ],
        }
        reg.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); _own(reg, s.runner_user)
    data = json.loads(reg.read_text(encoding="utf-8"))
    if "agents" in (data.get("defaults") or {}):      # ADR-020: agents left the workspace for the person's account
        data["defaults"].pop("agents")
        if not data["defaults"]:
            data.pop("defaults")
        reg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); _own(reg, s.runner_user)
    renamed = False
    for w in data["workspaces"]:                       # the stage is the badge, not part of a name (Chris, 2026-10-28)
        if w.get("id") == "pressroom" and w.get("label") == f"PressRoom {env.label}":
            w["label"], renamed = "PressRoom", True
    if renamed:
        reg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); _own(reg, s.runner_user)
    # applications that came after the registry was written (ADR-021: Gatehouse), added once their world is on the stage
    later = {"gatehouse": {"label": "Gatehouse", "config_dir": str(cfg / "gatehouse"), "template": str(d / "worlds" / "gatehouse-live"), "mode": "live"},
             "gatehouse-muster": {"label": "Gatehouse · Muster", "config_dir": str(cfg / "gatehouse"), "template": str(d / "worlds" / "gatehouse"), "mode": "replay"},
             "gatehouse-vorfuehrung": {"label": "Gatehouse · Vorführung", "config_dir": str(cfg / "gatehouse"), "template": str(d / "worlds" / "gatehouse-demo"), "mode": "live"},
             "posteingang": {"label": "Posteingang", "config_dir": str(cfg / "posteingang"), "template": str(d / "worlds" / "posteingang-live"), "mode": "live"},
             "posteingang-muster": {"label": "Posteingang · Muster", "config_dir": str(cfg / "posteingang"), "template": str(d / "worlds" / "posteingang"), "mode": "replay"},
             "angebot": {"label": "Angebotsakte", "config_dir": str(cfg / "angebot"), "template": str(d / "worlds" / "angebot-live"), "mode": "live"},
             "angebot-muster": {"label": "Angebotsakte · Muster", "config_dir": str(cfg / "angebot"), "template": str(d / "worlds" / "angebot"), "mode": "replay"},
             "bestandsakte": {"label": "Bestandsakte", "config_dir": str(cfg / "bestandsakte"), "template": str(d / "worlds" / "bestandsakte"), "mode": "replay"},
             "aenderungsakte": {"label": "Änderungsakte", "config_dir": str(cfg / "aenderungsakte"), "template": str(d / "worlds" / "aenderungsakte"), "mode": "replay"},
             # the PressRoom sample (2026-10-29): real pieces on the stages one flow needs; not the public demo's sandbox world `pressroom`
             "pressroom-muster": {"label": "PressRoom · Muster", "config_dir": str(cfg / "pressroom"), "template": str(d / "worlds" / "pressroom-muster"), "mode": "replay"}}
    grew = [k for k, v in later.items() if k not in data["applications"] and Path(v["template"]).is_dir()]
    for k in grew:
        data["applications"][k] = later[k]
    if grew:
        reg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); _own(reg, s.runner_user)
        log.info("%s: applications added: %s", env.name, ", ".join(grew))
    have = {w["id"] for w in data["workspaces"]}
    venv = cp / ".venv"
    added = []
    # what we use and show lives where production lives; a clone stage carries the PressRoom alone and gets a sample when a test needs one
    samples = [("schadenakte-muster", "claims", "Schadenakte · Muster", []), ("gutachtenakte-muster", "egutachten", "Gutachtenakte · Muster", []),
               ("gatehouse-muster", "gatehouse-muster", "Gatehouse · Muster", []), ("gatehouse", "gatehouse", "Gatehouse", ["chris", "akhil"]),
               ("gatehouse-vorfuehrung", "gatehouse-vorfuehrung", "Gatehouse · Vorführung", ["chris"]),
               ("posteingang-muster", "posteingang-muster", "Posteingang · Muster", []), ("posteingang", "posteingang", "Posteingang", ["chris"]),
               ("angebot-muster", "angebot-muster", "Angebotsakte · Muster", []),
               ("bestandsakte-muster", "bestandsakte", "Bestandsakte · Muster", []), ("aenderungsakte-muster", "aenderungsakte", "Änderungsakte · Muster", []),
               ("pressroom-muster", "pressroom-muster", "PressRoom · Muster", [])]
    if not env.showcase:
        samples = []
    for wid, app, label, members in samples:
        if wid in have or app not in data["applications"]:
            continue
        # argparse takes the config as a positional after the id, which the options swallow: run from the cockpit dir instead
        r = run([str(venv / "bin" / "cockpit"), "workspace", "create", wid, "--application", app, "--shared", "--label", label, *[x for m in members for x in ("--member", m)]],
                user=s.runner_user, cwd=str(cp), check=False)
        if r.returncode != 0:
            log.warning("%s: sample workspace %s not created: %s", env.name, wid, (r.stderr or r.stdout).strip()[-300:])
        else:
            added.append(wid)
    if added:
        data = json.loads(reg.read_text(encoding="utf-8"))
        for w in data["workspaces"]:
            if w["id"] in added and w.get("mode") == "replay":
                w["open_identity"] = True              # sample worlds keep the person picker: their people are invented
        reg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _connect_targets(data, cp, cfg, s)
    log.info("%s: workspaces: %s", env.name, ", ".join(w["id"] for w in data["workspaces"]))
    return reg


def _connect_targets(data: dict, cp: Path, cfg: Path, s) -> None:
    """ADR-022: an inbox hands a confirmed mail to another application; which tree that is, the stage decides here — the
    inboxes write into the claims and quote sample worlds of the same stage. Written into each inbox's tree as targets.json, every
    deploy, so a rebuilt sample world finds its target again."""
    ws = {w["id"]: w for w in data["workspaces"]}

    def tree(w: dict) -> Path:
        r = Path(w.get("write_root") or w["root"])
        return r if r.is_absolute() else cp / r

    targets = {}
    if ws.get("schadenakte-muster"):
        targets["schadenakte"] = {"label": "Schadenakte · Muster", "root": str(tree(ws["schadenakte-muster"])), "config": str(cfg / "claims-demo"), "url": "../schadenakte-muster", "external_prefix": "SN-"}
    if ws.get("angebot-muster"):                       # the agency case (2026-10-27): quote requests open a quote file
        targets["angebot"] = {"label": "Angebotsakte · Muster", "root": str(tree(ws["angebot-muster"])), "config": str(cfg / "angebot"), "url": "../angebot-muster", "external_prefix": "AN-"}
    # the claims and the assessor's sample worlds hand an order and the e-report to each other (the demo's GDV stand-in)
    pairs = {"schadenakte-muster": {"egutachten": ("gutachtenakte-muster", "egutachten", "Gutachtenakte · Muster")},
             "gutachtenakte-muster": {"claims": ("schadenakte-muster", "claims-demo", "Schadenakte · Muster")}}
    plan = {wid: targets for wid in ("posteingang", "posteingang-muster") if targets}
    for wid, partners in pairs.items():
        got = {key: {"label": label, "root": str(tree(ws[other])), "config": str(cfg / conf)} for key, (other, conf, label) in partners.items() if other in ws}
        if got:
            plan[wid] = got
    for wid, doc in plan.items():
        w = ws.get(wid)
        if not w:
            continue
        r = tree(w)
        if r.is_dir():
            (r / "targets.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            _own(r / "targets.json", s.runner_user)


def write_cockpit_config(settings: Settings, env: Env, folder_id: int) -> Path:
    s = settings.server
    cp = env.dir(s) / "cockpit"
    toml = _render("cockpit.toml", env=env.name, label=env.label, port=env.port, base_path=env.base_path,
                   users_json=s.users_json, cookie_secret=s.cookie_secret, accounts=s.users_json.parent / "accounts",
                   agents=s.shared / "control" / "shared-context" / "agents",
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
