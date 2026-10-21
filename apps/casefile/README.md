# casefile

The case that leads itself. Folders are the truth, one core writes, a step is one button.

A case is a folder inside a stage folder. The stage folder is its status. `meta.json` describes it,
`review.md` is its append-only thread, deliverables are versioned files beside them, and a helper
run is an order file in `_runs/`. People sync the tree; this core is the only thing that writes
into it on their behalf (ADR-013).

Two functions carry everything:

- `turn(case)` says whose move it is: a run is running → Claude; the last run failed → the operator;
  an open entry addressed to someone → that person; otherwise the stage says who, what, and which
  deliverables the move needs. Pure, reads only.
- `step(case, action, by, payload, step_id)` makes one move whole or not at all: lock the case,
  check the precondition, journal the intent in `_steps/`, append the thread entry, move the folder,
  mark the journal done. The same step id twice is a no-op. A journal left half-way is completed on
  the next start.

Nothing in the code names a domain. Stages, deliverables, words and people are files per domain
(`config/<domain>/`, ADR-015); a pipeline root may carry its own `artifacts.json`, `vocabulary.json`
and `people.json`, which win.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m casefile.cli.inventory <pipeline-root>     # a read-only report over a real tree
```

Python 3.11 or newer. The surface (a static app served by the core, ADR-014) and the API follow.
