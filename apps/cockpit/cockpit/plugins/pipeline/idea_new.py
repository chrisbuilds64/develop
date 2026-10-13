#!/usr/bin/env python3
"""Enter an idea — the first container of a piece, in 10-ideas.

    idea_new.py --label FN --title "Working title" --by chris [--series SIM] [--kind idea|script|draft|transcript|notes]
                [--text "…"] [--file /path/to/upload --name original.md]

What a piece begins with is `--kind`: an idea (the default, a few lines), a finished script
(POD), a finished draft (FN, WN, SP), a transcript, or notes. The text comes on stdin, as
--text, or as an uploaded file (.md or .txt). Writes one folder into 10-ideas at the pipeline
root (COCKPIT_DATA_DIR): meta.json as a seed (checked against meta.schema.json before anything
is written), source.md as the intake note, and — for script, draft, transcript, notes — the
material under its canonical name (script.md, substack.md or linkedin-post.txt, transcript.md,
notes.md). Nothing else. No number yet — `xxx` stands where the number will go; the
interpretation or derivation gives the piece its number (or its place in the series).

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
KINDS = ("idea", "script", "draft", "transcript", "notes")
# where finished material lands, by kind and label — the primary artifact /interpret would have written
PRIMARY = {"script": {"POD": "script.md"},
           "draft": {"FN": "substack.md", "WN": "substack.md", "SP": "linkedin-post.txt", "POD": "script.md"},
           "transcript": {"*": "transcript.md"}, "notes": {"*": "notes.md"}}
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
    p.add_argument("--kind", default="idea", choices=KINDS, help="what the piece begins with")
    p.add_argument("--text", default=None, help="the text; read from stdin when absent and no --file is given")
    p.add_argument("--file", default=None, help="an uploaded .md or .txt file with the material")
    p.add_argument("--name", default="", help="the uploaded file's original name (for the type check and the record)")
    p.add_argument("--put", nargs=3, action="append", default=[], metavar=("ARTIFACT", "ORIGINAL-NAME", "TMPFILE"),
                   help="an artifact that already exists, by its file name from artifacts.json; repeatable")
    a = p.parse_args(argv)

    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    label, title, series, kind = a.label.strip().upper(), " ".join(a.title.split()), a.series.strip().upper(), a.kind
    material_name = (a.name or (Path(a.file).name if a.file else "")).strip()
    if a.file:
        ext = material_name.rsplit(".", 1)[-1].lower() if "." in material_name else ""
        if ext not in ("md", "txt"):
            sys.exit(f"'{material_name or a.file}' is not a text file — .md or .txt")
        try:
            text = Path(a.file).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            sys.exit(f"cannot read the upload: {exc}")
    else:
        text = (a.text if a.text is not None else ("" if sys.stdin.isatty() else sys.stdin.read())).strip()

    if not (root / IDEAS).is_dir():
        sys.exit(f"no {IDEAS}/ at the pipeline root — this is not a pipeline")
    schema = load_json(root, "meta.schema.json")
    labels = (schema or {}).get("properties", {}).get("label", {}).get("enum")
    if labels and label not in labels:
        sys.exit(f"label '{label}' is not one of: {', '.join(labels)}")
    if not title:
        sys.exit("the title is empty")
    puts = []
    if a.put:
        known = {}
        art = load_json(root, "artifacts.json") or {}
        for fmt, spec in art.get("formats", {}).items():
            for x in spec.get("artifacts", []):
                known.setdefault(x["file"] if isinstance(x, dict) else x, set()).add(fmt)
        for artifact, orig, tmp in a.put:
            if artifact not in known:
                sys.exit(f"'{artifact}' is not an artifact artifacts.json knows")
            if label not in known[artifact]:
                sys.exit(f"'{artifact}' is not an artifact of a {label}")
            ext_a = artifact.rsplit(".", 1)[-1]; ext_o = orig.rsplit(".", 1)[-1].lower() if "." in orig else ""
            if ext_o not in (ext_a, "jpeg" if ext_a == "jpg" else ext_a):
                sys.exit(f"'{orig}' does not fit {artifact} — expected .{ext_a}")
            if not Path(tmp).is_file() or Path(tmp).stat().st_size == 0:
                sys.exit(f"the upload for {artifact} is missing or empty")
            puts.append((artifact, orig, Path(tmp)))
    if not text and not puts:
        sys.exit("the text is empty — a title alone is not an idea" if kind == "idea" else f"no {kind} given — paste it or upload the file")
    if not text and puts:
        kind, text = "idea", f"Brought in with material: {', '.join(x[0] for x in puts)}."
    primary = (PRIMARY.get(kind) or {}).get(label) or (PRIMARY.get(kind) or {}).get("*")
    if kind != "idea" and not primary:
        sys.exit(f"a {kind} is not a way to begin a {label} — one of: idea, " + ", ".join(k for k in KINDS[1:] if (PRIMARY[k].get(label) or PRIMARY[k].get("*"))))

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
    origin = (f"entered by {who['name']} in the cockpit" if kind == "idea"
              else f"{kind} by {who['name']}, brought in through the cockpit" + (f" as {material_name}" if material_name else ""))
    meta = {
        "label": label, "slug": folder, "title": title, "working_title": title,
        "created": today, "origin": origin, "seed": True,
    }
    if series:
        meta["series"] = series
    problems = schema_check(meta, schema)
    if problems:
        sys.exit("refused — " + "; ".join(problems))

    head = [f"# Source — {title}", "",
            f"**Created:** {today} · **By:** {who['name']} · **Format:** {label}"
            + (f" · **Series:** `{series}` — construct: `series/{series}/construct.md`" if series else "")
            + (f" · **Begins with:** {kind} (`{primary}`)" if kind != "idea" else ""), ""]
    if kind == "idea":
        head += ["## Core Concept", "", text, ""]
    else:
        head += [f"The {kind} is the author's and sits in `{primary}`. It is not rewritten; derived files come from it (`/derive`).", ""]
    target = root / IDEAS / folder
    target.mkdir()
    (target / "source.md").write_text("\n".join(head), encoding="utf-8")
    if kind != "idea":
        (target / primary).write_text(text + "\n", encoding="utf-8")
    for artifact, orig, tmp in puts:
        if (target / artifact).exists():
            continue                                           # the pasted primary wins over an upload of the same name
        (target / artifact).write_bytes(tmp.read_bytes())
    if puts:
        meta["origin"] += " — with " + ", ".join(x[0] for x in puts)
    (target / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"created {IDEAS}/{folder} — {label} by {who['name']}" + (f", {kind} in {primary}" if kind != "idea" else "")
          + (f", with {', '.join(x[0] for x in puts)}" if puts else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
