#!/usr/bin/env python3
"""Append one entry to a container's review.md — append only, never rewrite.

    review_append.py <container> --by <author> --title <line> [--status open] [--for Akhil] [--resolves REV-002]
                                                                                        text on stdin

The entry is an item: `## REV-NNN — title`, a head line with its attributes, the
text below (see review_entries.py). The number is the next free one in the file,
the date and the stage come from now and from where the container stands. The
attributes are checked against review.schema.json at the pipeline root before
anything is written; a value outside a list is refused, not corrected. Existing
text is never touched: the tool opens the file for appending and writes at the end.

Works in COCKPIT_DATA_DIR (the pipeline root).
"""
import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_entries import canonical, check, load_schema, next_id, render  # noqa: E402

STAGE = re.compile(r"^\d{2}-")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="review_append.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("container")
    p.add_argument("--by", required=True, help="the author — matched to the schema's list, case does not matter")
    p.add_argument("--title", required=True)
    p.add_argument("--status", default="info")
    p.add_argument("--for", dest="for_", default="")
    p.add_argument("--resolves", default="")
    a = p.parse_args(argv)
    text = sys.stdin.read().strip()
    if not text:
        sys.exit("nothing to append")

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    name = a.container.strip().strip("/").split("/")[-1]  # "stage/name" from the surface, "name" from the shell
    if not name or name.startswith("."):
        sys.exit(f"'{name}' is not a container name")
    here = [s for s in sorted(p.name for p in root.iterdir() if p.is_dir() and STAGE.match(p.name)) if (root / s / name).is_dir()]
    if len(here) != 1:
        sys.exit(f"container '{name}' " + ("not found" if not here else f"exists in more than one stage: {', '.join(here)}"))
    target = root / here[0] / name / "review.md"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""

    schema = load_schema(root)
    props = (schema or {}).get("properties", {})
    entry = {
        "id": next_id(existing),
        "date": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
        "author": canonical(a.by, props.get("author", {}).get("enum", [])) or a.by.strip(),
        "status": canonical(a.status, props.get("status", {}).get("enum", [])) or a.status.strip(),
        "stage": here[0],
        "title": a.title.strip(),
        "text": text,
    }
    if a.for_.strip():
        entry["for"] = canonical(a.for_, props.get("for", {}).get("enum", [])) or a.for_.strip()
    if a.resolves.strip():
        entry["resolves"] = a.resolves.strip().upper()
        if not re.search(rf"^## {re.escape(entry['resolves'])} — ", existing, re.M):
            sys.exit(f"{entry['resolves']} is not an entry in this review.md")
    problems = check(entry, schema)
    if problems:
        sys.exit("refused — " + "; ".join(problems))

    if not target.exists():
        target.write_text(f"# Review — {name}\n\nAppend only. Newest entry at the end, never edited afterwards.\n", encoding="utf-8")
    with target.open("a", encoding="utf-8") as fh:
        fh.write(render(entry))
    print(f"{entry['id']} appended to {here[0]}/{name}/review.md — {entry['status']} by {entry['author']}"
          + (f" for {entry['for']}" if entry.get("for") else "") + (f", resolves {entry['resolves']}" if entry.get("resolves") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
