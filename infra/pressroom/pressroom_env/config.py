"""The stages and the server they live on — read from envs.toml, refused when incomplete.

One file describes everything the tool touches: where Nextcloud keeps team folders, who the runner
user is, and one table per stage (team folder, mount, port, URL prefix, code reference). Nothing here
has a hidden default that could point a TEST runner at the PROD folder; a missing field is an error
with a sentence, not a guess.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class OpsError(Exception):
    """A sentence for the operator, never a stack trace."""


@dataclass(frozen=True)
class Server:
    occ: Path                   # Nextcloud's occ
    php: str                    # the PHP binary occ runs with (CloudPanel ships several)
    nextcloud_user: str         # the site user that owns Nextcloud's files
    groupfolders_data: Path     # …/data/__groupfolders — team folder <id> lives at <id>/files
    nextcloud_group: str        # the group that may use the team folders
    dav_base: str               # WebDAV root of the runner's Nextcloud account
    davfs_secrets: Path         # /etc/davfs2/secrets — the runner's app password, one line per URL
    runner_user: str
    shared: Path                # checkouts every stage shares: canon/, control/
    envs_root: Path             # one directory per stage below here
    claude_bin: Path
    develop_repo: str
    users_json: Path            # the cockpits' one users file
    cookie_secret: Path         # the cockpits' one cookie secret
    runner_env_file: Path       # ANTHROPIC_API_KEY for the runners
    nginx_snippet: Path         # the location blocks, included by the vhost
    host: str


@dataclass(frozen=True)
class Env:
    name: str                   # "prod", "test", "entw" — also the stage label in the cockpit header
    label: str
    folder: str                 # Nextcloud team folder name
    mount: Path                 # davfs2 mount point of that folder
    port: int                   # the cockpit's local port
    base_path: str              # "" for the root, "/test" for a prefix
    ref: str                    # git ref of develop deployed to this stage
    clone_from: str             # the stage this one is cloned from; "" = never a clone target

    def dir(self, server: Server) -> Path:
        return server.envs_root / self.name

    @property
    def is_root(self) -> bool:
        return self.base_path == ""


@dataclass(frozen=True)
class Settings:
    server: Server
    envs: dict[str, Env]
    path: Path

    def env(self, name: str) -> Env:
        if name not in self.envs:
            raise OpsError(f"no stage '{name}' in {self.path.name} — defined: {', '.join(self.envs)}")
        return self.envs[name]


def _need(table: dict, key: str, where: str):
    if key not in table:
        raise OpsError(f"{where}: field '{key}' is missing")
    return table[key]


def load(path: Path) -> Settings:
    path = Path(path)
    if not path.is_file():
        raise OpsError(f"configuration not found: {path}")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise OpsError(f"{path.name} is not valid TOML: {exc}") from exc

    s = raw.get("server")
    if not isinstance(s, dict):
        raise OpsError(f"{path.name}: [server] is missing")
    w = "[server]"
    server = Server(
        occ=Path(_need(s, "occ", w)), php=str(_need(s, "php", w)),
        nextcloud_user=str(_need(s, "nextcloud_user", w)),
        groupfolders_data=Path(_need(s, "groupfolders_data", w)),
        nextcloud_group=str(_need(s, "nextcloud_group", w)),
        dav_base=str(_need(s, "dav_base", w)).rstrip("/"),
        davfs_secrets=Path(_need(s, "davfs_secrets", w)),
        runner_user=str(_need(s, "runner_user", w)),
        shared=Path(_need(s, "shared", w)), envs_root=Path(_need(s, "envs_root", w)),
        claude_bin=Path(_need(s, "claude_bin", w)), develop_repo=str(_need(s, "develop_repo", w)),
        users_json=Path(_need(s, "users_json", w)), cookie_secret=Path(_need(s, "cookie_secret", w)),
        runner_env_file=Path(_need(s, "runner_env_file", w)),
        nginx_snippet=Path(_need(s, "nginx_snippet", w)), host=str(_need(s, "host", w)),
    )

    envs: dict[str, Env] = {}
    ports: dict[int, str] = {}
    for name, e in (raw.get("env") or {}).items():
        w = f"[env.{name}]"
        if not name.isidentifier() or name != name.lower():
            raise OpsError(f"{w}: a stage name is lower-case letters, it becomes a unit and a directory name")
        base_path = str(e.get("base_path", "")).rstrip("/")
        if base_path and not base_path.startswith("/"):
            raise OpsError(f"{w}: base_path = '{base_path}' — expected '/{name}' or nothing for the root")
        port = int(_need(e, "port", w))
        if port in ports:
            raise OpsError(f"{w}: port {port} is already taken by stage '{ports[port]}'")
        ports[port] = name
        envs[name] = Env(
            name=name, label=str(e.get("label", name.upper())), folder=str(_need(e, "folder", w)),
            mount=Path(_need(e, "mount", w)), port=port, base_path=base_path,
            ref=str(e.get("ref", "main")), clone_from=str(e.get("clone_from", "")),
        )
    if not envs:
        raise OpsError(f"{path.name}: no [env.<name>] tables — nothing to manage")
    roots = [e.name for e in envs.values() if e.is_root]
    if len(roots) != 1:
        raise OpsError(f"{path.name}: exactly one stage serves the root (base_path = \"\"), found: {', '.join(roots) or 'none'}")
    for e in envs.values():
        if e.clone_from and e.clone_from not in envs:
            raise OpsError(f"[env.{e.name}]: clone_from = '{e.clone_from}' is not a stage")
        if e.clone_from == e.name:
            raise OpsError(f"[env.{e.name}]: a stage cannot be cloned from itself")
    folders = [e.folder for e in envs.values()]
    if len(set(folders)) != len(folders):
        raise OpsError(f"{path.name}: two stages name the same team folder — every stage has its own")
    return Settings(server=server, envs=envs, path=path)
