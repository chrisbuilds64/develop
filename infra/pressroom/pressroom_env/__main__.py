"""pressroom-env — the PressRoom's stages on one server: ENTW, TEST, PROD.

    pressroom-env status                       every stage: units, port, path, team folder
    pressroom-env create  <stage>              team folder + mount + code + cockpit + runner (idempotent)
    pressroom-env clone   <stage>              fresh test data: copy the stage it is cloned from
    pressroom-env deploy  <stage> [--ref R]    develop at a reference, cockpit reinstalled, units restarted
    pressroom-env nginx                        write the location snippet, test, reload
    pressroom-env render  <stage>              print what would be installed, install nothing

Configuration: envs.toml beside this package, or --config. Runs as root on the server; occ runs as the
Nextcloud site user, git and pip as the runner. Logs one line per step to stderr (the journal).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .clone import clone
from .config import OpsError, Settings, load
from .nextcloud import TeamFolders
from . import systemd, workspace

HERE = Path(__file__).resolve().parent
log = logging.getLogger("pressroom-env")


def _settings(args) -> Settings:
    return load(Path(args.config) if args.config else HERE.parent / "envs.toml")


def _root() -> None:
    if os.geteuid() != 0:
        raise OpsError("run as root (sudo): units, mounts and Nextcloud's files need it")


def cmd_status(args):
    st = _settings(args)
    folders = TeamFolders(st.server).list() if os.geteuid() == 0 else {}
    rows = systemd.status(st) if os.geteuid() == 0 else [{"stage": e.name, "port": e.port, "path": e.base_path or "/"} for e in st.envs.values()]
    for row, env in zip(rows, st.envs.values()):
        row["folder"] = f"{env.folder} (id {folders[env.folder]})" if env.folder in folders else f"{env.folder} (missing)"
        row["ref"] = env.ref
        if env.clone_from:
            row["clone_of"] = env.clone_from
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row['stage']:6} {row['path']:8} :{row['port']}  mount={row.get('mount', '-'):10} cockpit={row.get('cockpit', '-'):10} "
              f"runner={row.get('runner', '-'):10} {row['folder']}  ref={row['ref']}" + (f"  clone of {row['clone_of']}" if row.get("clone_of") else ""))
    return 0


def cmd_create(args):
    _root()
    st = _settings(args)
    env = st.env(args.stage)
    folders = TeamFolders(st.server)
    fid = folders.create(env.folder)
    workspace.deploy_code(st, env)
    workspace.write_cockpit_config(st, env, fid)
    workspace.seed_workspaces(st, env, fid)
    workspace.build_home(st, env, trust_from=Path(f"/home/{st.server.runner_user}/.claude.json"))
    names = systemd.install(st, env, folders.dav_url(env.folder))
    if env.clone_from and not (folders.files(fid) / "flow").is_dir():
        log.info("%s has no pipeline yet — cloning from %s", env.name, env.clone_from)
        clone(st, st.env(env.clone_from), env, folders)
    print(f"{env.name}: team folder {env.folder} (id {fid}), units {', '.join(names.values())}, "
          f"http://127.0.0.1:{env.port}{env.base_path}")
    return 0


def cmd_clone(args):
    _root()
    st = _settings(args)
    env = st.env(args.stage)
    if not env.clone_from:
        raise OpsError(f"stage '{env.name}' has no clone_from — it is a source, not a copy")
    folders = TeamFolders(st.server)
    out = clone(st, st.env(env.clone_from), env, folders)
    print(f"{env.name} ← {env.clone_from}: {out['files']} files, {out['transferred']} transferred, {out['seconds']} s")
    return 0


def cmd_deploy(args):
    _root()
    st = _settings(args)
    env = st.env(args.stage)
    folders = TeamFolders(st.server)
    ids = folders.list()
    if env.folder not in ids:
        raise OpsError(f"team folder {env.folder} missing — `create {env.name}` first")
    commit = workspace.deploy_code(st, env, args.ref)
    workspace.write_cockpit_config(st, env, ids[env.folder])
    workspace.seed_workspaces(st, env, ids[env.folder])
    workspace.build_home(st, env, trust_from=Path(f"/home/{st.server.runner_user}/.claude.json"))
    systemd.install(st, env, folders.dav_url(env.folder))
    print(f"{env.name}: {commit} deployed and restarted")
    return 0


def cmd_nginx(args):
    _root()
    st = _settings(args)
    changed = systemd.install_nginx(st)
    vhost = Path(f"/etc/nginx/sites-enabled/{st.server.host}.conf")
    print(("snippet updated" if changed else "snippet unchanged") + f": {st.server.nginx_snippet}")
    if not systemd.vhost_includes_snippet(st, vhost):
        print(f"NOTE: {vhost} does not include it yet — add inside the server block, before `location / {{`:\n"
              f"  include {st.server.nginx_snippet};")
    return 0


def cmd_render(args):
    st = _settings(args)
    env = st.env(args.stage)
    names = systemd.unit_names(env) if os.geteuid() == 0 else {"mount": "<mount>.mount", "cockpit": f"pressroom-cockpit-{env.name}.service", "runner": f"pressroom-runner-{env.name}.service"}
    d = env.dir(st.server)
    print(f"# stage {env.name}: dir {d}, units {names}\n")
    print(workspace._render("cockpit.toml", env=env.name, label=env.label, port=env.port, base_path=env.base_path,
                            users_json=st.server.users_json, cookie_secret=st.server.cookie_secret,
                            data=st.server.groupfolders_data / "<id>" / "files" / "flow", mount=env.mount / "flow"))
    print(systemd.nginx_snippet(st))
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S", stream=sys.stderr)
    p = argparse.ArgumentParser(prog="pressroom-env", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="envs.toml (default: beside the package)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_status)
    for name, fn in (("create", cmd_create), ("clone", cmd_clone), ("render", cmd_render)):
        s = sub.add_parser(name); s.add_argument("stage"); s.set_defaults(fn=fn)
    s = sub.add_parser("deploy"); s.add_argument("stage"); s.add_argument("--ref"); s.set_defaults(fn=cmd_deploy)
    s = sub.add_parser("nginx"); s.set_defaults(fn=cmd_nginx)
    args = p.parse_args(argv)
    try:
        return args.fn(args) or 0
    except OpsError as exc:
        log.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
