# Cockpit

A surface over the engine. It shows what the tools know and owns none of their data.

Three sentences carry the design:

1. **Nothing is readable that is not named.** Sources are declared in `cockpit.toml`; deny is the default.
2. **The cockpit writes nothing a tool owns.** It reads. The tool that owns a file is the only thing that changes it.
3. **Every access is recorded** — refused ones included, with the reason.

## Run

```bash
pipx install .            # or: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cockpit init              # writes cockpit.toml next to you, commented
cockpit check             # every source, every module, every role — before anyone watches
cockpit run               # http://127.0.0.1:8200
cockpit run --demo        # the shipped fixtures, nothing from this machine
cockpit export --lang de --out overview.html   # one file, no server, for mail and projector
```

Python 3.11 or newer. No build step, no Node, no database. HTMX ships as a file in `static/`.

## Configuration

Three segments, read in this order:

| Segment | Says |
|---|---|
| `[[source]]` | a directory the cockpit may read — path, release list, sensitivity (`public` < `internal` < `confidential`) |
| `[[module]]` | a card — its reader, the sources it needs, its maturity (`running` · `draft` · `planned` · `assumption`) |
| `[[role]]` | who may open which modules, and up to which sensitivity |

`cockpit.example.toml` explains every option. A module whose source the current role may
not see does not vanish — it shows as *not released*, so what exists stays visible and the
release stays a decision.

## The contract

A module reports a **panel**: one state (`ok` · `attention` · `blocked`), one headline number,
up to five lines, and where the numbers come from. `cockpit/schemas/panel.schema.json` is the
contract; it appears unchanged in `/openapi.json` under `components.schemas.Panel`, because
OpenAPI 3.1 speaks the same JSON Schema.

A panel is checked before it is shown — shape first, then freshness. One that fails is
rendered as a card that says so. An empty card is honest; a wrong number on a screen is not.

## Adding a module

A reader is a function of about thirty lines:

```python
def read(access, role, module, config) -> dict:   # returns a panel
```

It reads only through `access` and reports `as_of` as the time of the data, not of reading.
Drop it in `cockpit/readers/`, add a `[[module]]` that names it, done. The core does not change.

## Adding a language

Copy `cockpit/locales/en.json` to `<code>.json`, translate, keep `_name`. It appears in the
switcher. Readers speak in keys, never in sentences, so no code is touched.

## Actions

A card that only shows is a dashboard. A plugin may bring **actions**: forms that run the
tool owning the data — `todo.py add`, `todo.py done` — through the tool's own command. The
cockpit never writes the file; it runs the program that does, and that program validates.

Actions are defined **once, in the plugin's `plugin.json`**, never in an instance's
configuration:

```json
"needs": ["worklist", "tools"],
"actions": [
  {"id": "add", "label": "worklist.add",
   "tool": "tools", "command": "todo.py", "data": "worklist",
   "args": ["add", "{title}", "--cluster", "{cluster}", "--due", "{due}"],
   "field": [{"name": "title", "required": true},
             {"name": "cluster", "type": "select", "options_from": "todo.json:lov.clusters"}]}
]
```

