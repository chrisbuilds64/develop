"""A visitor's sandbox is a copy of the world. Documents (images, PDFs, video) are hard-linked instead of copied: the core never
writes into an existing document — a new version is a new file, and text files (which the core appends to) are copied for real.
A room of five hundred sandboxes then costs the text, not the pictures."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

LINKED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".mp4", ".mov", ".webm", ".m4a", ".wav", ".mp3"}


def copy_world(template: Path, dest: Path) -> None:
    for src in sorted(template.rglob("*")):
        d = dest / src.relative_to(template)
        if src.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in LINKED:
            try:
                os.link(src, d)
                continue
            except OSError:         # another filesystem, or links not allowed: a copy is still right
                pass
        shutil.copy2(src, d)


KEPT = ("workspace.json", "targets.json", "mailbox.json")      # what the cockpit and the stage wrote into a workspace: not the world's


def reset_world(template: Path, root: Path) -> None:
    """A sample workspace back to its world, for the next run of a demonstration: everything the world brought and every
    case and run since then go; what the stage wrote beside it (where hand-offs land, the marker) stays."""
    src = template / "flow" if (template / "flow").is_dir() else template
    for child in root.iterdir():
        if child.name in KEPT:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    copy_world(src, root)
