"""Stage a: the deterministic rules. Local only — nothing here leaves the machine."""

import os
import sys
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


def _core():
    """The decision lives in the casefile core (casefile/domain/sorting.py, standard library only); one implementation."""
    try:
        from casefile.domain import sorting
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "casefile"))
        from casefile.domain import sorting
    return sorting


def classify(h: dict, folders: list[Folder], newsletter_fallback: str = "") -> Decision:
    rows = [{"id": f.path, "sort": {"domains": f.domains, "subject": f.subject}} for f in folders]
    rows.append({"id": "_Benachrichtigungen", "sort": {"auto": True}})
    if newsletter_fallback:
        rows.append({"id": newsletter_fallback, "sort": {"bulk": True}})
    hit = _core().classify(h, rows)
    if hit is None:
        return Decision(UNDECIDED, "-", "no rule")
    return Decision(hit[0]["id"], "a", hit[1])
