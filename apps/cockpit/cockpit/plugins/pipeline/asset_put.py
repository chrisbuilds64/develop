#!/usr/bin/env python3
"""Put a file into a container as a versioned asset — never overwrite.

    asset_put.py <container> <kind> <tmpfile> --name <original-name> [--by <user>]

The kind decides the stem and the allowed extensions; the tool finds the next
free version and writes <stem>.vN.<ext> into the container, wherever in the
pipeline it currently stands. A second upload of the same kind is a new
version beside the first. Nothing is ever replaced.

Works in COCKPIT_DATA_DIR (the pipeline root). The kinds are the deliverable
names the production workflow already uses.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

STAGE = re.compile(r"^\d{2}-")
KINDS = {
    "linkedin-image":  ("linkedin-image",  ("png", "jpg", "jpeg")),
    "substack-image":  ("substack-image",  ("png", "jpg", "jpeg")),
    "header-16x9":     ("header-16x9",     ("png", "jpg", "jpeg")),
    "header-4x5":      ("header-4x5",      ("png", "jpg", "jpeg")),
    "thumbnail":       ("thumbnail-16x9",  ("png", "jpg", "jpeg")),
    "poster-4x5":      ("poster-4x5",      ("png", "jpg", "jpeg")),
    "teaser-reel":     ("teaser-reel",     ("mp4", "mov")),
    "screen-segment":  ("screen-segment",  ("mp4", "mov")),
    "image":           ("image",           ("png", "jpg", "jpeg")),
}
VERSION = re.compile(r"\.v(\d+)\.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="asset_put.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container"); p.add_argument("kind"); p.add_argument("tmpfile")
    p.add_argument("--name", required=True, help="the original file name, for its extension")
    p.add_argument("--by", default="")
    a = p.parse_args(argv)

    if a.kind not in KINDS:
        sys.exit(f"unknown kind '{a.kind}' — one of: {', '.join(KINDS)}")
    stem, allowed = KINDS[a.kind]
    ext = a.name.rsplit(".", 1)[-1].lower() if "." in a.name else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in allowed and not (ext == "jpg" and "jpeg" in allowed):
        sys.exit(f"'{a.name}' is not allowed for {a.kind} — one of: {', '.join(allowed)}")
    src = Path(a.tmpfile)
    if not src.is_file() or src.stat().st_size == 0:
        sys.exit("the uploaded file is missing or empty")

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = a.container.strip().strip("/").split("/")[-1]  # "stage/name" from the surface, "name" from the shell
    if not name or name.startswith("."):
        sys.exit(f"'{name}' is not a container name")
    here = [s for s in sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name)) if (root / s / name).is_dir()]
    if not here:
        sys.exit(f"container '{name}' not found in any stage")
    if len(here) > 1:
        sys.exit(f"container '{name}' exists in more than one stage: {', '.join(here)}")
    folder = root / here[0] / name

    used = [int(m.group(1)) for f in folder.iterdir() for m in [VERSION.search(f.name)] if m and f.name.startswith(stem + ".v")]
    unversioned = (folder / f"{stem}.{ext}").exists()
    n = max(used, default=1 if unversioned else 0) + 1
    target = folder / f"{stem}.v{n}.{ext}"
    if target.exists():
        sys.exit(f"{target.name} already exists — refusing to overwrite")
    shutil.copyfile(src, target)
    print(f"stored {here[0]}/{name}/{target.name} ({target.stat().st_size // 1024} KB)"
          + (f" by {a.by}" if a.by else "") + (f" — previous versions: {sorted(used)}" if used else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
