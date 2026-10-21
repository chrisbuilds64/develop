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
