"""The one schema checker.

Every JSON document the cockpit or one of its tools accepts — a panel, a detail
view, a plugin manifest, a container's meta.json, a review entry, a run order —
is checked against its schema here, with the same rules and the same words:

- required fields are present
- a field with a value list carries one of its values
- a field the schema does not define is refused (when the schema says
  `additionalProperties: false`)
- types, patterns and lengths hold, in nested objects and arrays too

It covers the JSON Schema subset this project uses and needs no library. One
checker, so a rule holds everywhere or nowhere; before it, four copies had
drifted apart in what they refused and how they said it.
"""

from __future__ import annotations

import re

TYPES = {"object": dict, "array": list, "string": str, "integer": int,
         "number": (int, float), "boolean": bool, "null": type(None)}


def resolve(ref: str, root: dict):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def check(node, schema: dict | None, root: dict | None = None, path: str = "") -> list[str]:
    """Problems as a list of sentences; empty means the document fits.

    `path` prefixes nested findings ("guests[0]: required field 'name' is missing");
    at the top level the sentence stands alone.
    """
    if not schema:
        return []
    root = root if root is not None else schema
    out: list[str] = []
    _walk(node, schema, root, path, out)
    return out


def _at(path: str) -> str:
    return f"{path}: " if path else ""


def _walk(node, schema: dict, root: dict, path: str, out: list[str]) -> None:
    if "$ref" in schema:
        return _walk(node, resolve(schema["$ref"], root), root, path, out)
    t = schema.get("type")
    if t:
        want = t if isinstance(t, list) else [t]
        ok = any(isinstance(node, TYPES[w]) and not (w in ("integer", "number") and isinstance(node, bool))
                 for w in want)
        if not ok:
            out.append(f"{path or 'document'}: expected {'/'.join(want)}, got {type(node).__name__}")
            return
    if "enum" in schema and node not in schema["enum"]:
        out.append(f"{path or 'value'} = {node!r} is not one of {schema['enum']}")
    if isinstance(node, str):
        if "pattern" in schema and not re.search(schema["pattern"], node):
            out.append(f"{path or 'value'} = {node!r} does not match {schema['pattern']}")
        if len(node) < schema.get("minLength", 0):
            out.append(f"{path or 'value'}: empty")
    if isinstance(node, list):
        if len(node) > schema.get("maxItems", 10**9):
            out.append(f"{path or 'list'}: more than {schema['maxItems']} entries")
        if "items" in schema:
            for i, v in enumerate(node):
                _walk(v, schema["items"], root, f"{path}[{i}]", out)
    if isinstance(node, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in node:
                out.append(f"{_at(path)}required field '{key}' is missing")
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    out.append(f"{_at(path)}unknown field '{key}' — define it in the schema first")
        for key, val in node.items():
            if key in props:
                _walk(val, props[key], root, f"{path}.{key}" if path else key, out)
