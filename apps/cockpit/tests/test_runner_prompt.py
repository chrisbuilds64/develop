"""REQ-001 A-06: every helper is told to ask only in what the screen shows, and to start each choice with its action in
everyday words — a choice in a move's button words becomes that button. One rule for every skill of every application."""

import importlib.util
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "runner.py"
spec = importlib.util.spec_from_file_location("runner_under_test", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_the_writing_rule_forbids_what_the_screen_does_not_show_and_shapes_the_choices():
    p = runner.prompt_for({"container": "20-build/SW-2026-001-x", "skill": "shipyard-build"}, "Axel")
    for must in ("never a file name", "entry number", "internal id", "heading, button or place",
                 "starts with the action in everyday words", "the button's words"):
        assert must in p, must
    assert "ids in backticks" not in p                                       # the old rule invited them
    claim = runner.prompt_for({"container": "10-inbox/SN-1", "skill": "reconcile"}, "Claude")
    assert runner.HELPER_WRITING in p and runner.HELPER_WRITING in claim       # the same rule for every skill
