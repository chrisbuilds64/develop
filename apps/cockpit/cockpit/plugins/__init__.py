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
    """Import the plugin's reader from its own directory, under a name of its own."""
    target = plugin.manifest["reader"]
    if target.endswith(".py") or "/" in target:
        file = plugin.path / target
    else:
        file = plugin.path / (target.replace(".", "/") + ".py")
    if not file.is_file():
        raise PluginError(f"{plugin.id}: reader '{target}' not found at {file}")
    name = f"cockpit_plugin_{plugin.id.replace('-', '_')}_reader"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


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
