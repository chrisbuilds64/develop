"""Configuration: what the cockpit may see, what it shows, who sees what.

The cockpit refuses to start on a configuration it cannot fully understand
rather than falling back to a default. A silent default here would mean a
source is readable that nobody released, or a role sees a level nobody
granted — the two mistakes this file exists to make impossible.

Sources, modules and roles are the three segments. A module names the sources
it needs; a role names the modules it may open and the highest sensitivity it
may read. Deny is the default at every step.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

SENSITIVITY = ("public", "internal", "confidential")
MODES = ("read", "read-write")
KINDS = ("dir",)        # "http" comes with the same rules: named, released, per role, recorded
MATURITY = ("running", "draft", "planned", "assumption")


class ConfigError(Exception):
    """A message for the operator, not a stack trace."""


def _rank(sensitivity: str) -> int:
    return SENSITIVITY.index(sensitivity)


@dataclass(frozen=True)
class Source:
    id: str
    label: str
    path: Path
    kind: str = "dir"
    mode: str = "read"
    include: tuple[str, ...] = ()
    sensitivity: str = "internal"


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    type: str = "text"               # text | select | textarea | date
    required: bool = False
    options: tuple[str, ...] = ()
    placeholder: str = ""


@dataclass(frozen=True)
class Action:
    id: str
    label: str
    tool: str                        # a source id: the script must be released from it
    command: str                     # path inside that source
    args: tuple[str, ...]            # argv template; "{field}" is substituted
    fields: tuple[Field, ...] = ()
    data: str | None = None          # a source id the tool works on (sets COCKPIT_DATA_DIR)
    scope: str = "module"            # "module": on the module page · "document": on a document page, with {ref}
    stdin: str | None = None         # name of a field whose value goes to the tool on stdin


@dataclass(frozen=True)
class Module:
    id: str
    plugin: str                      # the plugin id; reader, app and locales come from its manifest
    sources: tuple[str, ...]
    maturity: str
    label: str | None = None
    enabled: bool = True
    actions: tuple[Action, ...] = ()
    app_config: Path | None = None   # handed to the plugin's app factory, if it has one


@dataclass(frozen=True)
class Role:
    id: str
    modules: tuple[str, ...]
    max_sensitivity: str
    actions: tuple[str, ...] = ()    # "module.action" names, or "*"

    def may_see(self, sensitivity: str) -> bool:
        return _rank(sensitivity) <= _rank(self.max_sensitivity)

    def may_open(self, module_id: str) -> bool:
        return "*" in self.modules or module_id in self.modules

    def may_act(self, action_name: str) -> bool:
        return "*" in self.actions or action_name in self.actions


@dataclass(frozen=True)
class Config:
    name: str
    locale: str
    host: str
    port: int
    default_role: str
    role_switch: bool
    audit_path: Path
    users_path: Path
    secret_path: Path
    plugins_dir: Path
    login_required: bool
    stale_after_hours: int
    sources: dict[str, Source]
    modules: list[Module]
    roles: dict[str, Role]
    base_dir: Path = field(default_factory=Path.cwd)
    def bind_path(self, p: Path) -> Path:
        p = Path(p).expanduser()
        return p if p.is_absolute() else (self.base_dir / p)

    def role(self, role_id: str | None = None) -> Role:
        return self.roles[role_id or self.default_role]


def _path(value: str, base: Path) -> Path:
    if "{" in value:
        return Path(value)          # a placeholder: bound per user later, relative to base then
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p)


def _need(table: dict, key: str, where: str):
    if key not in table:
        raise ConfigError(f"{where}: field '{key}' is missing")
    return table[key]


def _choice(value: str, allowed: tuple[str, ...], where: str, key: str) -> str:
    if value not in allowed:
        raise ConfigError(f"{where}: {key} = '{value}' is not allowed — one of: {', '.join(allowed)}")
    return value


def load(path: Path) -> Config:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"configuration not found: {path}")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path.name} is not valid TOML: {exc}") from exc
    base = path.resolve().parent

    top = raw.get("cockpit", {})
    bind = top.get("bind", "127.0.0.1:8200")
    host, _, port = bind.rpartition(":")
    if not host or not port.isdigit():
        raise ConfigError(f"[cockpit] bind = '{bind}' — expected 'host:port'")

    # --- sources ----------------------------------------------------------
    sources: dict[str, Source] = {}
    for i, s in enumerate(raw.get("source", []), 1):
        where = f"[[source]] Nr. {i}"
        sid = _need(s, "id", where)
        if sid in sources:
            raise ConfigError(f"{where}: id '{sid}' appears twice")
        sources[sid] = Source(
            id=sid,
            label=s.get("label", sid),
            path=_path(_need(s, "path", where), base),
            kind=_choice(s.get("kind", "dir"), KINDS, where, "kind"),
            mode=_choice(s.get("mode", "read"), MODES, where, "mode"),
            include=tuple(s.get("include", [])),
            sensitivity=_choice(s.get("sensitivity", "internal"), SENSITIVITY, where, "sensitivity"),
        )

    # --- modules ----------------------------------------------------------
    modules: list[Module] = []
    seen: set[str] = set()
    for i, m in enumerate(raw.get("module", []), 1):
        where = f"[[module]] Nr. {i}"
        mid = _need(m, "id", where)
        if mid in seen:
            raise ConfigError(f"{where}: id '{mid}' appears twice")
        seen.add(mid)
        needs = tuple(m.get("sources", []))
        for sid in needs:
            if sid not in sources:
                raise ConfigError(f"{where} ('{mid}'): source '{sid}' is not defined")
        actions = []
        for j, a in enumerate(m.get("action", []), 1):
            aw = f"{where} ('{mid}') [[module.action]] Nr. {j}"
            tool = a.get("tool", "plugin")
            if tool != "plugin" and tool not in sources:
                raise ConfigError(f"{aw}: tool source '{tool}' is not defined")
            data = a.get("data")
            if data and data not in sources:
                raise ConfigError(f"{aw}: data source '{data}' is not defined")
            if data and sources[data].mode != "read-write":
                raise ConfigError(f"{aw}: data source '{data}' is mode = \"read\" — an action that writes needs mode = \"read-write\"")
            fields = tuple(Field(
                name=_need(f, "name", aw), label=f.get("label", f["name"]),
                type=_choice(f.get("type", "text"), ("text", "select", "textarea", "date"), aw, "type"),
                required=bool(f.get("required", False)), options=tuple(f.get("options", [])),
                placeholder=f.get("placeholder", ""),
            ) for f in a.get("field", []))
            actions.append(Action(
                id=_need(a, "id", aw), label=a.get("label", a["id"]), tool=tool,
                command=_need(a, "command", aw), args=tuple(a.get("args", [])),
                fields=fields, data=data,
                scope=_choice(a.get("scope", "module"), ("module", "document"), aw, "scope"),
                stdin=a.get("stdin"),
            ))
        modules.append(Module(
            id=mid,
            plugin=m.get("plugin", mid),
            sources=needs,
            maturity=_choice(m.get("maturity", "running"), MATURITY, where, "maturity"),
            label=m.get("label"),
            enabled=bool(m.get("enabled", True)),
            actions=tuple(actions),
            app_config=_path(m["app_config"], base) if m.get("app_config") else None,
        ))

    # --- roles ------------------------------------------------------------
    roles: dict[str, Role] = {}
    for i, r in enumerate(raw.get("role", []), 1):
        where = f"[[role]] Nr. {i}"
        rid = _need(r, "id", where)
        if rid in roles:
            raise ConfigError(f"{where}: id '{rid}' appears twice")
        mods = tuple(r.get("modules", []))
        for mid in mods:
            if mid != "*" and mid not in seen:
                raise ConfigError(f"{where} ('{rid}'): module '{mid}' is not defined")
        roles[rid] = Role(
            id=rid,
            modules=mods,
            max_sensitivity=_choice(r.get("max_sensitivity", "public"), SENSITIVITY, where, "max_sensitivity"),
            actions=tuple(r.get("actions", [])),
        )
    if not roles:
        raise ConfigError("no [[role]] defined — without a role nobody sees anything, the operator included")

    default_role = top.get("default_role", next(iter(roles)))
    if default_role not in roles:
        raise ConfigError(f"[cockpit] default_role = '{default_role}' is not a defined role")

    return Config(
        name=top.get("name", "Cockpit"),
        locale=top.get("locale", "en"),
        host=host,
        port=int(port),
        default_role=default_role,
        # Off by default: with no sign-in, a switch is a way to pick any role.
        # Turn it on for a demo on your own machine, never on a shared one.
        role_switch=bool(top.get("role_switch", False)),
        audit_path=_path(top.get("audit", "cockpit-audit.jsonl"), base),
        users_path=_path(top.get("users", "users.json"), base),
        secret_path=_path(top.get("secret", ".cockpit-secret"), base),
        plugins_dir=_path(top.get("plugins", "plugins"), base),
        # With users on file, sign-in is required unless the config says otherwise.
        login_required=bool(top.get("login_required", (base / top.get("users", "users.json")).exists())),
        stale_after_hours=int(top.get("stale_after_hours", 24)),
        sources=sources,
        modules=modules,
        roles=roles,
        base_dir=base,
    )
