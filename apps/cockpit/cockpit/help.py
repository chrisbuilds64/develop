"""Help for the page you are on — instead of a manual, kept in step with the code by a check.

Every element worth explaining carries an anchor in the markup, `data-help="<key>"` (templates, the side panel's
script, casefile's web/src). Next to the code lies a catalog per surface, `help/<surface>.json`, with one topic per
anchor: title and text in each language, and `since` — the version that brought it, so the panel can mark what is
new. The side panel shows the topics whose anchors are on the page, walks through them as a tour, and hands a
question with the page's help to the person's team.

`check()` compares anchors and topics in both directions. An anchor without a topic, a topic without an anchor, a
topic without `since` or without a language: each is a finding. The tests run it and pressroom-env runs it before
a deploy, so the help cannot drift from what is on the screen — change both in the same commit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANCHOR = re.compile(r"""data-help(?:=|['"]\s*[,:]\s*)["']([a-z][a-z0-9.-]+)["']""")
# data-help="x" in markup; 'data-help', 'x' in setAttribute; {"data-help": "x"} spread into JSX
LANGS = ("de", "en")


def casefile_root() -> Path | None:
    try:
        import casefile
    except ImportError:
        return None
    return Path(casefile.__file__).resolve().parent


def catalogs() -> list[Path]:
    out = sorted((HERE / "help").glob("*.json"))
    cf = casefile_root()
    if cf and (cf / "help").is_dir():
        out += sorted((cf / "help").glob("*.json"))
    return out


def sources() -> list[Path]:
    """Where anchors may be: the cockpit's templates and scripts, casefile's web sources."""
    out = sorted((HERE / "templates").glob("*.html")) + sorted((HERE / "static").glob("*.js"))
    cf = casefile_root()
    if cf and (cf.parent / "web" / "src").is_dir():
        out += sorted(p for p in (cf.parent / "web" / "src").rglob("*.tsx"))
    return out


def anchors() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for p in sources():
        for key in ANCHOR.findall(p.read_text(encoding="utf-8", errors="replace")):
            found.setdefault(key, []).append(p.name)
    return found


def topics() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in catalogs():
        doc = json.loads(p.read_text(encoding="utf-8"))
        for t in doc.get("topics", []):
            out[t["key"]] = dict(t, surface=doc.get("surface", p.stem))
    return out


def check() -> list[str]:
    """Findings, one sentence each. Empty means the help matches the screen."""
    found, docs, problems = anchors(), topics(), []
    for key in sorted(set(found) - set(docs)):
        problems.append(f"anchor '{key}' ({', '.join(sorted(set(found[key])))}) has no help topic")
    for key in sorted(set(docs) - set(found)):
        problems.append(f"help topic '{key}' ({docs[key]['surface']}) has no anchor on any page")
    for key, t in sorted(docs.items()):
        if not t.get("since"):
            problems.append(f"help topic '{key}' has no 'since' version")
        for lang in LANGS:
            if not (t.get("title") or {}).get(lang) or not (t.get("text") or {}).get(lang):
                problems.append(f"help topic '{key}' has no {lang} title or text")
    return problems


def view(lang: str) -> dict:
    """What the panel needs: per surface the intro, and every topic in the person's language."""
    lang = lang if lang in LANGS else "en"
    out = {"surfaces": {}, "topics": []}
    for p in catalogs():
        doc = json.loads(p.read_text(encoding="utf-8"))
        out["surfaces"][doc.get("surface", p.stem)] = (doc.get("intro") or {}).get(lang, "")
        for t in doc.get("topics", []):
            out["topics"].append({"key": t["key"], "since": t.get("since", ""), "surface": doc.get("surface", p.stem),
                                  "title": t["title"].get(lang, ""), "text": t["text"].get(lang, "")})
    return out


def as_text(lang: str = "de", keys: list[str] | None = None) -> str:
    """The help as plain text for an agent: the topics on the page the person asks from, or all of them."""
    v = view(lang)
    lines = [f"[{s}] {intro}" for s, intro in v["surfaces"].items() if intro]
    lines += [f"- {t['title']} ({t['key']}): {t['text']}" for t in v["topics"] if keys is None or t["key"] in keys]
    return "\n".join(lines)
