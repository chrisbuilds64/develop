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


def build_cards(config: Config, access: Access, role: Role) -> list[Card]:
    cards: list[Card] = []
    for module in config.modules:
        if not module.enabled:
            continue
        if not role.may_open(module.id):
            cards.append(Card(module.id, None, "denied", f"role '{role.id}' may not open '{module.id}'"))
            continue
        try:
            reader = importlib.import_module(module.reader)
        except ImportError as exc:
            cards.append(Card(module.id, None, "error", f"reader '{module.reader}' not found: {exc}"))
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


def reader_for(module):
    return importlib.import_module(module.reader)


def card_for(config: Config, access: Access, role: Role, module_id: str) -> Card | None:
    for card in build_cards(config, access, role):
        if card.module_id == module_id:
            return card
    return None
