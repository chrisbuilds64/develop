"""Workspaces: one pipeline tree under one application, personal or shared — and the casefile app that serves it.

The cockpit is the shell: who you are, what you may open. An **application** is a domain configuration for
the casefile core (PressRoom, Schadenakte, Gutachtenakte: `config/<domain>/`). A **workspace** is one tree of
folders under such an application, with an owner or shared, with members. Any number of them run side by
side; each is mounted under `/w/<id>/` with the cockpit's login as its identity.

The registry is one file beside `users.json`:

    {"applications": {"pressroom": {"label": "PressRoom", "config_dir": "…", "template": "…"}},
     "workspaces": [{"id": "pressroom", "application": "pressroom", "label": "PressRoom", "shared": true,
                     "members": ["chris", "akhil"], "root": "…/flow", "write_root": "…/flow", "mode": "live"}]}

A workspace carries **components** — named paths, each its own or shared with other workspaces: today only
`pipeline` (the tree; `root`/`write_root` are its older spelling and still read). Agents and sessions left the
workspace (ADR-020): they belong to the person, and a session carries its workspace as its place.

Creating one copies a source (the application's template, or a workspace the person may see; documents as
hard links, as in the demo sandbox), empties the queue and the journals, writes the entry, mounts at once.
Nothing here names a domain; the words come from the application's configuration.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{1,47}$")
MODES = ("live", "replay")
CLEARED = ("_runs", "_steps", "_audit")        # a copy starts without the source's orders, journals and audit
COMPONENTS = ("pipeline",)
RETIRED = ("agents", "sessions")                 # ADR-019 components, skipped when an older registry still names them


class WorkspaceError(Exception):
    """A sentence for the person, never a stack trace."""


@dataclass(frozen=True)
class Application:
    id: str
    label: str
    config_dir: Path
    template: Path | None = None               # a built tree to copy for a new workspace; None = start empty
    mode: str = "live"                         # the mode a new workspace of this application gets


@dataclass(frozen=True)
class Component:
    path: Path
    write_path: Path | None = None             # the same files through a mount, when writes must go that way
    shared: bool = False                       # other workspaces point here too: what is written here, they see
    writable: bool = True                      # false: read, never written (a git checkout the server does not commit)


@dataclass
class Workspace:
    id: str
    application: str
    label: str
    root: Path
    write_root: Path | None = None             # the same tree through a WebDAV mount, when writes must go that way
    shared: bool = False
    owner: str | None = None
    members: list[str] = field(default_factory=list)
    mode: str = "live"
    open_identity: bool = False                # true: a person picker instead of the cockpit's login (sample worlds)
    created: str = ""
    cloned_from: str | None = None
    components: dict[str, Component] = field(default_factory=dict)   # declared ones only; component() fills the defaults

    def visible_to(self, user: str | None) -> bool:
        return self.shared or (user is not None and (user == self.owner or user in self.members))


class Workspaces:
    def __init__(self, path: Path, base: Path):
        self.path = Path(path)
        self.base = Path(base)
        self.applications: dict[str, Application] = {}
        self.items: list[Workspace] = []
        self.defaults: dict[str, Component] = {}   # the stage's default per component (an `agents` directory for all)
        self.load()

    def component(self, w: Workspace, name: str) -> Component | None:
        """A workspace's component: declared, else the stage default, else the built-in place (`pipeline` = the tree)."""
        if name not in COMPONENTS:
            raise WorkspaceError(f"'{name}' is not a component — one of: {', '.join(COMPONENTS)}")
        if name in w.components:
            return w.components[name]
        if name in self.defaults:
            return self.defaults[name]
        return Component(path=w.root, write_path=w.write_root, shared=w.shared)

    def _components(self, raw: dict, where: str) -> dict[str, Component]:
        out = {}
        for name, c in (raw or {}).items():
            if name in RETIRED:
                continue
            if name not in COMPONENTS:
                raise WorkspaceError(f"{where}: '{name}' is not a component — one of: {', '.join(COMPONENTS)}")
            if not isinstance(c, dict) or not c.get("path"):
                raise WorkspaceError(f"{where}: component '{name}' needs a path")
            out[name] = Component(path=self._abs(c["path"]), write_path=self._abs(c.get("write_path")),
                                  shared=bool(c.get("shared", False)), writable=bool(c.get("writable", True)))
        return out

    # ---------------------------------------------------------------- file
    def _abs(self, value) -> Path | None:
        if not value:
            return None
        p = Path(str(value)).expanduser()
        return p if p.is_absolute() else (self.base / p)

    def load(self) -> None:
        self.applications, self.items, self.defaults = {}, [], {}
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise WorkspaceError(f"{self.path} is not valid JSON: {exc}") from exc
        for aid, a in (raw.get("applications") or {}).items():
            if not NAME.match(aid):
                raise WorkspaceError(f"application id '{aid}' — lower-case letters, digits, - and _")
            if not a.get("config_dir"):
                raise WorkspaceError(f"application '{aid}': config_dir is missing")
            self.applications[aid] = Application(id=aid, label=str(a.get("label", aid)), config_dir=self._abs(a["config_dir"]),
                                                 template=self._abs(a.get("template")), mode=str(a.get("mode", "live")))
        self.defaults = self._components(raw.get("defaults") or {}, "defaults")
        seen = set()
        for w in raw.get("workspaces") or []:
            wid = str(w.get("id", ""))
            if not NAME.match(wid):
                raise WorkspaceError(f"workspace id '{wid}' — lower-case letters, digits, - and _ (2 to 48)")
            if wid in seen:
                raise WorkspaceError(f"workspace '{wid}' appears twice")
            if w.get("application") not in self.applications:
                raise WorkspaceError(f"workspace '{wid}': application '{w.get('application')}' is not defined")
            if w.get("mode", "live") not in MODES:
                raise WorkspaceError(f"workspace '{wid}': mode must be one of {', '.join(MODES)}")
            seen.add(wid)
            self.items.append(Workspace(
                id=wid, application=str(w["application"]), label=str(w.get("label") or wid), root=self._abs(w["root"]),
                write_root=self._abs(w.get("write_root")), shared=bool(w.get("shared", False)), owner=w.get("owner"),
                members=[str(m) for m in w.get("members", [])], mode=str(w.get("mode", "live")),
                open_identity=bool(w.get("open_identity", False)), created=str(w.get("created", "")), cloned_from=w.get("cloned_from"),
                components=self._components(w.get("components") or {}, f"workspace '{wid}'"),
            ))

    def save(self) -> None:
        def rel(p: Path | None):
            if p is None:
                return None
            try:
                return str(p.relative_to(self.base))
            except ValueError:
                return str(p)

        def comps(cs: dict[str, Component]) -> dict:
            return {n: {k: v for k, v in {"path": rel(c.path), "write_path": rel(c.write_path), "shared": c.shared or None,
                                          "writable": None if c.writable else False}.items() if v is not None} for n, c in cs.items()}
        doc = {
            "$comment": "The cockpit's workspaces: applications (a casefile domain configuration) and the trees that run under them. Edited by `cockpit workspace …` and the cockpit itself; paths relative to this file's directory or absolute.",
            "applications": {a.id: {k: v for k, v in {"label": a.label, "config_dir": rel(a.config_dir), "template": rel(a.template), "mode": a.mode}.items() if v is not None} for a in self.applications.values()},
            **({"defaults": comps(self.defaults)} if self.defaults else {}),
            "workspaces": [{k: v for k, v in {**asdict(w), "root": rel(w.root), "write_root": rel(w.write_root), "components": comps(w.components)}.items()
                            if v not in (None, "", [], False, {}) or k in ("shared", "members")} for w in self.items],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- reading
    def get(self, wid: str) -> Workspace | None:
        return next((w for w in self.items if w.id == wid), None)

    def for_user(self, user: str | None) -> list[Workspace]:
        return [w for w in self.items if w.visible_to(user)]

    def may_open(self, user: str | None, wid: str) -> bool:
        w = self.get(wid)
        return w is not None and w.visible_to(user)

    # ---------------------------------------------------------------- creating
    def create(self, wid: str, application: str, owner: str | None, label: str = "", source: str | None = None,
               shared: bool = False, members: list[str] | None = None, where: Path | None = None) -> Workspace:
        """A new workspace: its tree copied from `source` (a workspace id the owner may see) or from the
        application's template, or started empty from the configuration. `where` is the parent directory of
        the new tree; default `<registry dir>/workspaces/<owner or shared>/<id>`."""
        if not NAME.match(wid):
            raise WorkspaceError(f"'{wid}' is not a workspace id — lower-case letters, digits, - and _ (2 to 48)")
        if self.get(wid):
            raise WorkspaceError(f"workspace '{wid}' exists")
        app = self.applications.get(application)
        if app is None:
            raise WorkspaceError(f"no application '{application}' — defined: {', '.join(self.applications) or 'none'}")
        parent = where or (self.path.parent / "workspaces" / (owner or "shared") / wid)
        root = parent / "flow"
        if root.exists():
            raise WorkspaceError(f"{root} exists already — pick another id or remove the folder")
        src: Path | None = None
        if source:
            s = self.get(source)
            if s is None or not s.visible_to(owner):
                raise WorkspaceError(f"'{source}' is not a workspace you may copy")
            if s.application != application:
                raise WorkspaceError(f"'{source}' belongs to application {s.application}, not {application}")
            src = s.root
        elif app.template and app.template.is_dir():
            src = app.template / "flow" if (app.template / "flow").is_dir() else app.template
        root.mkdir(parents=True)
        if src is not None:
            _copy_tree(src, root)
            for name in CLEARED:
                d = root / name
                if d.is_dir():
                    shutil.rmtree(d)
            (root / "_runs").mkdir()
        else:
            _empty_tree(app.config_dir, root)
        marker = {"workspace": wid, "application": application, "owner": owner, "shared": shared,
                  "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "cloned_from": source,
                  "$comment": "Written by the cockpit when this workspace was created. The tree is the truth; this says where it came from."}
        (root / "workspace.json").write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        w = Workspace(id=wid, application=application, label=label or wid, root=root, shared=shared, owner=owner,
                      members=list(members or []), mode=app.mode, open_identity=False, created=marker["created"][:19], cloned_from=source)
        self.items.append(w)
        self.save()
        return w

    def remove(self, wid: str, delete_files: bool = False) -> bool:
        w = self.get(wid)
        if w is None:
            return False
        self.items.remove(w)
        self.save()
        if delete_files and w.root.is_dir() and not w.shared:
            shutil.rmtree(w.root.parent if w.root.name == "flow" else w.root, ignore_errors=True)
        return True


LINKED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".mp4", ".mov", ".webm", ".m4a", ".wav", ".mp3"}


