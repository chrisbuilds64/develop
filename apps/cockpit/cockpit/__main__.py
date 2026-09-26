"""Entry point.

    cockpit run     [cockpit.toml] [--demo]
    cockpit check   [cockpit.toml] [--demo]        verify before anyone sits down in front of it
    cockpit export  [cockpit.toml] [--demo] [--out file.html] [--lang de] [--role guest] [--user name]
    cockpit init    [directory]                    write a commented cockpit.toml to start from

    cockpit plugin list    [cockpit.toml]
    cockpit plugin add     <path> [--link] [cockpit.toml]
    cockpit plugin remove  <id> [cockpit.toml]

    cockpit user add       <name> --role <role> --context <dir> [--password …] [cockpit.toml]
    cockpit user list      [cockpit.toml]
    cockpit user remove    <name> [cockpit.toml]

`--demo` runs against the fixtures shipped with the package: nothing from the
real machine is read, so the surface can be shown before anything is installed.
"""

from __future__ import annotations

import argparse
import getpass
import shutil
import sys
from pathlib import Path

from .config import Config, ConfigError, load

HERE = Path(__file__).parent
DEMO_CONFIG = HERE.parent / "fixtures" / "cockpit.demo.toml"
EXAMPLE = HERE.parent / "cockpit.example.toml"


def _config(args) -> Config:
    path = DEMO_CONFIG if getattr(args, "demo", False) else Path(args.config or "cockpit.toml")
    try:
        return load(path)
    except ConfigError as exc:
        sys.exit(f"cockpit cannot start: {exc}")


# ------------------------------------------------------------------- run / check / export

def cmd_run(args):
    import uvicorn
    from .app import create_app
    config = _config(args)
    app = create_app(config)
    print(f"{config.name} — {len(config.modules)} modules, "
          + ("sign-in required" if config.login_required else f"role '{config.default_role}'")
          + (" (demo)" if args.demo else ""))
    for mid, err in app.state.app_failures.items():
        print(f"  plugin app '{mid}' did not start: {err}")
    print(f"http://{config.host}:{config.port}")
    uvicorn.run(app, host=config.host, port=config.port, log_level="warning")


def cmd_check(args):
    """Everything that can fail in front of a client, checked in an empty room."""
    from .access import Access
    from .audit import AuditLog
    from .registry import build_cards, plugins_for
    from .users import Users
    config = _config(args)
    print(f"configuration  OK      {config.name}, {len(config.sources)} sources, "
          f"{len(config.modules)} modules, {len(config.roles)} roles")
    failures = 0
    plugins = plugins_for(config)
    for m in config.modules:
        p = plugins.get(m.plugin)
        print(f"plugin         {'OK     ' if p else 'MISSING'} {m.plugin:14} for module '{m.id}'"
              + (f" — {p.version}, {'bundled' if p.bundled else 'installed'}" if p else ""))
        failures += 0 if p else 1
    users = Users(config.users_path, config.secret_path)
    identities = [(n, users.get(n, config.base_dir)) for n in users.names()] or [(None, None)]
    if identities[0][0]:
        print(f"users          OK      {', '.join(n for n, _ in identities)} — sign-in required")
    else:
        print(f"users          none    running as role '{config.default_role}'")
    for name, user in identities:
        variables = user.as_vars() if user else {}
        access = Access(config, AuditLog(config.audit_path), variables)
        for sid, src in access._sources.items():
            if "{" in str(src.path):
                print(f"source         VAR     {sid} → {src.path}  (resolves per user)")
            elif src.path.exists():
                print(f"source         OK      {sid} → {src.path}" + (f"  [{name}]" if name else ""))
            else:
                print(f"source         MISSING {sid} → {src.path}" + (f"  [{name}]" if name else ""))
                failures += 1
        roles = [config.roles.get(user.role, config.role())] if user else [config.role(r) for r in config.roles]
        for role in roles:
            for card in build_cards(config, access, role):
                mark = {"ok": "OK     ", "denied": "denied ", "stale": "STALE  ",
                        "error": "ERROR  ", "invalid": "INVALID"}[card.verdict]
                print(f"module         {mark} {card.module_id:14} as {name or role.id}"
                      + (f" — {card.reason}" if card.reason else ""))
                if card.verdict in ("error", "invalid"):
                    failures += 1
                    for pr in card.problems:
                        print(f"                        {pr}")
    print("\nready." if not failures else f"\n{failures} problem(s).")
    return 0 if not failures else 1


