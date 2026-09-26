"""Languages: one JSON file each, nothing in the core knows which exist.

`locales/en.json` is the primary language and the fallback. A new language is
a new file beside it — drop `fr.json` in, and it appears in the switcher. The
file carries its own display name under `_name`, so the core never holds a
list of languages.

Readers and templates speak in keys (`worklist.open`), never in sentences. A
key without a translation falls back to English, and a key without English
falls back to itself, visibly — a missing string should be seen, not hidden.
"""

from __future__ import annotations

import json
from pathlib import Path

PRIMARY = "en"


class I18n:
    def __init__(self, locales_dir: Path):
        self._dir = Path(locales_dir)
        self._tables: dict[str, dict[str, str]] = {}
        for f in sorted(self._dir.glob("*.json")):
            self._tables[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        if PRIMARY not in self._tables:
            raise RuntimeError(f"locales/{PRIMARY}.json is missing — it is the fallback for everything")

    def languages(self) -> list[tuple[str, str]]:
        """(code, display name) for every language file present."""
        return [(code, t.get("_name", code)) for code, t in self._tables.items()]

    def has(self, lang: str) -> bool:
        return lang in self._tables

    def pick(self, requested: str | None, default: str) -> str:
        """The language to use: what was asked for if we have it, else the default, else English."""
        for candidate in (requested, default, PRIMARY):
            if candidate and candidate in self._tables:
                return candidate
        return PRIMARY

    def t(self, lang: str, key: str, **kw) -> str:
        text = self._tables.get(lang, {}).get(key) or self._tables[PRIMARY].get(key) or key
        try:
            return text.format(**kw) if kw else text
        except (KeyError, IndexError):
            return text
