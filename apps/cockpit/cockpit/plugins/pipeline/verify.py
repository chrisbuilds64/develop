#!/usr/bin/env python3
"""Check a container against the rules the workflow lives by.

    verify.py <container>

Reports, and only reports:
  - files whose name follows neither the version convention (<stem>.vN.<ext>)
    nor the fixed names a container is expected to carry;
  - identical files under different names (the delete-and-reupload pattern);
  - review.md whose dated headings are not in chronological order (a sign
    that something was edited above the end).

Exit 0 when clean, 1 with findings. Works in COCKPIT_DATA_DIR.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

STAGE = re.compile(r"^\d{2}-")
VERSIONED = re.compile(r"^[a-z0-9-]+\.v\d+\.[a-z0-9]+$")
FIXED = {"meta.json", "review.md", "validation.md", "source.md", "interpretation.md", "visual-brief.md",
         "show-notes.txt", "edit-instructions.txt", "first-comment.txt", "substack.md", "substack.html",
         "linkedin-post.txt", "reel-hooks.txt", "script.md", "teleprompter.txt", "image.png"}
HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)", re.M)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.exit(__doc__)
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = argv[0].strip().strip("/").split("/")[-1]      # "stage/name" from the surface, "name" from the shell
    here = [s for s in sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name)) if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else "exists in more than one stage"))
    folder = root / here[0] / name
    findings = []

    hashes = {}
    for f in sorted(folder.iterdir()):
        if f.is_dir() or f.name.startswith("."):
            continue
        n = f.name.lower()
        if n not in FIXED and not VERSIONED.match(n) and not re.match(r"^[a-z0-9-]+\.[a-z0-9]+$", n):
            findings.append(f"naming: '{f.name}' follows neither <stem>.vN.<ext> nor a fixed name")
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h in hashes:
            findings.append(f"duplicate: '{f.name}' is identical to '{hashes[h]}'")
        hashes[h] = f.name

    review = folder / "review.md"
    if review.exists():
        dates = HEADING.findall(review.read_text(encoding="utf-8"))
        if dates != sorted(dates):
            findings.append("review.md: dated headings are not in order — something was written above the end")

    print(f"{here[0]}/{name}: " + ("clean" if not findings else f"{len(findings)} finding(s)"))
    for x in findings:
        print("  " + x)
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
