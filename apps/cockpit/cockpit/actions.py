"""Actions: the cockpit runs the tool that owns the data — it never writes the data.

An action is declared in the configuration, not in code: which module it
belongs to, which released script it runs, which form fields become which
arguments. The runner builds an argument list — never a shell string — so a
field value is a value, not a command. Every run is recorded with its
arguments and outcome, refused ones included.

A role must be granted an action by name (`worklist.add`) or `*`. Deny is the
default here as everywhere.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

from .access import Access, Denied
from .audit import AuditLog
from .config import Action, Config, Module, Role


@dataclass
class Outcome:
    ok: bool
    output: str
    argv: list[str]


class Actions:
    def __init__(self, config: Config, access: Access, audit: AuditLog, plugins: dict | None = None):
        self._config = config
        self._access = access
        self._audit = audit
        self._plugins = plugins or {}

    def find(self, module: Module, action_id: str) -> Action | None:
        return next((a for a in module.actions if a.id == action_id), None)

    def options(self, action: Action, field, role: Role) -> tuple[str, ...]:
        """A select's values: from the config, or from a schema in the action's data source.

        `options_from = "review.schema.json:status"` reads that file through the
        access layer and takes the property's value list. The surface shows what
        the schema allows and the run refuses what it does not — the same list.
        """
        if not field.options_from:
            return field.options
        file, _, prop = field.options_from.partition(":")
        try:
            schema = self._access.read_json(action.data, file, role)
            return tuple(str(v) for v in schema["properties"][prop]["enum"])
        except Exception:
            return ()

    def options_for(self, module: Module, role: Role) -> dict[str, dict[str, tuple[str, ...]]]:
        return {a.id: {f.name: self.options(a, f, role) for f in a.fields if f.type == "select"} for a in module.actions}

    def run(self, module: Module, action: Action, form: dict[str, str], role: Role,
            ref: str | None = None, user: str | None = None) -> Outcome:
        name = f"{module.id}.{action.id}"
        if not role.may_act(name):
            self._audit.record(role.id, action.tool, name, "act", ok=False,
                               reason=f"role '{role.id}' may not run '{name}'")
            raise Denied(f"role '{role.id}' may not run '{name}'")

        if action.tool == "plugin":
            # The plugin's own tool: installed code, inside the plugin directory only.
            plugin = self._plugins.get(module.plugin)
            if plugin is None:
                raise Denied(f"plugin '{module.plugin}' is not installed")
            script = (plugin.path / action.command).resolve()
            if not script.is_relative_to(plugin.path) or not script.is_file():
                raise Denied(f"'{action.command}' is not inside plugin '{module.plugin}'")
            self._audit.record(role.id, f"plugin:{module.plugin}", action.command, "read")
        else:
            # A released script: same source rules as any file, same log line.
            script = self._access.resolve(action.tool, action.command, role)

        values = {"ref": ref or "", "user": user or role.id}
        if action.scope == "document" and not ref:
            raise Denied("this action needs a document")
        for f in action.fields:
            v = (form.get(f.name) or "").strip()
            if f.required and not v:
                raise Denied(f"field '{f.name}' is required")
            if f.type == "file":
                # The surface stored the upload and put its path here; the original name follows.
                if v:
                    orig = form.get(f.name + ".name", "")
                    ext = orig.rsplit(".", 1)[-1].lower() if "." in orig else ""
                    if f.accept and ext not in f.accept:
                        raise Denied(f"'{orig}' is not an allowed file type — one of: {', '.join(f.accept)}")
                    values[f.name + ".name"] = orig
                values[f.name] = v
                continue
            allowed = self.options(action, f, role)
            if allowed and v and v not in allowed:
                raise Denied(f"'{v}' is not an allowed value for '{f.name}' — one of: {', '.join(allowed)}")
            values[f.name] = v

        argv: list[str] = [sys.executable, str(script)]
        for tpl in action.args:
            # "{title}" → the value; an arg whose value is empty is dropped together
            # with the flag before it, so optional fields do not produce "--due ''".
            if tpl.startswith("{") and tpl.endswith("}"):
                v = values.get(tpl[1:-1], "")
                if v == "":
                    if argv and argv[-1].startswith("--"):
                        argv.pop()
                    continue
                argv.append(v)
            else:
                argv.append(tpl)

        env = dict(os.environ)
        data_src = self._access.source(action.data) if action.data else None
        if data_src:
            env["COCKPIT_DATA_DIR"] = env["CONTEXT_LOOP_DIR"] = str(data_src.path.expanduser())

        feed = values.get(action.stdin, "") if action.stdin else None
        r = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120, input=feed)
        Access.forget()                                   # the tool changed the data; nothing cached is trusted
        out = (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
        self._audit.record(role.id, action.tool, name, "act", ok=r.returncode == 0,
                           reason=None if r.returncode == 0 else out[-300:])
        return Outcome(r.returncode == 0, out, argv[1:])
