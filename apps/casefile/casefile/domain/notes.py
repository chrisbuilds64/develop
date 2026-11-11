"""Free notes in a case (REQ-001 S-17): Markdown a person writes beside the documents the application declares.

A note lives under `notes/<slug>.md` and is versioned like any document (`notes/<slug>.v2.md`). It stands outside the
case's top level on purpose: `store.files()` does not see the subfolder, so no slot, no `shape:`, no `required`, no
primary and no four-eyes check ever counts a note — notes count for no gate by where they lie, not by an exception in
each rule. Whether an application offers notes is its word (`"notes": false` in theme.json); the default is on.
"""

from __future__ import annotations

import re
import unicodedata

from ..config import DomainConfig
from ..models import FileVersion, Note
from ..store import FsStore, StoreError
from .cases import split_version

FOLDER = "notes"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FILE = re.compile(rf"^{FOLDER}/([a-z0-9]+(?:-[a-z0-9]+)*)(?:\.v(\d+))?\.md$")
HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$")
FOLD = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


class NotesOff(Exception):
    """The application does not offer notes."""


def enabled(config: DomainConfig) -> bool:
    """On unless the application says `"notes": false`."""
    return config.theme.get("notes", True) is not False


def is_note(file: str) -> bool:
    """`notes/<slug>.md` — the name a note is addressed by (its first version); never a path out of the folder."""
    m = FILE.match(file)
    return bool(m) and m.group(2) is None


def is_note_version(name: str) -> bool:
    """`notes/<slug>.md` or one of its versions — what the reader may open."""
    return bool(FILE.match(name))


def slug(title: str) -> str:
    """'Gespräch mit Peter' → 'gespraech-mit-peter'. Empty when nothing of the title is left."""
    t = "".join(FOLD.get(ch, ch) for ch in title.strip().lower())
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60].strip("-")


def word_of(text: str, file: str) -> str:
    """What the surface calls a note: its first heading, else its name with spaces."""
    for line in text.splitlines():
        m = HEADING.match(line.strip())
        if m:
            return m.group(1)[:80]
        if line.strip():
            break
    base = FILE.match(file).group(1) if FILE.match(file) else file
    return base.replace("-", " ").capitalize()


def load(store: FsStore, case_id: str) -> list[Note]:
    """The notes of a case, each with its versions oldest → newest, in the order they were named."""
    by: dict[str, list[FileVersion]] = {}
    for name in store.sub_files(case_id, FOLDER):
        if not is_note_version(name):
            continue
        base, v = split_version(name)
        by.setdefault(base, []).append(FileVersion(name=name, version=v, size=store.size(case_id, name)))
    out = []
    for base, versions in sorted(by.items()):
        versions.sort(key=lambda x: x.version)
        try:
            text = store.case_text(case_id, versions[-1].name)
        except (OSError, UnicodeDecodeError):
            text = ""
        out.append(Note(file=base, word=word_of(text, base), versions=versions))
    return out


def new(store: FsStore, config: DomainConfig, case_id: str, title: str) -> str:
    """The file a new note with this title will be written to. Writes nothing; the first save creates it."""
    if not enabled(config):
        raise NotesOff("this application does not offer notes")
    if store.find(case_id) is None:
        raise StoreError(f"case '{case_id}' not found")
    s = slug(title)
    if not s:
        raise ValueError("a note needs a title with letters or digits")
    file = f"{FOLDER}/{s}.md"
    if any(split_version(n)[0] == file for n in store.sub_files(case_id, FOLDER)):
        raise FileExistsError(f"a note '{s}' already exists in this case")
    return file


def next_name(store: FsStore, case_id: str, file: str) -> str:
    """The name the next version of a note gets: the note itself first, then `.v2`, `.v3` …"""
    versions = [split_version(n)[1] for n in store.sub_files(case_id, FOLDER) if split_version(n)[0] == file]
    if not versions:
        return file
    stem = file[: -len(".md")]
    return f"{stem}.v{max(max(versions), 1) + 1}.md"


def save(store: FsStore, case_id: str, file: str, text: str) -> str:
    """The text as the next version of the note. Returns the name written."""
    name = next_name(store, case_id, file)
    store.put_bytes(case_id, name, text.encode("utf-8"))
    return name
