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

A card that only shows is a dashboard. A module may declare **actions**: forms that run the
tool owning the data — `todo.py add`, `todo.py done` — through the tool's own command. The
cockpit never writes the file; it runs the program that does, and that program validates.

```toml
[[module.action]]
id = "add"
label = "worklist.add"
tool = "tools"            # a source; the script must be released from it like any file
command = "todo.py"
data = "worklist"         # the source the tool works on
args = ["add", "{title}", "--cluster", "{cluster}", "--due", "{due}"]
  [[module.action.field]]
  name = "title"
  required = true
```

Field values become **arguments, never a shell string** — an injection attempt arrives as one
harmless argument. An empty optional field drops its flag. A role must be granted the action
by name (`actions = ["worklist.add"]`) or `*`; every run is recorded with its outcome.

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
