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
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_entries import load_people, person  # noqa: E402

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
TEXT = ("md", "txt", "html")


def artifact_kinds(root: Path) -> set[str]:
    """Every artifact file name artifacts.json knows, across formats — an upload may name one of them as its kind."""
    p = root / "artifacts.json"
    if not p.exists():
        return set()
    d = json.loads(p.read_text(encoding="utf-8"))
    out = set(d.get("kinds", []))
    for f in list(d.get("formats", {}).values()) + [{"artifacts": d.get("common", [])}]:
        out.update(a["file"] if isinstance(a, dict) else a for a in f.get("artifacts", []))
    return out


def kind_of(root: Path, kind: str) -> tuple[str, tuple[str, ...], bool]:
    """(stem, allowed extensions, is_artifact). A kind is a known asset kind or an artifact's file name."""
    if kind in KINDS:
        return KINDS[kind] + (False,)
    if "." in kind and kind in artifact_kinds(root):
        stem, ext = kind.rsplit(".", 1)
        allowed = ("jpg", "jpeg") if ext in ("jpg", "jpeg") else (ext,)
        return stem, allowed, True
    sys.exit(f"unknown kind '{kind}' — one of: {', '.join(KINDS)}, or an artifact's file name from artifacts.json")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="asset_put.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container"); p.add_argument("kind"); p.add_argument("tmpfile")
    p.add_argument("--name", required=True, help="the original file name, for its extension")
    p.add_argument("--by", default="")
    a = p.parse_args(argv)

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    stem, allowed, is_artifact = kind_of(root, a.kind)
    ext = a.name.rsplit(".", 1)[-1].lower() if "." in a.name else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in allowed and not (ext == "jpg" and "jpeg" in allowed):
        sys.exit(f"'{a.name}' is not allowed for {a.kind} — one of: {', '.join(allowed)}")
    src = Path(a.tmpfile)
    if not src.is_file() or src.stat().st_size == 0:
        sys.exit("the uploaded file is missing or empty")

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    if a.by.strip():
        a.by = person(a.by, load_people(root)) or sys.exit(f"'{a.by}' is not in people.json — add the person there first")
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
    # an artifact starts unversioned (the convention for deliverables); the first revision becomes .v2 beside it
    target = folder / (f"{stem}.{ext}" if is_artifact and not used and not unversioned else f"{stem}.v{n}.{ext}")
    if target.exists():
        sys.exit(f"{target.name} already exists — refusing to overwrite")
    shutil.copyfile(src, target)
    print(f"stored {here[0]}/{name}/{target.name} ({target.stat().st_size // 1024} KB)"
          + (f" by {a.by}" if a.by else "") + (f" — previous versions: {sorted(used)}" if used else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
