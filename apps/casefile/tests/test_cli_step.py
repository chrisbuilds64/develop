"""A helper's run makes its steps through the core (ADR-027): only as the run's agent, never as a person, and the
same request twice changes nothing."""

import json
from pathlib import Path

import pytest

from casefile.cli import step as cli
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config" / "shipyard"
CID = "SW-2026-001-split-the-api"


@pytest.fixture
def root(tmp_path, monkeypatch):
    root = tmp_path / "flow"
    for s in json.loads((CFG / "stages.json").read_text(encoding="utf-8"))["stages"]:
        (root / s["folder"]).mkdir(parents=True)
    case = root / "20-build" / CID
    case.mkdir()
    (case / "meta.json").write_text(json.dumps({"label": "SW", "number": "2026-001", "title": "Split the API", "configVersion": "1"}), encoding="utf-8")
    (case / "review.md").write_text("", encoding="utf-8")
    monkeypatch.setenv("COCKPIT_DATA_DIR", str(root))
    monkeypatch.setenv("PRESSROOM_RUN_ID", "20261109-120000_build_" + CID)
    return root


def stage(root):
    store = FsStore(root)
    return reading.load(store, DomainConfig.load(CFG, root), CID).stage


def test_the_run_files_its_record_and_moves_the_case_as_its_agent(root, monkeypatch, capsys):
    monkeypatch.setenv("PRESSROOM_AGENT", "Axel")
    (root / "20-build" / CID / "pr.md").write_text("https://example.org/pull/9", encoding="utf-8")
    assert cli.main([CID, "deliver", "--config", str(CFG), "--file", "pr.md"]) == 0
    assert cli.main([CID, "open_pr", "--config", str(CFG)]) == 0
    assert stage(root) == "30-checks"
    out = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert out[-1]["ok"] and out[-1]["to"] == "30-checks"
    assert "Axel" in (root / "30-checks" / CID / "review.md").read_text(encoding="utf-8")


def test_a_run_cannot_step_for_a_person(root, monkeypatch):
    monkeypatch.setenv("PRESSROOM_AGENT", "chris")
    assert cli.main([CID, "open_pr", "--config", str(CFG)]) == 2
    assert stage(root) == "20-build"


def test_without_an_agent_nothing_steps(root, monkeypatch):
    monkeypatch.delenv("PRESSROOM_AGENT", raising=False)
    assert cli.main([CID, "open_pr", "--config", str(CFG)]) == 2


def test_a_refused_step_says_why_and_moves_nothing(root, monkeypatch, capsys):
    monkeypatch.setenv("PRESSROOM_AGENT", "Axel")
    assert cli.main([CID, "open_pr", "--config", str(CFG)]) == 1            # no pull request recorded yet
    assert json.loads(capsys.readouterr().out)["reason"]
    assert stage(root) == "20-build"


def test_the_same_request_twice_changes_nothing(root, monkeypatch):
    monkeypatch.setenv("PRESSROOM_AGENT", "Axel")
    (root / "20-build" / CID / "pr.md").write_text("x", encoding="utf-8")
    assert cli.main([CID, "deliver", "--config", str(CFG), "--file", "pr.md"]) == 0
    assert cli.main([CID, "deliver", "--config", str(CFG), "--file", "pr.md"]) == 0
    text = (root / "20-build" / CID / "review.md").read_text(encoding="utf-8")
    assert text.count("pr.md") == 1


def test_a_note_for_the_product_owner_makes_it_their_move(root, monkeypatch):
    monkeypatch.setenv("PRESSROOM_AGENT", "Axel")
    assert cli.main([CID, "note", "--config", str(CFG), "--for", "chris", "--text", "The task names no requirement line."]) == 0
    text = (root / "20-build" / CID / "review.md").read_text(encoding="utf-8")
    assert "Chris" in text and "no requirement line" in text
