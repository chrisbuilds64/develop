"""Plugins: where they live, how they are found, how one is added.

A plugin is a directory with a `plugin.json` — validated against
`schemas/plugin.schema.json` — and beside it a `reader.py`, optionally a web
app, optionally a `locales/` folder. Two places are searched: the plugins
bundled with the cockpit (`cockpit/plugins/`) and the ones installed next to
the configuration (`<config dir>/plugins/`). An installed plugin with the same
id shadows a bundled one.

`cockpit plugin add <path>` copies a plugin directory into the installed set
after checking its manifest; `--link` symlinks it instead, for development.
A module in the configuration names a plugin by id and nothing else — reader,
app and locales come from the manifest.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from ..panel import _check

HERE = Path(__file__).parent
SCHEMA_PATH = HERE.parent / "schemas" / "plugin.schema.json"
BUNDLED = HERE                                   # the bundled plugins sit beside this file


class PluginError(Exception):
    pass


@dataclass(frozen=True)
class Plugin:
    id: str
    name: str
    version: str
    path: Path
    manifest: dict
    bundled: bool

    @property
    def app(self) -> dict | None:
        return self.manifest.get("app")

    @property
    def icon(self) -> str:
        return self.manifest.get("icon") or "box"

    @property
    def accent(self) -> str:
        return self.manifest.get("accent") or "#3b82f6"

    @property
    def locales(self) -> Path | None:
        d = self.manifest.get("locales")
        return (self.path / d) if d else None


def validate(manifest: dict) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _check(manifest, schema, schema)


def load_manifest(path: Path) -> dict:
    mf = Path(path) / "plugin.json"
    if not mf.is_file():
        raise PluginError(f"{path}: no plugin.json")
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginError(f"{mf}: not valid JSON: {exc}") from exc
    problems = validate(manifest)
    if problems:
        raise PluginError(f"{mf}: " + "; ".join(problems))
    return manifest


def discover(installed_dir: Path | None) -> dict[str, Plugin]:
    found: dict[str, Plugin] = {}
    places = [(BUNDLED, True)] + ([(Path(installed_dir), False)] if installed_dir else [])
    for base, bundled in places:
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not (d / "plugin.json").is_file():
                continue
            try:
                m = load_manifest(d)
            except PluginError:
                continue          # `cockpit plugin list` reports it; the surface just skips it
            found[m["id"]] = Plugin(m["id"], m["name"], m["version"], d.resolve(), m, bundled)
    return found


def reader_of(plugin: Plugin):
    """Import the plugin's reader as part of a package named after the plugin.

    The plugin directory becomes a package (`cockpit_plugin_<id>`), so a reader
    may use relative imports and helper modules beside it. Loaded once.
    """
    pkg = f"cockpit_plugin_{plugin.id.replace('-', '_')}"
    target = plugin.manifest["reader"]
    rel = target[:-3] if target.endswith(".py") else target.replace(".", "/")
    file = plugin.path / (rel + ".py")
    if not file.is_file():
        raise PluginError(f"{plugin.id}: reader '{target}' not found at {file}")
    if pkg not in sys.modules:
        spec = importlib.util.spec_from_file_location(pkg, plugin.path / "__init__.py",
                                                      submodule_search_locations=[str(plugin.path)])
        if (plugin.path / "__init__.py").is_file():
            pkg_mod = importlib.util.module_from_spec(spec)
            sys.modules[pkg] = pkg_mod
            spec.loader.exec_module(pkg_mod)
        else:                                   # a package without __init__: namespace-style
            pkg_mod = importlib.util.module_from_spec(importlib.machinery.ModuleSpec(pkg, None, is_package=True))
            pkg_mod.__path__ = [str(plugin.path)]
            sys.modules[pkg] = pkg_mod
    mod_name = pkg + "." + rel.replace("/", ".")
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    _check_contract(plugin, mod)
    return mod


def _check_contract(plugin: Plugin, mod) -> None:
    """A reader must offer read(access, role, module, config); detail and document are optional but must fit."""
    import inspect
    fn = getattr(mod, "read", None)
    if not callable(fn):
        raise PluginError(f"{plugin.id}: reader has no read()")
    want = {"read": 4, "detail": 4, "document": 5}
    for name, n in want.items():
        f = getattr(mod, name, None)
        if f is None:
            continue
        params = [p for p in inspect.signature(f).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        if len(params) != n:
            raise PluginError(f"{plugin.id}: {name}() takes {len(params)} arguments, the contract has {n}")


def app_of(plugin: Plugin, config_path: Path | None):
    """Build the plugin's web app from its manifest, or return None."""
    spec = plugin.app
    if not spec:
        return None
    root = (plugin.path / spec.get("path", ".")).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    mod_name, _, factory_name = spec["factory"].partition(":")
    factory = getattr(importlib.import_module(mod_name), factory_name)
    cfg = config_path or (root / spec["config"] if spec.get("config") else None)
    return factory(cfg) if cfg else factory()


def add(src: Path, installed_dir: Path, link: bool = False) -> Plugin:
    src = Path(src).resolve()
    m = load_manifest(src)
    dest = Path(installed_dir) / m["id"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    if link:
        os.symlink(src, dest)
    else:
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", ".venv", ".git", "*.pyc"))
    return Plugin(m["id"], m["name"], m["version"], dest.resolve(), m, False)


def remove(plugin_id: str, installed_dir: Path) -> bool:
    dest = Path(installed_dir) / plugin_id
    if dest.is_symlink():
        dest.unlink(); return True
    if dest.is_dir():
        shutil.rmtree(dest); return True
    return False
