"""Entry point.

    cockpit run    [cockpit.toml] [--demo]
    cockpit check  [cockpit.toml] [--demo]        verify before anyone sits down in front of it
    cockpit export [cockpit.toml] [--demo] [--out file.html] [--lang de] [--role guest]
    cockpit init   [directory]                    write a commented cockpit.toml to start from

`--demo` runs against the fixtures shipped with the package: nothing from the
real machine is read, so the surface can be shown before anything is installed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .config import Config, ConfigError, load

HERE = Path(__file__).parent
DEMO_CONFIG = HERE.parent / "fixtures" / "cockpit.demo.toml"
EXAMPLE = HERE.parent / "cockpit.example.toml"


def _config(args) -> Config:
    path = DEMO_CONFIG if args.demo else Path(args.config or "cockpit.toml")
    try:
        return load(path)
    except ConfigError as exc:
        sys.exit(f"cockpit cannot start: {exc}")


def cmd_run(args):
    import uvicorn
    from .app import create_app
    config = _config(args)
    app = create_app(config)
    print(f"{config.name} — {len(config.modules)} modules, role '{config.default_role}'"
          + (" (demo)" if args.demo else ""))
    print(f"http://{config.host}:{config.port}")
    uvicorn.run(app, host=config.host, port=config.port, log_level="warning")


def cmd_check(args):
    """Everything that can fail in front of a client, checked in an empty room."""
    from .access import Access, Denied
    from .audit import AuditLog
    from .registry import build_cards
    config = _config(args)
    print(f"configuration  OK      {config.name}, {len(config.sources)} sources, "
          f"{len(config.modules)} modules, {len(config.roles)} roles")
    failures = 0
    for sid, src in config.sources.items():
        if src.path.exists():
            print(f"source         OK      {sid} → {src.path}")
        else:
            print(f"source         MISSING {sid} → {src.path}")
            failures += 1
    access = Access(config, AuditLog(config.audit_path))
    for role_id in config.roles:
        for card in build_cards(config, access, config.role(role_id)):
            mark = {"ok": "OK     ", "denied": "denied ", "stale": "STALE  ",
                    "error": "ERROR  ", "invalid": "INVALID"}[card.verdict]
            print(f"module         {mark} {card.module_id:14} as {role_id}"
                  + (f" — {card.reason}" if card.reason else ""))
            if card.verdict in ("error", "invalid"):
                failures += 1
                for p in card.problems:
                    print(f"                        {p}")
    print("\nready." if not failures else f"\n{failures} problem(s).")
    return 0 if not failures else 1


def cmd_export(args):
    from .export import write
    config = _config(args)
    out = Path(args.out or "cockpit.html")
    write(config, out, lang=args.lang, role_id=args.role)
    print(f"written: {out} ({out.stat().st_size // 1024} KB)")


def cmd_init(args):
    target = Path(args.directory or ".") / "cockpit.toml"
    if target.exists():
        sys.exit(f"{target} already exists — not overwriting")
    shutil.copy(EXAMPLE, target)
    print(f"written: {target}\nEdit the [[source]] paths, then: cockpit check")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cockpit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", cmd_run), ("check", cmd_check), ("export", cmd_export)):
        s = sub.add_parser(name)
        s.add_argument("config", nargs="?")
        s.add_argument("--demo", action="store_true")
        s.set_defaults(fn=fn)
        if name == "export":
            s.add_argument("--out"); s.add_argument("--lang"); s.add_argument("--role")
    s = sub.add_parser("init"); s.add_argument("directory", nargs="?"); s.set_defaults(fn=cmd_init)
    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