`tool` is `"plugin"` (the script sits in the plugin directory) or a name from `needs` (a released
script of the customer's); `data` is the name from `needs` the tool works on. The instance maps
`needs` onto its own sources by position (`sources = ["worklist", "tools"]`) and that is all it
has to say. An action is offered only where everything it needs is released — the tool's source,
and the data source `read-write`; otherwise it is **withheld**, and `cockpit check` says which and
why. An instance that opens a source for reading gets the reader, not the buttons.

An instance may keep a subset (`actions = ["move", "verify"]` on the module) and may add actions
of its own as `[[module.action]]` with the same fields; it cannot redefine one the plugin brings.

Field values become **arguments, never a shell string** — an injection attempt arrives as one
harmless argument. An empty optional field drops its flag. A role must be granted the action
by name (`actions = ["worklist.add"]`) or `*`; every run is recorded with its outcome.

A field of `type = "file"` is an upload. The cockpit stores it in a temporary file, refuses
it above `max_upload_mb` (default 50) or outside the field's `accept` list, and hands the tool
the path as `{file}` and the original name as `{file.name}`. The tool decides where the file
goes and what it is called — the pipeline's `asset_put.py` writes `<kind>.vN.<ext>` into the
piece, next version each time, and never overwrites. `{user}` is the signed-in name, for a
`--by`. Images and video inside a released source are served at `/m/<module>/file/<path>`,
through the same access check as every read; a document may list them and the page shows them.

## Figures

A panel may carry one **figure** — typed data the surface draws as SVG: `bar` (segments),
`ring` (value of a whole), `flow` (stages with counts), `route` (where data goes: inside the
building or out). Readers send numbers, never markup. A new kind is one macro in
`templates/figures.html` and one value in the schema.

## Languages

English is primary; German ships. A language is one JSON file in `cockpit/locales/` — copy
`en.json`, translate, keep `_name`. Readers and templates speak in keys, so the core is not
touched. The switch is in the header.

## Demo

`cockpit run --demo` reads `fixtures/` — an invented company, nothing from this machine.
Actions write through the real tools, so click freely; `python3 fixtures/make.py` resets it.

## Behind the card

A card is the entry. `Open` leads to the working view: typed **blocks** a reader returns —
`kanban` (columns with cards), `table` (rows, cells may be links or badges), `document`
(markdown, rendered by the surface), `links` (other tools). A reader may also serve single
documents under `/m/<module>/doc/<ref>` — an audit, a content piece, a procedure.

The pipeline opens as a board by stage with every piece; audits open as a table of runs plus a
table of findings in their current state, each linking to the audit that carries it. Same
contract for every module (`schemas/detail.schema.json`); a new module gets the full view
without a new template.

## Users

```bash
cockpit user add alex --role operator --context ~/loops/alex/context
cockpit user list
```

A user has a role and a **context directory** — their Context Loop folder. A source may say
`path = "{user.context}"`, and for the signed-in user it resolves to their folder: one cockpit,
several people, each on their own state, no database. With users on file, sign-in is required;
the first visit plays a short intro, then the sign-in. Passwords are PBKDF2 hashes in
`users.json`, sessions are HMAC-signed cookies over a secret file (mode 600). A password has
ten characters or more. After `lockout_after` failed attempts (default 5) a name is locked
for `lockout_minutes` (default 15); each attempt is an audit line with the client's address.
Elementary by design: no reset, no e-mail.

Before the cockpit faces the internet: `secure_cookies = true` (behind TLS), `login_required
= true` written down rather than inferred, and `uvicorn --proxy-headers` so the address in
the audit is the client's, not the proxy's. `/docs` and `/openapi.json` sit behind the sign-in.

## Plugins

```bash
cockpit plugin list
cockpit plugin add ../gatehouse --link     # --link symlinks, for development
cockpit plugin remove gatehouse
```

The cockpit is the surface; **plugins** bring the mechanisms. A plugin is a directory with a
`plugin.json` (`cockpit/schemas/plugin.schema.json`) that declares a reader — the card and the
working view — its actions, and optionally a **whole web application** mounted under
`/m/<id>/app`, running inside the cockpit's process and URL. Gatehouse is the first: the
interview, the artifacts, the reading and the audit are all reachable from its card. The one
requirement for an app to be mountable is that it builds its links from
`request.scope["root_path"]`.

Bundled plugins live in `cockpit/plugins/`; installed ones next to the configuration in
`plugins/`, and an installed one shadows a bundled one of the same id. A module names its
plugin and the sources it releases — reader, app, locales and actions come from the manifest.

**The example plugin is `decisions`**: three files. `plugin.json` declares it, `reader.py`
turns the Context Loop decision log into a card and a table, `decide.py` is the tool an
action runs to record a decision — into the signed-in user's context. Copy it to start your own.

A customer's own tool is attached the same way: manifest, reader, released sources. Nothing in
the core changes for a new plugin — that is the test for whether the boundary holds.

**The trust boundary, plainly:** a plugin runs inside the cockpit's process with the cockpit's
rights. The access layer governs readers that go through it; it cannot stop code that does not.
"Nothing is readable that is not named" holds for plugins you have read. Install those. For
plugins that talk to outside systems, the rule for secrets is Gatehouse's: never in
`cockpit.toml`, only the *name* of an environment variable that holds the value.

**Next:** a source kind `http`, so a reader can consult an API — Jira, Confluence, a ticket
system — under the same rules as a directory: named, released, per role, recorded.

## Setup

`/setup` — for roles granted `setup.view` or `*` — shows what the cockpit is made of: plugins
(origin, version, app, used by), sources (kind, mode, sensitivity, release list), modules, roles,
and **every schema it knows**: its own three, and any `*.schema.json` inside a released source,
each as a table of attributes.

A schema in a source with `mode = "read-write"` can be **extended** from there: one attribute
at a time, with type, description, optional allowed values, optionally required, at the top
level or inside a `$defs` type. It runs the bundled `tools/schema_add.py`, which refuses to
overwrite anything that exists. Define first, then use — and the tool that owns the data
(`todo.py`) validates against the extended schema on its next write.

`mode` matters now: an action whose `data` points at a source that is not `read-write` is
refused when the configuration loads. The cockpit never writes; released tools may.
