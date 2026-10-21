"""casefile — the case that leads itself.

Folders are the truth (ADR-013): a stage folder is a case's status, `meta.json` describes it,
`review.md` is its append-only thread, deliverables are versioned files, agent runs are order
files in `_runs/`. This package is the one writer over that tree. Two functions carry it:
`turn()` says whose move it is, `step()` makes one move whole or not at all.
"""

__version__ = "0.1.0"
