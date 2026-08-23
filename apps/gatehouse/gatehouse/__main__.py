"""Entry point: python -m gatehouse [config path] [--check]"""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

from .adapters import ModelError, Registry
from .api import create_app
from .audit import AuditLog
from .config import TASKS, Config, ConfigError, load
from .pack import PackError
from .pack import load as load_pack


def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv

    config_path = Path(argv[0] if argv else "gatehouse.toml")

    try:
        config = load(config_path)
    except ConfigError as exc:
        print(f"Gatehouse kann nicht starten: {exc}", file=sys.stderr)
        return 1

    if check_only:
        return check(config)

    try:
        app = create_app(config)
    except (PackError, ModelError) as exc:
        print(f"Gatehouse kann nicht starten: {exc}", file=sys.stderr)
        return 1

    print(f"Gatehouse — Pack {config.pack_path.name}, Instanz {config.instance_path}")
    _print_routing(config)
    print("Antworten gehen an: " + ", ".join(config.destinations))
    print(f"http://{config.host}:{config.port}")

    uvicorn.run(app, host=config.host, port=config.port, log_level="warning")
    return 0


def check(config: Config) -> int:
    """Verify the configuration before an operator sits down with a client.

    Every profile gets one real call. A sign-in that is missing, expired
    or pointed at the wrong account fails here, in an empty room, rather
    than in the third question of an interview.
    """
    print(f"Konfiguration: {config.pack_path}")
    failures = 0

    try:
        pack = load_pack(config.pack_path)
        questions = sum(len(b.questions) for b in pack.blocks)
        print(f"  Pack     OK      {' + '.join(pack.layers)} "
              f"({len(pack.blocks)} Blöcke, {questions} Fragen)")
    except PackError as exc:
        print(f"  Pack     FEHLER  {exc}")
        failures += 1

    print(f"  Instanz  OK      {config.instance_path}")
    _print_routing(config)

    audit = AuditLog(config.instance_path)
    for name in sorted(config.profiles):
        profile = config.profiles[name]
        if profile.adapter == "echo":
            print(f"  Profil   OK      {name}: sendet nichts")
            continue
        try:
            from .adapters import build
            model = build(profile, audit)
            model.ask("check", "Antworte mit genau einem Wort: bereit")
            print(f"  Profil   OK      {name}: "
                  f"{profile.model or profile.adapter} erreichbar")
        except ModelError as exc:
            print(f"  Profil   FEHLER  {name}: {exc}")
            failures += 1

    print("\nBereit." if not failures else f"\n{failures} Punkt(e) offen.")
    return 0 if not failures else 1


def _print_routing(config: Config) -> None:
    for task in TASKS:
        profile = config.profile_for(task)
        marker = "" if task in config.task_profiles else "  (Standard)"
        print(f"  Aufgabe  {task:12} -> {profile.name} "
              f"({profile.model or profile.adapter}){marker}")


if __name__ == "__main__":
    raise SystemExit(main())