def cmd_export(args):
    from .export import write
    config = _config(args)
    out = Path(args.out or "cockpit.html")
    write(config, out, lang=args.lang, role_id=args.role, user=args.user)
    print(f"written: {out} ({out.stat().st_size // 1024} KB)")


def cmd_init(args):
    target = Path(args.directory or ".") / "cockpit.toml"
    if target.exists():
        sys.exit(f"{target} already exists — not overwriting")
    shutil.copy(EXAMPLE, target)
    print(f"written: {target}\nEdit the [[source]] paths, then: cockpit check")


# ------------------------------------------------------------------- plugins

def cmd_plugin(args):
    from .plugins import PluginError, add, discover, load_manifest, remove
    config = _config(args)
    if args.sub == "list":
        found = discover(config.plugins_dir)
        used = {m.plugin for m in config.modules}
        for p in found.values():
            print(f"  {p.id:14} {p.version:8} {'bundled  ' if p.bundled else 'installed'}"
                  f"  {'app ' if p.app else '    '} {'in use' if p.id in used else '      '}  {p.name}")
        # manifests that failed validation, so a broken install is visible
        for base in (config.plugins_dir,):
            if base.is_dir():
                for d in sorted(base.iterdir()):
                    if (d / "plugin.json").is_file() and d.name not in {p.path.name for p in found.values()}:
                        try:
                            load_manifest(d)
                        except PluginError as exc:
                            print(f"  {d.name:14} INVALID   {exc}")
        return 0
    if args.sub == "add":
        try:
            p = add(Path(args.path), config.plugins_dir, link=args.link)
        except PluginError as exc:
            sys.exit(f"not added: {exc}")
        print(f"{'linked' if args.link else 'installed'}: {p.id} {p.version} → {p.path}")
        print(f"now add a [[module]] with plugin = \"{p.id}\" and release the sources it needs: "
              + ", ".join(p.manifest.get("needs", [])))
        return 0
    if args.sub == "remove":
        print("removed" if remove(args.id, config.plugins_dir) else "not installed", args.id)
        return 0


# ------------------------------------------------------------------- users

def cmd_user(args):
    from .users import Users
    config = _config(args)
    users = Users(config.users_path, config.secret_path)
    if args.sub == "add":
        if args.role not in config.roles:
            sys.exit(f"role '{args.role}' is not defined in the configuration")
        pw = args.password or getpass.getpass(f"password for {args.name}: ")
        users.add(args.name, pw, args.role, args.context, args.display or "")
        print(f"user {args.name}: role {args.role}, context {args.context}")
        return 0
    if args.sub == "list":
        for n in users.names():
            u = users.get(n, config.base_dir)
            print(f"  {n:14} {u.role:10} {u.context}")
        return 0
    if args.sub == "remove":
        ok = users.remove(args.name)
        if ok:
            users.save()
        print("removed" if ok else "no such user", args.name)
        return 0


# ------------------------------------------------------------------- argv

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cockpit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(s):
        s.add_argument("config", nargs="?")
        s.add_argument("--demo", action="store_true")

    for name, fn in (("run", cmd_run), ("check", cmd_check), ("export", cmd_export)):
        s = sub.add_parser(name); common(s); s.set_defaults(fn=fn)
        if name == "export":
            s.add_argument("--out"); s.add_argument("--lang"); s.add_argument("--role"); s.add_argument("--user")
    s = sub.add_parser("init"); s.add_argument("directory", nargs="?"); s.set_defaults(fn=cmd_init)

    pl = sub.add_parser("plugin"); pls = pl.add_subparsers(dest="sub", required=True)
    s = pls.add_parser("list"); common(s)
    s = pls.add_parser("add"); s.add_argument("path"); s.add_argument("--link", action="store_true"); common(s)
    s = pls.add_parser("remove"); s.add_argument("id"); common(s)
    pl.set_defaults(fn=cmd_plugin)

    us = sub.add_parser("user"); uss = us.add_subparsers(dest="sub", required=True)
    s = uss.add_parser("add"); s.add_argument("name"); s.add_argument("--role", required=True)
    s.add_argument("--context", required=True); s.add_argument("--password"); s.add_argument("--display"); common(s)
    s = uss.add_parser("list"); common(s)
    s = uss.add_parser("remove"); s.add_argument("name"); common(s)
    us.set_defaults(fn=cmd_user)

    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
