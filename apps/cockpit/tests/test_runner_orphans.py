"""A deploy restarts the runner; a run it had taken stays "running" for ever unless the runner says what happened
(found 2026-11-09 on ENTW: a release run cut off by its own stage's deploy)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline"))

import runner  # noqa: E402


def order(q: Path, rid: str, **kw):
    (q / f"{rid}.json").write_text(json.dumps({"id": rid, "skill": "x", **kw}), encoding="utf-8")


def test_a_run_this_runner_had_taken_is_marked_failed_with_what_happened_at_start(tmp_path):
    order(tmp_path, "mine", status="running", taken_by="runner@host/entw", started="2026-11-09T12:32:36+01:00")
    order(tmp_path, "other", status="running", taken_by="runner@host/prod")
    order(tmp_path, "waiting", status="queued")
    order(tmp_path, "done", status="done", taken_by="runner@host/entw")
    assert runner.orphans(tmp_path, "runner@host/entw") == ["mine"]
    mine = json.loads((tmp_path / "mine.json").read_text())
    assert mine["status"] == "failed" and "Interrupted" in mine["result"] and mine["finished"]
    assert json.loads((tmp_path / "other.json").read_text())["status"] == "running"      # another runner's run
    assert json.loads((tmp_path / "waiting.json").read_text())["status"] == "queued"
