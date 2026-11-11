#!/usr/bin/env python3
"""The design sandbox: the cockpit and its sample applications on one Mac, offline, with fictional data only.

    python3 sandbox/sandbox.py setup      once (needs the network): Python environment, the web surface, a headless browser
    python3 sandbox/sandbox.py up         start: http://127.0.0.1:8200, sign in as designer / sandbox-local; the surface rebuilds on save
    python3 sandbox/sandbox.py reset      every workspace back to its sample world
    python3 sandbox/sandbox.py check      the design guard, then every sample flow and walk headless; screenshots per step in sandbox/.state/check/
    python3 sandbox/sandbox.py check ID…  only these flows or walks (CI plays one per machine, in parallel)
    python3 sandbox/sandbox.py ids        every flow and walk id as JSON — the CI matrix
    python3 sandbox/sandbox.py ids B H    only the checks the change B..H needs: its applications' flows and walks, all of them
                                          when the core changed, none for docs or unit tests (the rules: `touched`)

    SANDBOX_PREBUILT=1 plays an existing web/dist and skips the guards (when both were just done by another step).

The worlds in `sandbox/worlds/` are exported from the private demo builder (`demo.py sandbox`), with a name scan as the gate.
The PressRoom here is casefile's built-in fictional one. Nothing in this folder talks to a server; `.state/` is yours to break.
See SANDBOX.md for what to change and how to hand it back.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CASEFILE = REPO / "apps" / "casefile"
COCKPIT = REPO / "apps" / "cockpit"
WEB = CASEFILE / "web"
CFG = CASEFILE / "config"
WORLDS = HERE / "worlds"
STATE = HERE / ".state"
VENV = HERE / ".venv"
PY = VENV / "bin" / "python"
PORT = int(os.environ.get("SANDBOX_PORT", "8200"))
USER, PASSWORD = "designer", "sandbox-local"

# workspace id → (world, configuration, label); the ids are the ones production uses, so the flows find them
SPACES = {
    "posteingang-muster": ("posteingang", "posteingang", "Posteingang · Muster"),
    "angebot-muster": ("angebot", "angebot", "Angebotsakte · Muster"),
    "schadenakte-muster": ("claims", "claims-demo", "Schadenakte · Muster"),
    "gutachtenakte-muster": ("egutachten", "egutachten", "Gutachtenakte · Muster"),
    "pressroom-muster": ("pressroom", "pressroom", "PressRoom · Muster"),
}
# mounted for the checks only, not offered in `up`: a world no demo flow plays, kept for a walk
CHECK_SPACES = {
    "shipyard-muster": ("shipyard", "shipyard", "Shipyard · Muster"),     # nine stations, the longest station line
}


def sh(cmd: list[str], **kw) -> None:
    print("·", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def in_venv() -> None:
    """Every command but setup runs with the sandbox's own Python."""
    if not PY.exists():
        sys.exit("No environment yet — run: python3 sandbox/sandbox.py setup")
    if Path(sys.prefix).resolve() != VENV.resolve():
        os.execv(str(PY), [str(PY), __file__, *sys.argv[1:]])


# ----------------------------------------------------------------------------- setup

