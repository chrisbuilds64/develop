"""Configuration: what the cockpit may see, what it shows, who sees what.

The cockpit refuses to start on a configuration it cannot fully understand
rather than falling back to a default. A silent default here would mean a
source is readable that nobody released, or a role sees a level nobody
granted — the two mistakes this file exists to make impossible.

Sources, modules and roles are the three segments. A module names the sources
it needs; a role names the modules it may open and the highest sensitivity it
may read. Deny is the default at every step.

Actions belong to plugins. A module inherits its plugin's actions, mapped onto
the sources the instance released (`needs` → `sources`, by position). The
instance may keep a subset (`actions = [...]`) and add its own `[[module.action]]`;
it cannot redefine one the plugin brings.
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
    type: str = "text"               # text | select | textarea | date | file
    accept: tuple[str, ...] = ()     # file: allowed extensions, e.g. ("png", "jpg")
    required: bool = False
    options: tuple[str, ...] = ()
    options_from: str = ""           # select: "<schema file>:<property>" in the action's data source — the value list lives there
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
    withheld: tuple[tuple[str, str], ...] = ()   # plugin actions not offered here, with the reason
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
    secure_cookies: bool
    max_upload_mb: int
    lockout_after: int
    lockout_minutes: int
    cache_seconds: int
    stale_after_hours: int
    people: tuple[str, str] | None     # (source id, file): the one list of persons — display names, check of logins
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


def _action(a: dict, aw: str, sources: dict[str, Source]) -> Action:
    """One action table → Action. `tool` is "plugin" or a source id; `data` a read-write source id."""
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
        type=_choice(f.get("type", "text"), ("text", "select", "textarea", "date", "file"), aw, "type"),
        required=bool(f.get("required", False)), options=tuple(f.get("options", [])),
        placeholder=f.get("placeholder", ""), accept=tuple(x.lower().lstrip(".") for x in f.get("accept", [])),
        options_from=str(f.get("options_from", "")),
    ) for f in a.get("field", []))
    for f in fields:
        if f.options_from and (":" not in f.options_from or not data):
            raise ConfigError(f"{aw}: field '{f.name}': options_from is '<file>:<path>' and needs a data source")
    return Action(
        id=_need(a, "id", aw), label=a.get("label", a["id"]), tool=tool,
        command=_need(a, "command", aw), args=tuple(a.get("args", [])),
        fields=fields, data=data,
        scope=_choice(a.get("scope", "module"), ("module", "document"), aw, "scope"),
        stdin=a.get("stdin"),
    )


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
    from .plugins import discover                 # here, not at the top: plugins import the panel checker
    plugins = discover(_path(top.get("plugins", "plugins"), base))
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
        # Actions: the plugin's first, mapped onto this module's sources by position
        # of `needs`; then the instance's own additions. Same id twice is a mistake.
        actions: list[Action] = []
        withheld: list[tuple[str, str]] = []
        only = m.get("actions")
        if only is not None and not isinstance(only, list):
            raise ConfigError(f"{where} ('{mid}'): actions = [...] lists the plugin actions to keep")
        plugin = plugins.get(m.get("plugin", mid))
        if plugin is not None:
            needs = list(plugin.manifest.get("needs", []))
            bound = dict(zip(needs, list(m.get("sources", []))))
            for a in plugin.manifest.get("actions", []):
                aw = f"{where} ('{mid}') plugin '{plugin.id}' action '{a.get('id', '?')}'"
                a = dict(a)
                if only is not None and a["id"] not in only:
                    continue
                # Offered only when everything it needs is released: the tool's source, and
                # the data source in read-write. Otherwise withheld — an instance that opens a
                # source for reading gets the reader, not the buttons. `cockpit check` says which.
                reason = None
                for key in ("tool", "data"):
                    name = a.get(key)
                    if name and name != "plugin":
                        if name not in bound:
                            reason = f"needs source '{name}' (position {needs.index(name) + 1} in sources)"
                            break
                        a[key] = bound[name]
                        if key == "data" and sources[bound[name]].mode != "read-write":
                            reason = f"source '{bound[name]}' is released read-only"
                            break
                if reason:
                    withheld.append((a["id"], reason))
                    continue
                actions.append(_action(a, aw, sources))
            if only is not None:
                known = {a.get("id") for a in plugin.manifest.get("actions", [])}
                for x in only:
                    if x not in known:
                        raise ConfigError(f"{where} ('{mid}'): actions = [...] names '{x}', which plugin '{plugin.id}' does not define")
        for j, a in enumerate(m.get("action", []), 1):
            aw = f"{where} ('{mid}') [[module.action]] Nr. {j}"
            act = _action(a, aw, sources)
            if any(x.id == act.id for x in actions):
                raise ConfigError(f"{aw}: id '{act.id}' is defined by the plugin — an instance adds actions, it does not redefine them")
            actions.append(act)
        modules.append(Module(
            id=mid,
            plugin=m.get("plugin", mid),
            sources=needs,
            maturity=_choice(m.get("maturity", "running"), MATURITY, where, "maturity"),
            label=m.get("label"),
            enabled=bool(m.get("enabled", True)),
            actions=tuple(actions),
            withheld=tuple(withheld),
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

    people = None
    if top.get("people"):
        sid, _, file = str(top["people"]).partition(":")
        if not file or sid not in sources:
            raise ConfigError(f"[cockpit] people = '{top['people']}' — expected '<source id>:<file>' with a defined source")
        people = (sid, file)

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
        secure_cookies=bool(top.get("secure_cookies", False)),      # true behind TLS
        max_upload_mb=int(top.get("max_upload_mb", 50)),
        lockout_after=int(top.get("lockout_after", 5)),
        lockout_minutes=int(top.get("lockout_minutes", 15)),
        cache_seconds=int(top.get("cache_seconds", 15)),          # listings and small reads over a slow mount; 0 = off
        stale_after_hours=int(top.get("stale_after_hours", 24)),
        people=people,
        sources=sources,
        modules=modules,
        roles=roles,
        base_dir=base,
    )