def _copy_tree(src: Path, dst: Path) -> None:
    """Text is copied, documents are hard-linked where the file system allows: the core never writes into an
    existing document, a new version is a new file (the demo sandbox's rule)."""
    import os
    for s in sorted(src.rglob("*")):
        d = dst / s.relative_to(src)
        if s.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.suffix.lower() in LINKED:
            try:
                os.link(s, d)
                continue
            except OSError:
                pass
        shutil.copy2(s, d)


def _empty_tree(config_dir: Path, root: Path) -> None:
    """A fresh tree from the configuration: every stage folder, the root files the configuration carries."""
    stages = json.loads((config_dir / "stages.json").read_text(encoding="utf-8")).get("stages", []) if (config_dir / "stages.json").is_file() else []
    for st in stages:
        (root / st["folder"]).mkdir(parents=True, exist_ok=True)
    for name in ("artifacts.json", "vocabulary.json", "people.json", "calendar.json", "run-policy.json", "run.schema.json", "meta.schema.json", "review.schema.json"):
        if (config_dir / name).is_file():
            shutil.copy2(config_dir / name, root / name)
    (root / "_runs").mkdir(exist_ok=True)


# -------------------------------------------------------------------- the apps behind the workspaces

def casefile_available() -> str | None:
    """None when the casefile core can be imported, otherwise the sentence that says what is missing."""
    try:
        import casefile  # noqa: F401
    except ImportError:
        return "the casefile package is not installed in this interpreter (pip install -e apps/casefile)"
    return None


