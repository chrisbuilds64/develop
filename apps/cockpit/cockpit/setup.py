"""The setup area: what the cockpit is made of, visible — and schemas extensible.

Plugins, sources, modules, roles as the configuration declares them, and every
JSON Schema the cockpit knows: its own three, and any `*.schema.json` inside a
released source. A schema is shown as a table of attributes; one that lives in
a source released for writing can be extended from here — through the bundled
`schema_add.py`, never by editing JSON in a browser. Define first, then use.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .access import Access, Denied
from .config import Config, Role

HERE = Path(__file__).parent
OWN_SCHEMAS = ("panel", "detail", "plugin")


def _fields(schema: dict, node: dict | None = None, prefix: str = "") -> list[dict]:
    """Flatten an object schema into rows: name, type, required, description."""
    node = node if node is not None else schema
    rows = []
    required = set(node.get("required", []))
    for name, prop in node.get("properties", {}).items():
        if "$ref" in prop:
            target = prop["$ref"].split("/")[-1]
            typ = f"→ {target}"
        elif "enum" in prop:
            typ = "one of: " + ", ".join(map(str, prop["enum"]))
        elif "oneOf" in prop:
            typ = " | ".join(("→ " + o["$ref"].split("/")[-1]) if "$ref" in o else str(o.get("type")) for o in prop["oneOf"])
        else:
            t = prop.get("type")
            typ = "/".join(t) if isinstance(t, list) else (t or "—")
            if t == "array" and "items" in prop:
                it = prop["items"]
                typ += " of " + (("→ " + it["$ref"].split("/")[-1]) if "$ref" in it else str(it.get("type", "…")))
        rows.append({"name": prefix + name, "type": typ, "required": name in required,
                     "description": prop.get("description", "")})
    return rows


def schemas_for(config: Config, access: Access, role: Role) -> list[dict]:
    out = []
    for name in OWN_SCHEMAS:
        path = HERE / "schemas" / f"{name}.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        out.append({"id": f"cockpit:{name}", "title": schema.get("title", name), "owner": "cockpit",
                    "path": str(path), "writable": False, "schema": schema,
                    "fields": _fields(schema), "defs": {k: _fields(schema, v) for k, v in schema.get("$defs", {}).items()
                                                         if v.get("type") == "object"},
                    "description": schema.get("description", "")})
    for sid, src in access._sources.items():
        if not role.may_see(src.sensitivity):
            continue
        try:
            names = access.listdir(sid, role)
        except Denied:
            continue
        for n in names:
            if not n.endswith(".schema.json"):
                continue
            try:
                schema = access.read_json(sid, n, role)
                path = access.resolve(sid, n, role)
            except Denied:
                continue
            out.append({"id": f"{sid}:{n}", "title": schema.get("title", n), "owner": src.label,
                        "path": str(path), "writable": src.mode == "read-write", "schema": schema,
                        "fields": _fields(schema), "defs": {k: _fields(schema, v) for k, v in schema.get("$defs", {}).items()
                                                             if v.get("type") == "object"},
                        "description": schema.get("description", "")})
    return out


def add_attribute(config: Config, access: Access, role: Role, schema_id: str, form: dict) -> tuple[bool, str]:
    """Run schema_add.py against a schema in a writable source. Everything else is refused."""
    sid, _, name = schema_id.partition(":")
    src = access.source(sid)
    if src is None or src.mode != "read-write":
        return False, f"'{schema_id}' is not in a source released for writing"
    try:
        path = access.resolve(sid, name, role)
    except Denied as exc:
        return False, str(exc)
    argv = [sys.executable, str(HERE / "tools" / "schema_add.py"), str(path), form.get("name", "").strip(),
            "--type", form.get("type", "string")]
    if form.get("description", "").strip():
        argv += ["--description", form["description"].strip()]
    if form.get("required"):
        argv.append("--required")
    if form.get("target", "").strip():
        argv += ["--target", form["target"].strip()]
    if form.get("enum", "").strip():
        argv += ["--enum", form["enum"].strip()]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=15)
    out = (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
    access._audit.record(role.id, sid, name, "act", ok=r.returncode == 0, reason=None if r.returncode == 0 else out[-300:])
    return r.returncode == 0, out
