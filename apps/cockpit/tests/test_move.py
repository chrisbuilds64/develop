"""The PressRoom move as a tool: finds, refuses collisions, never overwrites."""

import os
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "move.py"


def run(root, *args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          env={**os.environ, "COCKPIT_DATA_DIR": str(root)})


def make(tmp_path):
    for s in ("10-ideas", "30-review-human", "40-asset-generation"):
        (tmp_path / s).mkdir()
    (tmp_path / "30-review-human" / "POD-01").mkdir()
    (tmp_path / "30-review-human" / "POD-01" / "meta.json").write_text("{}")
    return tmp_path


def test_a_container_moves_and_keeps_its_files(tmp_path):
    root = make(tmp_path)
    r = run(root, "POD-01", "40-asset-generation")
    assert r.returncode == 0 and "30-review-human → 40-asset-generation" in r.stdout
    assert (root / "40-asset-generation" / "POD-01" / "meta.json").exists()
    assert not (root / "30-review-human" / "POD-01").exists()


def test_unknown_stage_unknown_container_same_stage_are_refused(tmp_path):
    root = make(tmp_path)
    assert run(root, "POD-01", "99-nope").returncode != 0
    assert run(root, "POD-99", "40-asset-generation").returncode != 0
    assert "already in" in run(root, "POD-01", "30-review-human").stderr


def test_nothing_is_ever_overwritten(tmp_path):
    root = make(tmp_path)
    (root / "40-asset-generation" / "POD-01").mkdir()
    r = run(root, "POD-01", "40-asset-generation")
    assert r.returncode != 0 and "more than one stage" in r.stderr
    assert (root / "30-review-human" / "POD-01" / "meta.json").exists()
    assert not (root / "40-asset-generation" / "POD-01" / "meta.json").exists()


def test_a_path_is_not_a_container_name(tmp_path):
    root = make(tmp_path)
    assert run(root, "../etc", "40-asset-generation").returncode != 0