def web_dist_default() -> Path | None:
    try:
        import casefile
    except ImportError:
        return None
    d = Path(casefile.__file__).resolve().parents[1] / "web" / "dist"
    return d if d.is_dir() else None


def build_app(w: Workspace, app: Application, identity, secret: str, web_dist: Path | None, stage: str | None = None, shell: str | None = None):
    """The casefile app for one workspace: its tree, its application, the cockpit's identity, the stage it is in,
    and where the shell lives — the menu offers the way back."""
    import casefile
    from casefile.api.app import Settings, create_app
    pkg = Path(casefile.__file__).resolve().parent
    settings = Settings(
        root=w.root, write_root=w.write_root, config_dir=app.config_dir, label=w.label, stage=stage, shell=shell,
        open_identity=w.open_identity, identity=None if w.open_identity else identity,
        secret=secret, web_dist=web_dist, demo=(w.mode == "replay"),
        samples_dir=pkg / "demo" / "samples", replies_dir=pkg / "demo" / "replies",
    )
    return create_app(settings)


def mount_all(shell, workspaces: Workspaces, identity, secret: str, web_dist: Path | None, stage: str | None = None, shell_url: str | None = None) -> dict[str, str]:
    """Mount every workspace under /w/<id>. Returns {id: reason} for the ones that did not come up."""
    failures: dict[str, str] = {}
    if (missing := casefile_available()):
        return {w.id: missing for w in workspaces.items}
    for w in workspaces.items:
        try:
            mount_one(shell, workspaces, w, identity, secret, web_dist, stage, shell_url)
        except Exception as exc:                 # noqa: BLE001 — one broken tree must not keep the shell down
            failures[w.id] = f"{type(exc).__name__}: {exc}"
    return failures


def mount_one(shell, workspaces: Workspaces, w: Workspace, identity, secret: str, web_dist: Path | None, stage: str | None = None, shell_url: str | None = None) -> None:
    app = workspaces.applications[w.application]
    shell.mount(f"/w/{w.id}", build_app(w, app, identity, secret, web_dist, stage, shell_url), name=f"ws-{w.id}")
