#!/usr/bin/env python3
"""Add one attribute to a JSON Schema — define it first, then use it.

    schema_add.py <schema.json> <name> --type string|integer|number|boolean|date
                  [--description "…"] [--required] [--target "$defs.todo"] [--enum a,b,c]

The schema stays valid JSON Schema 2020-12; the attribute lands under
`properties` of the target object (top level, or a `$defs` entry). Refuses to
overwrite an attribute that exists. `date` becomes a string with the ISO
pattern the cockpit uses everywhere.
"""
import argparse
import json
import sys
from pathlib import Path

DATE = {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="schema_add.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("schema"); p.add_argument("name")
    p.add_argument("--type", required=True, choices=["string", "integer", "number", "boolean", "date"])
    p.add_argument("--description", default=""); p.add_argument("--required", action="store_true")
    p.add_argument("--target", default="", help="e.g. $defs.todo — empty means the top-level object")
    p.add_argument("--enum", default="")
    a = p.parse_args(argv)

    path = Path(a.schema)
    schema = json.loads(path.read_text(encoding="utf-8"))
    node = schema
    for part in [x for x in a.target.split(".") if x]:
        if part not in node:
            sys.exit(f"'{a.target}' not found in {path.name}")
        node = node[part]
    if node.get("type") != "object":
        sys.exit(f"target is not an object (type = {node.get('type')!r})")
    props = node.setdefault("properties", {})
    if a.name in props:
        sys.exit(f"'{a.name}' already exists — attributes are added, never overwritten")

    prop = dict(DATE) if a.type == "date" else {"type": a.type}
    if a.description:
        prop["description"] = a.description
    if a.enum:
        prop = {"enum": [x.strip() for x in a.enum.split(",") if x.strip()]}
        if a.description:
            prop["description"] = a.description
    props[a.name] = prop
    if a.required:
        node.setdefault("required", [])
        if a.name not in node["required"]:
            node["required"].append(a.name)

    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    where = a.target or "top level"
    print(f"added '{a.name}' ({a.type}{', required' if a.required else ''}) at {where} of {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
