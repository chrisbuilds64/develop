"""From configuration to cards.

A module names a reader by dotted path. The registry imports it, hands it the
access layer and the role, and turns whatever comes back into a Card — a valid
panel, or the reason there is none. A reader that raises does not take the
page down; it produces a card that says "unavailable" and why.

Readers are ordinary functions:

    def read(access, role, module, config) -> dict   # a panel

They never open files themselves. Everything goes through `access`.
"""

from __future__ import annotations

import importlib

from .access import Access, Denied, Missing
from .config import Config, Role
from .panel import Card, evaluate
from .plugins import PluginError, app_of, discover, reader_of

_PLUGINS: dict = {}


def plugins_for(config: Config) -> dict:
    """The plugins this configuration can use — discovered once per process."""
    key = str(config.plugins_dir)
    if key not in _PLUGINS:
        _PLUGINS[key] = discover(config.plugins_dir)
    return _PLUGINS[key]


def reader_for(module, config: Config):
    plugin = plugins_for(config).get(module.plugin)
    if plugin is None:
        raise PluginError(f"plugin '{module.plugin}' is not installed")
    return reader_of(plugin)


def build_cards(config: Config, access: Access, role: Role) -> list[Card]:
    cards: list[Card] = []
    for module in config.modules:
        if not module.enabled:
            continue
        if not role.may_open(module.id):
            cards.append(Card(module.id, None, "denied", f"role '{role.id}' may not open '{module.id}'"))
            continue
        try:
            reader = reader_for(module, config)
        except (PluginError, ImportError, SyntaxError) as exc:
            cards.append(Card(module.id, None, "error", str(exc)))
            continue
        try:
            panel = reader.read(access, role, module, config)
        except Missing as exc:
            cards.append(Card(module.id, None, "error", str(exc)))
            continue
        except Denied as exc:
            cards.append(Card(module.id, None, "denied", str(exc)))
            continue
        except Exception as exc:  # a broken reader is a card, not a crash
            cards.append(Card(module.id, None, "error", f"{type(exc).__name__}: {exc}"))
            continue
        panel.setdefault("panel", module.id)
        panel.setdefault("maturity", module.maturity)
        cards.append(evaluate(module.id, panel, config.stale_after_hours))
    return cards


def card_for(config: Config, access: Access, role: Role, module_id: str) -> Card | None:
    for card in build_cards(config, access, role):
        if card.module_id == module_id:
            return card
    return None


def mount_apps(shell, config: Config) -> list[tuple[str, str]]:
    """Mount every module whose plugin brings a web app under /m/<id>/app.

    The app runs inside the cockpit's process and URL. The one thing it has to
    do to be mountable: build its links from `request.scope["root_path"]`.
    """
    failures = []
    plugins = plugins_for(config)
    for module in config.modules:
        plugin = plugins.get(module.plugin)
        if not module.enabled or plugin is None or not plugin.app:
            continue
        try:
            app = app_of(plugin, module.app_config)
            shell.mount(f"/m/{module.id}/app", app, name=f"app-{module.id}")
        except Exception as exc:
            failures.append((module.id, f"{type(exc).__name__}: {exc}"))
    return failures
