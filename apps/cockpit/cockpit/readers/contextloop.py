"""Context Loop: the package as it is on disk — version and procedures."""

from __future__ import annotations

from . import now_iso


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    manifest = access.read_json(src, ".claude-plugin/plugin.json", role)
    procedures = [n for n in access.listdir(src, role, "skills")]

    # A package manifest does not age: an unchanged file is current, not stale.
    # This is a live read of what is on disk, so as_of is now.
    return {
        "title": "contextloop.title",
        "subtitle": "contextloop.subtitle",
        "as_of": now_iso(),
        "state": "ok",
        "headline": {"value": len(procedures), "unit": "contextloop.procedures"},
        "lines": [
            {"label": "contextloop.version", "value": manifest.get("version", "—"), "tone": "ok"},
            {"label": "contextloop.procedures", "value": ", ".join(procedures), "tone": "muted"},
        ],
        "source": f"{access.source(src).label} · plugin.json",
        "figure": {"kind": "flow", "steps": [{"label": p, "value": 1, "tone": "accent"} for p in procedures]},
    }
