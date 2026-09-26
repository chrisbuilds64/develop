#!/usr/bin/env python3
"""Verify a to-do file against its schema — shape first, then the references.

JSON Schema checks the shape of a document. It cannot check that a todo's
"cluster" actually exists in lov.clusters, because that is a relation inside the
file. So this runs in two passes:

  1. Shape — against todo.schema.json. Uses the `jsonschema` package when it is
     installed; otherwise a built-in checker for the subset the schema uses.
  2. References — every id a todo points at must exist, ids must be unique, and
     dependencies must not run in a circle.

Exit code 0 = clean, 1 = findings. Usage: todo_validate.py [file.json] [schema.json]
"""
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- shape

def resolve(ref, root):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def check(node, schema, root, path="$", out=None):
    """The JSON Schema subset this project's schema actually uses."""
    out = out if out is not None else []
    if "$ref" in schema:
        return check(node, resolve(schema["$ref"], root), root, path, out)
    if "oneOf" in schema:
        if not any(not check(node, s, root, path, []) for s in schema["oneOf"]):
            out.append(f"{path}: passt auf keine der erlaubten Formen")
        return out
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int,
             "boolean": bool, "null": type(None)}
    if t:
        want = types[t]
        ok = isinstance(node, want) and not (want is int and isinstance(node, bool))
        if not ok:
            out.append(f"{path}: erwartet {t}, ist {type(node).__name__}")
            return out
    if "const" in schema and node != schema["const"]:
        out.append(f"{path}: muss {schema['const']!r} sein")
    if "enum" in schema and node not in schema["enum"]:
        out.append(f"{path}: {node!r} nicht in {schema['enum']}")
    if isinstance(node, str):
        if "pattern" in schema and not re.search(schema["pattern"], node):
            out.append(f"{path}: {node!r} passt nicht auf {schema['pattern']}")
        if len(node) < schema.get("minLength", 0):
            out.append(f"{path}: leer")
    if isinstance(node, list):
        if len(node) < schema.get("minItems", 0):
            out.append(f"{path}: zu wenige Einträge")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in node}) != len(node):
            out.append(f"{path}: doppelte Einträge")
        for i, v in enumerate(node):
            if "items" in schema:
                check(v, schema["items"], root, f"{path}[{i}]", out)
    if isinstance(node, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in node:
                out.append(f"{path}: Feld '{key}' fehlt")
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    out.append(f"{path}: unbekanntes Feld '{key}' — erst im Schema definieren")
        for key, val in node.items():
            if key in props:
                check(val, props[key], root, f"{path}.{key}", out)
    return out


def shape(doc, schema):
    try:
        import jsonschema
    except ImportError:
        return check(doc, schema, schema), "eingebauter Prüfer"
    v = jsonschema.Draft202012Validator(schema)
    errs = [f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in v.iter_errors(doc)]
    return errs, "jsonschema"

# ---------------------------------------------------------------- references

def references(doc):
    out = []
    lov = doc.get("lov", {})
    ids = {name: {e["id"] for e in lov.get(name, [])} for name in
           ("clusters", "statuses", "priorities", "people", "sourceKinds")}
    todos = doc.get("todos", [])

    seen = set()
    for t in todos:
        tid = t.get("id", "?")
        if tid in seen:
            out.append(f"{tid}: ID kommt mehrfach vor")
        seen.add(tid)

    if doc.get("meta", {}).get("defaultAssignee") not in ids["people"]:
        out.append("meta.defaultAssignee: steht nicht in lov.people")

    for t in todos:
        tid = t.get("id", "?")
        for field, bucket in (("cluster", "clusters"), ("status", "statuses"),
                              ("priority", "priorities"), ("assignee", "people")):
            if t.get(field) and t[field] not in ids[bucket]:
                out.append(f"{tid}.{field}: '{t[field]}' steht nicht in lov.{bucket}")
        for p in t.get("withPeople", []):
            if p not in ids["people"]:
                out.append(f"{tid}.withPeople: '{p}' steht nicht in lov.people")
            if p == t.get("assignee"):
                out.append(f"{tid}.withPeople: '{p}' ist schon zuständig")
        if "source" in t and t["source"]["kind"] not in ids["sourceKinds"]:
            out.append(f"{tid}.source.kind: '{t['source']['kind']}' steht nicht in lov.sourceKinds")
        for b in t.get("blockedBy", []):
            if b == tid:
                out.append(f"{tid}.blockedBy: verweist auf sich selbst")
            elif b not in seen | {x.get("id") for x in todos}:
                out.append(f"{tid}.blockedBy: '{b}' gibt es nicht")
        if t.get("updated") and t.get("created") and t["updated"] < t["created"]:
            out.append(f"{tid}: geändert liegt vor erstellt")
        terminal = {s["id"] for s in lov.get("statuses", []) if s.get("terminal")}
        if t.get("status") in terminal and not t.get("closed"):
            out.append(f"{tid}: Endzustand ohne 'closed'")
        if t.get("status") not in terminal and t.get("closed"):
            out.append(f"{tid}: 'closed' gesetzt, aber Status ist kein Endzustand")

    # Ringe in den Abhängigkeiten
    graph = {t["id"]: list(t.get("blockedBy", [])) for t in todos if "id" in t}
    state = {}
    def walk(n, trail):
        if state.get(n) == "done":
            return
        if state.get(n) == "open":
            out.append("Ringabhängigkeit: " + " → ".join(trail + [n]))
            return
        state[n] = "open"
        for m in graph.get(n, []):
            if m in graph:
                walk(m, trail + [n])
        state[n] = "done"
    for n in graph:
        walk(n, [])
    return out


def find_state():
    """Locate todo.json without being told where it is.

    Two layouts must both work and neither may need configuring:
      context/scripts/todo.py  →  context/todo.json        (the shipped package)
      <x>/scripts/todo.py      →  <x>/context/todo.json    (a project that keeps state in context/)
    CONTEXT_LOOP_DIR overrides both when someone puts the files somewhere else.
    """
    import os
    here = Path(__file__).resolve().parent
    candidates = []
    if os.environ.get("CONTEXT_LOOP_DIR"):
        candidates.append(Path(os.environ["CONTEXT_LOOP_DIR"]))
    candidates += [here.parent, here.parent / "context", here]
    for base in candidates:
        if (base / "todo.json").is_file():
            return base
    return candidates[0]


def main(doc_p=None, sch_p=None):
    base = find_state()
    if doc_p is None:
        doc_p = Path(sys.argv[1]) if len(sys.argv) > 1 else base / "todo.json"
    if sch_p is None:
        sch_p = Path(sys.argv[2]) if len(sys.argv) > 2 else base / "todo.schema.json"
    doc_p, sch_p = Path(doc_p), Path(sch_p)
    doc = json.loads(doc_p.read_text(encoding="utf-8"))
    schema = json.loads(sch_p.read_text(encoding="utf-8"))

    errs, engine = shape(doc, schema)
    refs = references(doc)
    n = len(doc.get("todos", []))
    print(f"{doc_p.name}: {n} Vorgänge · Form geprüft mit {engine}")
    for e in errs:
        print("  FORM  " + e)
    for r in refs:
        print("  BEZUG " + r)
    if not errs and not refs:
        print("  sauber")
        return 0
    print(f"  {len(errs)} Formfehler · {len(refs)} Bezugsfehler")
    return 1


if __name__ == "__main__":
    sys.exit(main())
