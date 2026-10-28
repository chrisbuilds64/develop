"""Stage a: the deterministic rules. Local only — nothing here leaves the machine."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RULES = Path(os.environ.get("MAILSORT_RULES", "~/.config/mailsort/rules.toml")).expanduser()

UNDECIDED = "(undecided: AI or inbox)"


@dataclass
class Folder:
    path: str
    kind: str
    hint: str
    domains: list[str] = field(default_factory=list)
    subject: list[str] = field(default_factory=list)


@dataclass
class Decision:
    folder: str
    stage: str
    reason: str


def load(path: Path = RULES) -> tuple[list[Folder], list[str], str]:
    data = tomllib.loads(path.read_text())
    folders = [Folder(**f) for f in data.get("folder", [])]
    never_ai = [x.lower() for x in data.get("privacy", {}).get("never_ai", [])]
    return folders, never_ai, data.get("newsletter_fallback", "")


def _domain_match(domain: str, rule: str) -> bool:
    return domain == rule or domain.endswith("." + rule)


def classify(h: dict, folders: list[Folder], newsletter_fallback: str = "") -> Decision:
    best = None
    for f in folders:
        for d in f.domains:
            if _domain_match(h["domain"], d) and (best is None or len(d) > len(best[1])):
                best = (f, d)
    if best:
        return Decision(best[0].path, "a", f"domain {best[1]}")
    subj = h["subject"].lower()
    for f in folders:
        for kw in f.subject:
            if kw in subj:
                return Decision(f.path, "a", f"subject '{kw}'")
    bulk = h["list_id"] or h["unsubscribe"] or h["precedence"] in ("bulk", "list", "junk")
    auto = h["auto_submitted"] and h["auto_submitted"] != "no"
    if auto and not bulk:
        return Decision("_Benachrichtigungen", "a", f"auto-submitted: {h['auto_submitted']}")
    if bulk and newsletter_fallback:
        return Decision(newsletter_fallback, "a", "list/bulk headers, no folder of its own")
    return Decision(UNDECIDED, "-", "no rule")
