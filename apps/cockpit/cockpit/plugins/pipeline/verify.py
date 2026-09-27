#!/usr/bin/env python3
"""Check a container against the rules the workflow lives by.

    verify.py <container>         one container
    verify.py --all               every container, one line each, findings indented

Reports, and only reports:
  - meta.json against meta.schema.json at the pipeline root: required fields,
    values outside a field's list, fields the schema does not know;
  - files whose name follows neither the version convention (<stem>.vN.<ext>)
    nor the fixed names a container is expected to carry;
  - identical files under different names (the delete-and-reupload pattern);
  - review.md whose dated headings are not in chronological order (a sign
    that something was edited above the end).

Exit 0 when clean, 1 with findings. Works in COCKPIT_DATA_DIR.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_entries  # noqa: E402
try:
    from cockpit.schema import check as schema_check
except ImportError:                                   # run by hand from the source tree, outside the cockpit's interpreter
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from cockpit.schema import check as schema_check

STAGE = re.compile(r"^\d{2}-")
VERSIONED = re.compile(r"^[a-z0-9-]+\.v\d+\.[a-z0-9]+$")
FIXED = {"meta.json", "review.md", "validation.md", "source.md", "interpretation.md", "visual-brief.md",
         "show-notes.txt", "edit-instructions.txt", "first-comment.txt", "substack.md", "substack.html",
         "linkedin-post.txt", "reel-hooks.txt", "script.md", "teleprompter.txt", "image.png"}
HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)", re.M)


def check_meta(folder: Path, schema: dict | None) -> list[str]:
    """meta.json against the schema — the cockpit's one checker, prefixed with the file name."""
    m = folder / "meta.json"
    if not m.exists():
        return ["meta.json: missing — the container has no identity"]
    try:
        d = json.loads(m.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"meta.json: not valid JSON ({exc})"]
    return ["meta.json: " + x for x in schema_check(d, schema)]


def check(root: Path, stage: str, name: str, schema: dict | None) -> list[str]:
    folder = root / stage / name
    findings = check_meta(folder, schema)
    files = [f for f in sorted(folder.iterdir()) if f.is_file() and not f.name.startswith(".")]
    for f in files:
        n = f.name.lower()
        if n not in FIXED and not VERSIONED.match(n) and not re.match(r"^[a-z0-9-]+\.[a-z0-9]+$", n):
            findings.append(f"naming: '{f.name}' follows neither <stem>.vN.<ext> nor a fixed name")
    # Duplicates: only files of the same size are hashed — over a network mount, reading
    # every image to compare it would take minutes; sizes are free.
    by_size: dict[int, list[Path]] = {}
    for f in files:
        by_size.setdefault(f.stat().st_size, []).append(f)
    for group in by_size.values():
        if len(group) < 2:
            continue
        hashes = {}
        for f in group:
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            if h in hashes:
                findings.append(f"duplicate: '{f.name}' is identical to '{hashes[h]}'")
            hashes[h] = f.name
    review = folder / "review.md"
    if review.exists():
        text = review.read_text(encoding="utf-8")
        dates = HEADING.findall(text)
        if dates != sorted(dates):
            findings.append("review.md: dated headings are not in order — something was written above the end")
        entries = review_entries.parse(text)
        ids = [e["id"] for e in entries]
        if ids != sorted(ids):
            findings.append("review.md: REV numbers are not in order — an entry was written above the end")
        if len(ids) != len(set(ids)):
            findings.append("review.md: a REV number occurs twice")
        rschema = review_entries.load_schema(folder.parent.parent)
        people = review_entries.load_people(folder.parent.parent)
        for e in entries:
            findings += ["review.md: " + x for x in review_entries.check(e, rschema, people)]
            if e.get("resolves") and e["resolves"] not in ids:
                findings.append(f"review.md: {e['id']} resolves {e['resolves']}, which is not in this file")
    return findings


def load_schema(root: Path) -> dict | None:
    p = root / "meta.schema.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.exit(__doc__)
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    schema = load_schema(root)
    stages = sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name))

    if argv[0] == "--all":
        total = 0
        for stage in stages:
            for c in sorted(p.name for p in (root / stage).iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
                f = check(root, stage, c, schema)
                if f:
                    total += len(f)
                    print(f"{stage}/{c}: {len(f)}")
                    for x in f:
                        print("  " + x)
        print(f"{total} finding(s)" + ("" if schema else " — no meta.schema.json at the root, meta.json not checked")
              + ("" if (root / "people.json").exists() else " — no people.json at the root, authors not checked"))
        return 0 if not total else 1

    name = argv[0].strip().strip("/").split("/")[-1]      # "stage/name" from the surface, "name" from the shell
    here = [s for s in stages if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else "exists in more than one stage"))
    findings = check(root, here[0], name, schema)
    print(f"{here[0]}/{name}: " + ("clean" if not findings else f"{len(findings)} finding(s)"))
    for x in findings:
        print("  " + x)
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
