#!/usr/bin/env python3
"""The design guard: colour, type and radius come from the tokens and nowhere else.

    python3 tools/design_guard.py              fail when a file holds more raw values than the baseline allows
    python3 tools/design_guard.py --list       every raw value still standing, file by file: what is left to move into tokens
    python3 tools/design_guard.py --update     write the baseline down to what is there now; it never goes up on its own
    python3 tools/design_guard.py --update --accept-more    a raise, on a person's word, with the reason in the commit

A ratchet, not a wall: the surface was built before the tokens covered type, so the baseline records what stands today
(per file and rule). A new raw value fails, a file the baseline does not know must be clean, and every value moved into a
token lowers the count for good. The tokens files themselves are where raw values belong.

Rules: `colour` (#hex, rgb(), hsl(), oklch()), `font-size` and `font-family` set to a literal, `radius` (a border-radius
other than 0, 50 % or a token). Spacing follows once the tokens carry a scale for it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).resolve().parent / "design_guard.baseline.json"

SCAN = [
    ("apps/casefile/web/src", ("*.css", "*.tsx", "*.ts")),
    ("apps/cockpit/cockpit/static", ("*.css", "*.js")),
    ("apps/cockpit/cockpit/templates", ("*.html",)),
]
TOKENS = {"tokens.css"}
SKIP = {"htmx.min.js"}

RULES = {
    "colour": re.compile(r"#[0-9a-fA-F]{3,8}\b(?![\w-])|\b(?:rgba?|hsla?|oklch)\("),
    "font-size": re.compile(r"font-?[sS]ize\s*[:=]\s*[\"']?\s*\d"),
    "font-family": re.compile(r"font-?[fF]amily\s*:(?!\s*[\"']?(?:var\(|inherit))\s*[^\s;}]"),
    "radius": re.compile(r"border-?[rR]adius\s*[:=]\s*[\"']?\s*(?!0(?:px)?\s*[;\"'}]|50%|var\()[0-9.]"),
}
_BLOCK = re.compile(r"/\*.*?\*/", re.S)
_LINE = re.compile(r"^\s*//.*$", re.M)
_HTMLC = re.compile(r"<!--.*?-->|\{#.*?#\}", re.S)


def files(root: Path):
    for base, globs in SCAN:
        d = root / base
        for g in globs:
            for p in sorted(d.rglob(g)) if d.is_dir() else []:
                if p.name not in TOKENS and p.name not in SKIP and "node_modules" not in p.parts:
                    yield p


def strip(p: Path, text: str) -> str:
    """Comments say things like 'the accent (#1D4ED8)'; they are not styles. Newlines stay, so line numbers hold."""
    keep = lambda m: "\n" * m.group(0).count("\n")
    text = _BLOCK.sub(keep, text)
    if p.suffix in (".ts", ".tsx", ".js"):
        text = _LINE.sub("", text)
    if p.suffix == ".html":
        text = _HTMLC.sub(keep, text)
    return text


def scan(root: Path = REPO) -> dict[str, dict[str, list[tuple[int, str]]]]:
    out: dict[str, dict[str, list[tuple[int, str]]]] = {}
    for p in files(root):
        rel = p.relative_to(root).as_posix()
        for n, line in enumerate(strip(p, p.read_text(encoding="utf-8", errors="replace")).splitlines(), 1):
            for rule, rx in RULES.items():
                if rx.search(line):
                    out.setdefault(rel, {}).setdefault(rule, []).append((n, line.strip()[:140]))
    return out


def counts(found: dict) -> dict[str, dict[str, int]]:
    return {f: {r: len(v) for r, v in rules.items()} for f, rules in sorted(found.items())}


def load_baseline(path: Path = BASELINE) -> dict[str, dict[str, int]]:
    return json.loads(path.read_text(encoding="utf-8"))["files"] if path.exists() else {}


def over(found: dict, base: dict) -> list[str]:
    """Every file and rule above its baseline, with the lines, so the new one is among them."""
    msgs = []
    for f, rules in found.items():
        for r, lines in rules.items():
            allowed = base.get(f, {}).get(r, 0)
            if len(lines) > allowed:
                msgs.append(f"{f}: {r} {len(lines)} > {allowed} allowed" + ("" if allowed else " (a new file or rule must be clean)"))
                msgs += [f"    {n:>5}  {t}" for n, t in lines] if not allowed or len(lines) - allowed <= 5 else [f"    … {len(lines)} lines, run --list"]
    return msgs


def write_baseline(found: dict, base: dict, accept_more: bool, path: Path = BASELINE) -> list[str]:
    now = counts(found)
    raised = [f"{f}: {r} {n} > {base.get(f, {}).get(r, 0)}" for f, rs in now.items() for r, n in rs.items() if n > base.get(f, {}).get(r, 0)]
    if raised and not accept_more:
        return raised
    doc = {"$comment": "Raw design values per file and rule that stood when the guard came (2026-10-30). Only goes down; "
                       "a raise needs --accept-more and a person's word. tools/design_guard.py",
           "files": now}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return []


def main(argv: list[str]) -> int:
    found = scan()
    base = load_baseline()
    if "--list" in argv:
        total = 0
        for f, rules in sorted(found.items()):
            for r, lines in rules.items():
                total += len(lines)
                print(f"{f}  [{r}] {len(lines)}")
                for n, t in lines:
                    print(f"    {n:>5}  {t}")
        print(f"\n{total} raw values left outside the tokens.")
        return 0
    if "--update" in argv:
        raised = write_baseline(found, base, "--accept-more" in argv)
        if raised:
            print("Not written — this would raise the baseline:", *raised, "A raise needs --accept-more and a reason.", sep="\n  ")
            return 1
        print(f"Baseline written: {sum(sum(r.values()) for r in counts(found).values())} raw values in {len(found)} files.")
        return 0
    msgs = over(found, base)
    total, allowed = sum(len(v) for r in found.values() for v in r.values()), sum(sum(r.values()) for r in base.values())
    if msgs:
        print("Design guard: raw values outside the tokens.", *msgs, sep="\n")
        print("\nUse a token from tokens.css, or add one there.")
        return 1
    note = f" — {allowed - total} fewer than the baseline; lower it with --update" if total < allowed else ""
    print(f"Design guard: clean ({total} raw values left from before the tokens{note}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
