#!/usr/bin/env python3
"""Enter an idea — the first container of a piece, in 10-ideas.

    idea_new.py --label FN --title "Working title" --by chris [--series SIM] [--text "…"]

The idea text comes on stdin when --text is absent. Writes one folder into
10-ideas at the pipeline root (COCKPIT_DATA_DIR): meta.json as a seed (checked
against meta.schema.json before anything is written) and source.md with the
text. Nothing else. No number yet — `xxx` stands where the number will go;
the interpretation gives the piece its number (or its place in the series).

Refuses: a label the schema does not list, a person people.json does not know,
a series without a head in series/<LABEL>/, an empty text, a folder of that
name anywhere in the pipeline. Nothing refused leaves a trace.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

try:
    from cockpit.schema import check as schema_check
except ImportError:                                   # run by hand from the source tree, outside the cockpit's interpreter
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from cockpit.schema import check as schema_check

STAGE = re.compile(r"^\d{2}-")
IDEAS = "10-ideas"
UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def slugify(title: str, limit: int = 60) -> str:
    s = unicodedata.normalize("NFKD", title.translate(UMLAUTS)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0]
    return s


def load_json(root: Path, name: str) -> dict | None:
    p = root / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="idea_new.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--label", required=True, help="content type, as meta.schema.json lists it (FN, POD, SP, WN)")
    p.add_argument("--title", required=True, help="the working title")
    p.add_argument("--by", required=True, help="who enters it — id or name from people.json")
    p.add_argument("--series", default="", help="series label, only if series/<LABEL>/series.json exists")
    p.add_argument("--text", default=None, help="the idea; read from stdin when absent")
    a = p.parse_args(argv)

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    label, title, series = a.label.strip().upper(), " ".join(a.title.split()), a.series.strip().upper()
    text = (a.text if a.text is not None else sys.stdin.read()).strip()

    if not (root / IDEAS).is_dir():
        sys.exit(f"no {IDEAS}/ at the pipeline root — this is not a pipeline")
    schema = load_json(root, "meta.schema.json")
    labels = (schema or {}).get("properties", {}).get("label", {}).get("enum")
    if labels and label not in labels:
        sys.exit(f"label '{label}' is not one of: {', '.join(labels)}")
    if not title:
        sys.exit("the title is empty")
    if not text:
        sys.exit("the idea text is empty — a title alone is not an idea")

    people = load_json(root, "people.json")
    if people is None:
        sys.exit("no people.json at the pipeline root — nobody can enter an idea")
    who = next((x for x in people.get("people", []) if a.by.strip().lower() in (x["id"].lower(), x["name"].lower())), None)
    if not who:
        sys.exit(f"'{a.by}' is not in people.json — add the person there first")

    if series and not (root / "series" / series / "series.json").is_file():
        sys.exit(f"series '{series}' has no head — series/{series}/series.json does not exist")

    slug = slugify(title)
    if not slug:
        sys.exit(f"'{title}' leaves nothing for a folder name")
    folder = f"{label}-{series + '-xx' if series else 'xxx'}-{slug}"
    stages = [x.name for x in root.iterdir() if x.is_dir() and STAGE.match(x.name)]
    taken = [s for s in stages if (root / s / folder).exists()]
    if taken:
        sys.exit(f"{folder} already exists in {', '.join(taken)} — nothing overwritten")

    today = dt.date.today().isoformat()
    meta = {
        "label": label, "slug": folder, "title": title, "working_title": title,
        "created": today, "origin": f"entered by {who['name']} in the cockpit", "seed": True,
    }
    if series:
        meta["series"] = series
    problems = schema_check(meta, schema)
    if problems:
        sys.exit("refused — " + "; ".join(problems))

    head = [f"# Source — {title}", "",
            f"**Created:** {today} · **By:** {who['name']} · **Format:** {label}"
            + (f" · **Series:** `{series}` — construct: `series/{series}/construct.md`" if series else ""),
            "", "## Core Concept", "", text, ""]
    target = root / IDEAS / folder
    target.mkdir()
    (target / "source.md").write_text("\n".join(head), encoding="utf-8")
    (target / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"created {IDEAS}/{folder} — {label} by {who['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