def setup() -> None:
    if sys.version_info < (3, 11):
        sys.exit(f"Python 3.11 or newer is needed (this is {sys.version.split()[0]}) — brew install python@3.12, then python3.12 sandbox/sandbox.py setup")
    if not shutil.which("node") or not shutil.which("npm"):
        sys.exit("Node.js is needed — brew install node")
    if not VENV.exists():
        sh([sys.executable, "-m", "venv", VENV])
    sh([PY, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    sh([PY, "-m", "pip", "install", "-q", "-e", CASEFILE, "-e", COCKPIT])
    sh(["npm", "ci", "--silent"], cwd=WEB)
    if os.environ.get("SANDBOX_PREBUILT") != "1":           # an existing build is kept when the caller just made it
        sh(["npm", "run", "build", "--silent"], cwd=WEB)
    sh(["npx", "playwright", "install", "chromium"], cwd=WEB)
    print("\nReady. Start with: python3 sandbox/sandbox.py up")


# ----------------------------------------------------------------------------- the state: trees, registry, cockpit

def world_dir(world: str) -> Path:
    return STATE / "worlds" / world if world == "pressroom" else WORLDS / world


def build_pressroom() -> None:
    from casefile.demo.worlds import build_pressroom as build
    dest = STATE / "worlds" / "pressroom"
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    build(dest)


def fill(ws: str) -> Path:
    from casefile.demo.sandbox import copy_world
    tree = STATE / "workspaces" / ws / "flow"
    shutil.rmtree(tree, ignore_errors=True)
    tree.mkdir(parents=True)
    copy_world(world_dir(SPACES[ws][0]), tree)
    return tree


def connect(tree_of) -> None:
    """The hand-offs, as production wires them: the inbox writes into the claims and quote samples; claims and assessor trade."""
    out = {"schadenakte": {"label": "Schadenakte · Muster", "root": str(tree_of("schadenakte-muster")), "config": str(CFG / "claims-demo"), "url": "../schadenakte-muster", "external_prefix": "SN-"},
           "angebot": {"label": "Angebotsakte · Muster", "root": str(tree_of("angebot-muster")), "config": str(CFG / "angebot"), "url": "../angebot-muster", "external_prefix": "AN-"}}
    plan = {"posteingang-muster": out,
            "schadenakte-muster": {"egutachten": {"label": "Gutachtenakte · Muster", "root": str(tree_of("gutachtenakte-muster")), "config": str(CFG / "egutachten")}},
            "gutachtenakte-muster": {"claims": {"label": "Schadenakte · Muster", "root": str(tree_of("schadenakte-muster")), "config": str(CFG / "claims-demo")}}}
    for ws, doc in plan.items():
        (tree_of(ws) / "targets.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


COCKPIT_TOML = """# The cockpit of the design sandbox. Written by sandbox.py; `reset` writes it again.
[cockpit]
name = "Cockpit"
locale = "de"
bind = "127.0.0.1:{port}"
environment = "sandbox"
default_role = "operator"
audit = "cockpit-audit.jsonl"
users = "users.json"
workspaces = "workspaces.json"
secret = ".cockpit-secret"
people = "pipeline:people.json"
plugins = "plugins"
stale_after_hours = 720

[[source]]
id = "pipeline"
label = "PressRoom"
path = "{pipeline}"
mode = "read-write"
sensitivity = "internal"

[[role]]
id = "operator"
modules = ["*"]
max_sensitivity = "confidential"
actions = ["*"]
"""


def init() -> None:
    shutil.rmtree(STATE, ignore_errors=True)
    STATE.mkdir()
    build_pressroom()
    trees = {ws: fill(ws) for ws in SPACES}
    connect(trees.__getitem__)
    reg = {"$comment": "The sandbox's applications and workspaces. Written by sandbox.py.",
           "applications": {ws: {"label": label, "config_dir": str(CFG / conf), "template": str(world_dir(world)), "mode": "replay"}
                            for ws, (world, conf, label) in SPACES.items()},
           "workspaces": [{"id": ws, "application": ws, "label": label, "root": str(trees[ws]), "shared": True, "members": [USER],
                           "mode": "replay", "open_identity": True} for ws, (_, _, label) in SPACES.items()]}
    (STATE / "workspaces.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (STATE / "plugins").mkdir()
    toml = STATE / "cockpit.toml"
    toml.write_text(COCKPIT_TOML.format(port=PORT, pipeline=trees["pressroom-muster"]), encoding="utf-8")
    # the configuration is found as cockpit.toml in the working directory: some Python versions let the options swallow a trailing positional
    sh([VENV / "bin" / "cockpit", "user", "add", USER, "--role", "operator", "--password", PASSWORD], cwd=STATE, stdout=subprocess.DEVNULL)


def reset() -> None:
    init()
    print(f"Every workspace is back at its sample world ({STATE}).")


# ----------------------------------------------------------------------------- up

def up() -> None:
    if not (STATE / "cockpit.toml").exists():
        init()
    if not (WEB / "dist" / "index.html").exists():
        sh(["npm", "run", "build", "--silent"], cwd=WEB)
    # the surface rebuilds whenever a file under web/src changes: save, then reload the browser
    watch = subprocess.Popen(["npx", "vite", "build", "--watch", "--logLevel", "warn"], cwd=WEB)
    print(f"\nhttp://127.0.0.1:{PORT}   sign in as {USER} / {PASSWORD}   (Ctrl-C stops)\n", flush=True)
    try:
        subprocess.run([str(VENV / "bin" / "cockpit"), "run", str(STATE / "cockpit.toml")], cwd=STATE)
    except KeyboardInterrupt:
        pass
    finally:
        watch.terminate()


# ----------------------------------------------------------------------------- check

# surface behaviour no demo flow presses, walked on its own after the flows — declared in walks.json, not here:
# id, script in web/walks, the workspaces it plays (passed to the script in this order), the requirement lines it proves
def walks() -> list[dict]:
    return json.loads((HERE / "walks.json").read_text(encoding="utf-8"))


def flows() -> list[dict]:
    seen: dict[str, dict] = {}
    for f in sorted(WORLDS.glob("*/_ablaeufe/*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        seen.setdefault(doc["id"], doc)
    return list(seen.values())


def stage_app(trees: Path):
    """Every sample workspace under /w/<id>, as the cockpit mounts it, without the sign-in: what the flows play against."""
    from casefile.api.app import Settings, create_app
    from casefile.demo.sandbox import copy_world
    from starlette.applications import Starlette
    import casefile
    pkg = Path(casefile.__file__).resolve().parent
    shutil.rmtree(trees, ignore_errors=True)
    spaces = {**SPACES, **CHECK_SPACES}
    for ws, (world, _, _) in spaces.items():
        (trees / ws).mkdir(parents=True)
        copy_world(world_dir(world), trees / ws)
    connect(lambda ws: trees / ws)
    shell = Starlette()
    for ws, (world, conf, _) in spaces.items():
        shell.mount(f"/w/{ws}", create_app(Settings(
            root=trees / ws, config_dir=CFG / conf, label=ws, open_identity=True, secret="sandbox", stage="check", shell="/",
            web_dist=WEB / "dist", demo=True, template=world_dir(world), samples_dir=pkg / "demo" / "samples", replies_dir=pkg / "demo" / "replies")))
    return shell


# ----------------------------------------------------------------------------- which checks a change needs

# A check (flow or walk) names the workspaces it plays; a workspace names its world and its configuration. A change touches
# applications through their configuration or their world, or it touches the core — and then every check runs. Paths that
# no check plays (documentation, unit tests, the cockpit shell, deploy tooling, guards) select nothing.
NO_CHECK = ("docs/", "apps/casefile/tests/", "apps/cockpit/", "infra/", "tools/")
BY_CONFIG = re.compile(r"^apps/casefile/config/([^/]+)/")
BY_WORLD = re.compile(r"^sandbox/worlds/([^/]+)/")
BY_WALK = re.compile(r"^apps/casefile/web/(walks/[^/]+)$")


def touched(files: list[str]) -> tuple[bool, set[str], set[str]]:
    """(everything, configurations, walk scripts) a list of changed paths reaches."""
    spaces = {**SPACES, **CHECK_SPACES}
    confs: set[str] = set()
    scripts: set[str] = set()
    for f in files:
        if not f or f.endswith(".md") or f.startswith(NO_CHECK):
            continue
        if m := BY_CONFIG.match(f):
            confs.add(m.group(1))
        elif m := BY_WORLD.match(f):
            confs |= {conf for world, conf, _ in spaces.values() if world == m.group(1)}
        elif m := BY_WALK.match(f):
            scripts.add(m.group(1))
        elif f == "sandbox/walks.json":
            continue                                            # a walk's declaration: the walk's own script decides
        else:
            return True, set(), set()                           # the core, the surface, the sandbox, CI: every check
    return False, confs, scripts


def selected(files: list[str] | None) -> list[str]:
    """The ids of the checks a change needs; every id when no change is given."""
    spaces = {**SPACES, **CHECK_SPACES}
    conf_of = lambda ws: spaces[ws][1] if ws in spaces else None
    every = [f["id"] for f in flows()] + [w["id"] for w in walks()]
    if files is None:
        return every
    allof, confs, scripts = touched(files)
    if allof:
        return every
    out = [f["id"] for f in flows() if any(conf_of(ws) in confs for ws in f["workspaces"])]
    out += [w["id"] for w in walks() if w["script"] in scripts or any(conf_of(ws) in confs for ws in w["workspaces"])]
    return out


def changed(base: str, head: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", base, head], capture_output=True, text=True, check=True)
    return [x for x in r.stdout.splitlines() if x.strip()]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def check(only: list[str]) -> int:
    out = STATE / "check"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    if not (STATE / "worlds" / "pressroom").exists():
        build_pressroom()
    prebuilt = os.environ.get("SANDBOX_PREBUILT") == "1"     # the caller built the surface and ran the guards just now
    if not prebuilt:
        # the design guard first: colour, type and radius from the tokens (the same gate the deploy holds)
        guard = subprocess.run([str(PY), str(REPO / "tools" / "design_guard.py")])
        if guard.returncode == 0:
            guard = subprocess.run([str(PY), str(REPO / "tools" / "arch_guard.py")])
        if guard.returncode != 0:
            print("\nA guard failed, so the flows were not played. `python3 tools/design_guard.py --list` shows what is left.")
            return 1
        sh(["npm", "run", "build", "--silent"], cwd=WEB, stdout=subprocess.DEVNULL)
    elif not (WEB / "dist" / "index.html").exists():
        print("SANDBOX_PREBUILT=1 but web/dist has no build")
        return 1
    port = free_port()
    server = subprocess.Popen([str(PY), __file__, "_stage", str(port)], stdout=open(out / "stage.log", "w"), stderr=subprocess.STDOUT)
    results = []
    try:
        time.sleep(4)
        for f in flows():
            if only and f["id"] not in only and f["suite"]["id"] not in only:
                continue
            first = next((x["ws"] for x in f["steps"] if x.get("ws")), next(iter(f["workspaces"])))
            t0 = time.time()
            r = subprocess.run(["node", "walks/director-shot.mjs", f"http://127.0.0.1:{port}", str(out / f["id"]), f["title"].split(" ")[0], first, f["id"]],
                               cwd=WEB, capture_output=True, text=True)
            tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
            ok = r.returncode == 0 and tail == "clean"
            results.append((f["id"], ok, "" if ok else (r.stdout + r.stderr).strip().splitlines()[-3:]))
            print(f"{'green' if ok else 'RED  '}  {f['suite']['id']:10} {f['id']:24} {round(time.time() - t0):>4} s", flush=True)
        for wk in walks():
            wid = wk["id"]
            if only and wid not in only:
                continue
            t0 = time.time()
            r = subprocess.run(["node", wk["script"], f"http://127.0.0.1:{port}", str(out / wid), *wk["workspaces"]], cwd=WEB, capture_output=True, text=True)
            tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
            ok = r.returncode == 0 and tail == "clean"
            results.append((wid, ok, "" if ok else (r.stdout + r.stderr).strip().splitlines()[-3:]))
            print(f"{'green' if ok else 'RED  '}  {'walk':10} {wid:24} {round(time.time() - t0):>4} s", flush=True)
    finally:
        server.terminate()
    for fid, ok, why in results:
        if not ok:
            print(f"\n{fid}:", *why, sep="\n  ")
    print(f"\nScreenshots: {out}")
    return 0 if results and all(ok for _, ok, _ in results) else 1


def _stage(port: str) -> None:
    import uvicorn
    uvicorn.run(stage_app(STATE / "check" / "trees"), host="127.0.0.1", port=int(port), log_level="warning")


if __name__ == "__main__":
    cmd, rest = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "setup":
        setup()
    elif cmd == "ids":
        # ids                  every check
        # ids BASE HEAD        the checks the change BASE..HEAD needs
        # ids --files P …      the checks these paths need (to try the rules)
        if rest[:1] == ["--files"]:
            print(json.dumps(selected(rest[1:])))
        elif len(rest) == 2:
            print(json.dumps(selected(changed(rest[0], rest[1]))))
        else:
            print(json.dumps(selected(None)))
    elif cmd in ("up", "reset", "check", "_stage"):
        in_venv()
        if cmd == "up":
            up()
        elif cmd == "reset":
            reset()
        elif cmd == "check":
            sys.exit(check(rest))
        else:
            _stage(rest[0])
    else:
        sys.exit(__doc__)
