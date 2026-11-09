"""PROD (/) and ENTW (/entw) share one origin, so they share the browser's storage. The Casefile entry opens the workspace
you were last in, from that storage; it must only ever open a workspace of its own stage (found 2026-11-09: the PROD
cockpit sent the product owner into ENTW's Shipyard)."""

import re
from pathlib import Path

T = Path(__file__).resolve().parents[1] / "cockpit" / "templates"


def test_the_remembered_workspace_is_followed_only_within_the_cockpits_own_stage():
    for name in ("base.html", "index.html"):
        text = (T / name).read_text(encoding="utf-8")
        script = next(s for s in re.findall(r"<script>(.*?)</script>", text, re.S) if "casefile-last" in s)
        assert "own + 'w/'" in script, name                  # the stage prefix of this page's own link
        assert "/^\\/(?:[\\w-]+\\/)*w\\/" not in script, name   # the old pattern took any stage's workspace
