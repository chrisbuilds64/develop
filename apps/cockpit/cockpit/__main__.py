"""Entry point.

    cockpit run     [cockpit.toml] [--demo]
    cockpit check   [cockpit.toml] [--demo]        verify before anyone sits down in front of it
    cockpit export  [cockpit.toml] [--demo] [--out file.html] [--lang de] [--role guest] [--user name]
    cockpit init    [directory]                    write a commented cockpit.toml to start from

    cockpit plugin list    [cockpit.toml]
    cockpit plugin add     <path> [--link] [cockpit.toml]
    cockpit plugin remove  <id> [cockpit.toml]

    cockpit user add       <name> --role <role> [--context <dir>] [--password …] [cockpit.toml]
                           context defaults to home/<name>/context beside the configuration
    cockpit user list      [cockpit.toml]
    cockpit user remove    <name> [cockpit.toml]

    cockpit account show         <name> [cockpit.toml]            settings, and per secret: set since … or not set
    cockpit account set          <name> <key> <value>              billing = auto | subscription | api-key · locale = de | en
    cockpit account set-secret   <name> <KEY> [--stdin]            value asked for without echo (or read from stdin); never on the command line
    cockpit account clear-secret <name> <KEY>

    cockpit workspace list                                        [cockpit.toml]
    cockpit workspace create <id> --application <app> [--owner <name> | --shared] [--label …] [--from <workspace>] [--member <name>]…
    cockpit workspace remove <id> [--delete-files]

    cockpit agent templates                                       the organisation's job profiles ([cockpit] agents)
    cockpit team list      <name>                                 the person's hired agents, with engine, model and memory
    cockpit team hire      <name> <template> [--id …] [--model …] [--memory <path, {stage} allowed>]
    cockpit team dismiss   <name> <agent>                         leaves the team; the folder and memory are kept
    cockpit session list   <name> [--all]                         the person's running sessions on this stage; --all adds the closed
    cockpit session start  <name> <agent> --topic "…" [--workspace <id>]
    cockpit session say    <name> <session> "message"             queued for the runner
    cockpit session end    <name> <session> [--note "…"]          the agent writes the log, the lease is released
    cockpit session show   <name> <session>                       the record and the conversation

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
    print(f"http://{config.host}:{config.port}{config.base_path}" + (f"  ({config.environment})" if config.environment else ""))
    # root_path: the reverse proxy strips the prefix, uvicorn prepends it again and tells the app — so links,
    # redirects and cookies come out with the prefix while the routes stay what they are
    uvicorn.run(app, host=config.host, port=config.port, log_level="warning", root_path=config.base_path)


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
              + (f" — {p.version}, {'bundled' if p.bundled else 'installed'}" if p else "")
              + (f"; actions: {', '.join(a.id for a in m.actions)}" if m.actions else ""))
        for aid, why in m.withheld:
            print(f"               withheld {m.id}.{aid} — {why}")
        failures += 0 if p else 1
    users = Users(config.users_path, config.secret_path)
    identities = [(n, users.get(n, config.base_dir)) for n in users.names()] or [(None, None)]
    if identities[0][0]:
        print(f"users          OK      {', '.join(n for n, _ in identities)} — sign-in required")
        if config.people:
            import json
            sid, file = config.people
            path = config.sources[sid].path.expanduser() / file
            known = {x["id"] for x in json.loads(path.read_text(encoding="utf-8")).get("people", [])} if path.exists() else None
            if known is None:
                print(f"people         MISSING {sid}:{file} — display names fall back to the login, tools refuse to sign")
                failures += 1
            else:
                missing = [n for n, _ in identities if n not in known]
                for n in missing:
                    print(f"people         WARN    login '{n}' has no entry in {file}")
                if not missing:
                    print(f"people         OK      {sid}:{file} — {len(known)} listed, every login among them")
        else:
            print("people         none    no [cockpit] people = \"<source>:<file>\" — display names come from users.json")
    else:
        print(f"users          none    running as role '{config.default_role}'")
    for name, user in identities:
        variables = user.as_vars() if user else {}
        access = Access(config, AuditLog(config.audit_path), variables)
        for sid, src in access._sources.items():
            if "{" in str(src.path):
                print(f"source         VAR     {sid} → {src.path}  (resolves per user)")
            elif src.path.exists():
                print(f"source         OK      {sid} → {src.path}" + (f"  [{name}]" if name else "")
                      + (f"  (tools write to {src.tools_path})" if src.tools_path else ""))
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
        context = args.context or f"home/{args.name}/context"
        try:
            users.add(args.name, pw, args.role, context, args.display or "")
        except ValueError as exc:
            sys.exit(str(exc))
        ctx_dir = config.bind_path(Path(context))
        ctx_dir.mkdir(parents=True, exist_ok=True)
        print(f"user {args.name}: role {args.role}, context {ctx_dir}")
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


def cmd_account(args):
    from .account import AccountError, Accounts, SECRETS
    config = _config(args)
    accounts = Accounts(config.accounts_path)
    try:
        if args.sub == "show":
            st = accounts.status(args.name)
            print(f"{st['name']}: billing {st['billing']}" + (f", locale {st['locale']}" if st['locale'] else ""))
            for k, v in st["secrets"].items():
                print(f"  {k:26} {'set since ' + v['since'][:16] if v['set'] else 'not set'}")
        elif args.sub == "set":
            accounts.set(args.name, args.key, args.value)
            print(f"{args.name}: {args.key} = {args.value}")
        elif args.sub == "set-secret":
            if args.key not in SECRETS:
                sys.exit(f"'{args.key}' is not a secret an account can hold — one of: {', '.join(SECRETS)}")
            value = sys.stdin.readline() if args.stdin else getpass.getpass(f"{args.key} for {args.name}: ")
            accounts.set_secret(args.name, args.key, value)
            print(f"{args.name}: {args.key} set")
        elif args.sub == "clear-secret":
            print(f"{args.name}: {args.key} " + ("cleared" if accounts.clear_secret(args.name, args.key) else "was not set"))
    except AccountError as exc:
        sys.exit(str(exc))
    return 0


def cmd_workspace(args):
    from .workspaces import WorkspaceError, Workspaces
    config = _config(args)
    try:
        ws = Workspaces(config.workspaces_path, config.workspaces_path.parent)
        if args.sub == "list":
            for a in ws.applications.values():
                print(f"application {a.id:14} {a.label:18} {a.config_dir}" + (f"  template {a.template}" if a.template else ""))
            for w in ws.items:
                who = "shared" if w.shared else f"owner {w.owner}"
                print(f"workspace   {w.id:14} {w.label:18} {w.application:10} {who:16} {w.mode:6} {w.root}" + (f"  writes via {w.write_root}" if w.write_root else ""))
            if not ws.items:
                print(f"no workspaces in {ws.path}")
        elif args.sub == "create":
            if not args.shared and not args.owner:
                sys.exit("a workspace is shared (--shared) or has an owner (--owner <name>)")
            w = ws.create(args.id, args.application, None if args.shared else args.owner, label=args.label or "", source=getattr(args, 'from'),
                          shared=args.shared, members=args.member or [])
            print(f"workspace {w.id} ({w.application}) at {w.root}" + (f", copied from {w.cloned_from}" if w.cloned_from else "") + " — restart the cockpit to serve it")
        elif args.sub == "remove":
            print("removed" if ws.remove(args.id, delete_files=args.delete_files) else "no such workspace", args.id)
    except WorkspaceError as exc:
        sys.exit(str(exc))
    return 0


def _people(args):
    from .account import Accounts
    from .agents import Catalog
    config = _config(args)
    return config, Accounts(config.accounts_path), Catalog.load(config.agents_path), (config.environment or "prod").lower()


def cmd_agent(args):
    config, _, cat, _ = _people(args)
    if config.agents_path is None:
        sys.exit("no [cockpit] agents in the configuration — the organisation has no templates")
    for a in cat.agents.values():
        print(f"{a.id:12} {a.label:12} {a.engine:12} {a.model or '-':16} skills: {', '.join(a.skills) or '-':30} hire: {', '.join(a.users + a.roles) or 'everyone'}")
    for name, why in cat.problems.items():
        print(f"{name:12} BROKEN — {why}")
    return 0


def cmd_team(args):
    from .agents import AgentError
    _, accounts, cat, stage = _people(args)
    try:
        team = accounts.team(args.name, cat, stage)
        if args.sub == "list":
            for a in team.agents.values():
                print(f"{a.id:12} {a.label:12} from {a.template or '(own)':10} {a.engine:12} {a.model or '-':16} memory {a.notes_path}")
            for name, why in team.problems.items():
                print(f"{name:12} BROKEN — {why}")
            if not team.agents and not team.problems:
                print(f"{args.name} has nobody on the team")
        elif args.sub == "hire":
            a = team.hire(args.template, args.id, role=None if args.any_role else "operator", model=args.model, memory=args.memory)
            print(f"hired {a.id} ({a.label}) for {args.name} — memory {a.notes_path}")
        elif args.sub == "dismiss":
            print("dismissed" if team.dismiss(args.agent) else "no such agent", args.agent)
    except AgentError as exc:
        sys.exit(str(exc))
    return 0


def cmd_session(args):
    from .sessions import SessionError
    from .agents import AgentError
    _, accounts, cat, stage = _people(args)
    try:
        store = accounts.store(args.name, stage)
        if args.sub == "list":
            rows = store.active() + (store.closed() if args.all else [])
            for s in rows:
                print(f"{s.status:7} {s.id:56} {s.agent:10} {s.topic}" + (f"  @{s.workspace}" if s.workspace else ""))
            if not rows:
                print("no sessions")
        elif args.sub == "start":
            agent = accounts.team(args.name, cat, stage).get(args.agent)
            if agent is None:
                sys.exit(f"'{args.agent}' is not on {args.name}'s team")
            s, overlapping = store.start(agent.id, args.name, args.topic, {"workspace": args.workspace} if args.workspace else None)
            print(f"started {s.id}" + (f" — starts from {s.starts_from}" if s.starts_from else ""))
            for o in overlapping:
                print(f"warning: {o.id} is running with the same agent and topic (since {o.started})")
        elif args.sub == "say":
            print("queued", store.say(args.session, args.name, args.text)["id"])
        elif args.sub == "end":
            print("queued", store.end(args.session, args.name, args.note or "")["id"])
        elif args.sub == "show":
            s = store.get(args.session)
            if s is None:
                sys.exit("no such session")
            print(f"{s.id} — {s.status}, {s.agent} for {s.user}, since {s.started}" + (f", log {s.log}" if s.log else ""))
            for t in store.transcript(s.id):
                print(f"\n[{t['at']}] {t['role']}:\n{t['text']}")
    except (SessionError, AgentError) as exc:
        sys.exit(str(exc))
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
    s.add_argument("--context"); s.add_argument("--password"); s.add_argument("--display"); common(s)
    s = uss.add_parser("list"); common(s)
    s = uss.add_parser("remove"); s.add_argument("name"); common(s)
    us.set_defaults(fn=cmd_user)

    ac = sub.add_parser("account"); acs = ac.add_subparsers(dest="sub", required=True)
    s = acs.add_parser("show"); s.add_argument("name"); common(s)
    s = acs.add_parser("set"); s.add_argument("name"); s.add_argument("key"); s.add_argument("value"); common(s)
    s = acs.add_parser("set-secret"); s.add_argument("name"); s.add_argument("key"); s.add_argument("--stdin", action="store_true"); common(s)
    s = acs.add_parser("clear-secret"); s.add_argument("name"); s.add_argument("key"); common(s)
    ac.set_defaults(fn=cmd_account)

    wsp = sub.add_parser("workspace"); wss = wsp.add_subparsers(dest="sub", required=True)
    s = wss.add_parser("list"); common(s)
    s = wss.add_parser("create"); s.add_argument("id"); s.add_argument("--application", required=True); s.add_argument("--owner")
    s.add_argument("--shared", action="store_true"); s.add_argument("--label"); s.add_argument("--from", dest="from"); s.add_argument("--member", action="append"); common(s)
    s = wss.add_parser("remove"); s.add_argument("id"); s.add_argument("--delete-files", action="store_true"); common(s)
    wsp.set_defaults(fn=cmd_workspace)

    ag = sub.add_parser("agent"); ags = ag.add_subparsers(dest="sub", required=True)
    s = ags.add_parser("templates"); common(s)
    ag.set_defaults(fn=cmd_agent)

    tm = sub.add_parser("team"); tms = tm.add_subparsers(dest="sub", required=True)
    s = tms.add_parser("list"); s.add_argument("name"); common(s)
    s = tms.add_parser("hire"); s.add_argument("name"); s.add_argument("template"); s.add_argument("--id"); s.add_argument("--model")
    s.add_argument("--memory"); s.add_argument("--any-role", action="store_true", help="ignore the template's role restriction (operator use)"); common(s)
    s = tms.add_parser("dismiss"); s.add_argument("name"); s.add_argument("agent"); common(s)
    tm.set_defaults(fn=cmd_team)

    se = sub.add_parser("session"); ses = se.add_subparsers(dest="sub", required=True)
    s = ses.add_parser("list"); s.add_argument("name"); s.add_argument("--all", action="store_true"); common(s)
    s = ses.add_parser("start"); s.add_argument("name"); s.add_argument("agent"); s.add_argument("--topic", required=True); s.add_argument("--workspace"); common(s)
    s = ses.add_parser("say"); s.add_argument("name"); s.add_argument("session"); s.add_argument("text"); common(s)
    s = ses.add_parser("end"); s.add_argument("name"); s.add_argument("session"); s.add_argument("--note"); common(s)
    s = ses.add_parser("show"); s.add_argument("name"); s.add_argument("session"); common(s)
    se.set_defaults(fn=cmd_session)

    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
