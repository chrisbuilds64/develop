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
            if f.options and v and v not in f.options:
                raise Denied(f"'{v}' is not an allowed value for '{f.name}'")
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
        out = (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
        self._audit.record(role.id, action.tool, name, "act", ok=r.returncode == 0,
                           reason=None if r.returncode == 0 else out[-300:])
        return Outcome(r.returncode == 0, out, argv[1:])
