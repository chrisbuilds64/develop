"""A run sees the skills and agents of its own application only: the content helper has no business in a claim. A tree that
declares nothing keeps everything, as before."""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "runner.py"
spec = importlib.util.spec_from_file_location("runner_under_test", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def base(tmp_path: Path) -> Path:
    b = tmp_path / "ws"
    for s in ("interpret", "reconcile", "ask"):
        (b / ".claude" / "skills" / s).mkdir(parents=True)
    (b / ".claude" / "agents").mkdir()
    for a in ("fact-checker", "code-reviewer"):
        (b / ".claude" / "agents" / f"{a}.md").write_text(a)
    (b / "CLAUDE.md").write_text("x")
    return b


def test_a_run_sees_only_what_its_application_names(tmp_path):
    b = base(tmp_path)
    data = tmp_path / "claims" / "flow"
    data.mkdir(parents=True)
    (data / "run-policy.json").write_text(json.dumps({"skills": {"reconcile": {}}, "agents": []}))
    _, ws = runner._build_home(Namespace(workspace=b), data, "schadenakte", "r1")
    assert sorted(p.name for p in (ws / ".claude" / "skills").iterdir()) == ["ask", "reconcile"]
    assert list((ws / ".claude" / "agents").iterdir()) == []


def test_a_tree_without_a_declaration_keeps_everything(tmp_path):
    b = base(tmp_path)
    data = tmp_path / "press" / "flow"
    data.mkdir(parents=True)
    (data / "run-policy.json").write_text(json.dumps({"skills": {"interpret": {}}}))
    _, ws = runner._build_home(Namespace(workspace=b), data, "pressroom", "r2")
    assert sorted(p.name for p in (ws / ".claude" / "skills").iterdir()) == ["ask", "interpret"]
    assert (ws / ".claude" / "agents").is_symlink()                   # no `agents` named: all of them
