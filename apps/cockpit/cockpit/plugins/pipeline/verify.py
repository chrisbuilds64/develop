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

STAGE = re.compile(r"^\d{2}-")
VERSIONED = re.compile(r"^[a-z0-9-]+\.v\d+\.[a-z0-9]+$")
FIXED = {"meta.json", "review.md", "validation.md", "source.md", "interpretation.md", "visual-brief.md",
         "show-notes.txt", "edit-instructions.txt", "first-comment.txt", "substack.md", "substack.html",
         "linkedin-post.txt", "reel-hooks.txt", "script.md", "teleprompter.txt", "image.png"}
HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)", re.M)


def check_meta(folder: Path, schema: dict | None) -> list[str]:
    """meta.json against the schema — the three checks that matter, without a library."""
    m = folder / "meta.json"
    if not m.exists():
        return ["meta.json: missing — the container has no identity"]
    try:
        d = json.loads(m.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"meta.json: not valid JSON ({exc})"]
    if not schema:
        return []
    out = []
    props = schema.get("properties", {})
    for k in schema.get("required", []):
        if k not in d:
            out.append(f"meta.json: required field '{k}' is missing")
    for k, v in d.items():
        if k not in props:
            if schema.get("additionalProperties") is False:
                out.append(f"meta.json: field '{k}' is not in the schema")
            continue
        allowed = props[k].get("enum")
        if allowed and v not in allowed:
            out.append(f"meta.json: {k} = {v!r} is not one of {allowed}")
    return out


def check(root: Path, stage: str, name: str, schema: dict | None) -> list[str]:
    folder = root / stage / name
    findings = check_meta(folder, schema)
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
        print(f"{total} finding(s)" + ("" if schema else " — no meta.schema.json at the root, meta.json not checked"))
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
