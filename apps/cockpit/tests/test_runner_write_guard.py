"""A helper writes in the case only the files its action delivers (REQ-001 A-05). The free question has no Write or Edit
at all; a helper with a delivery gets a write guard in its HOME that refuses everything else in the case and says why.
An order that names no delivery is not guarded (as before)."""

import importlib.util
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

PIPE = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline"
spec = importlib.util.spec_from_file_location("runner_under_test_guard", PIPE / "runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
import write_guard as G  # noqa: E402  (beside the runner, put on the path by it)

CASE = "20-build/SW-2026-009-x"


def tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    data = tmp_path / "flow"
    (data / CASE).mkdir(parents=True)
    (data / "10-task" / "SW-2026-010-y").mkdir(parents=True)
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    return data, home, checkout


def guard_for(tmp_path, produces, write=("{container}",)):
    data, home, checkout = tree(tmp_path)
    run = {"id": "r1", "skill": "s", "container": CASE, "produces": produces}
    rules = {"write": [w if w != "CHECKOUT" else str(checkout) for w in write]}
    log = G.install(home, run, rules, data, sys.executable, PIPE)
    guard = json.loads((home / ".claude" / "write-guard.json").read_text())
    return data, home, checkout, guard, log


def write(guard, path) -> str | None:
    return G.decide(guard, "Write", {"file_path": str(path), "content": "x"})


def test_the_free_question_has_no_write_tools(tmp_path):
    args = Namespace(claude="claude", add_dir=[])
    ask = runner.command_for({"id": "r", "skill": "ask", "container": CASE, "produces": []},
                             {"tools": ["Read", "Glob", "Grep"]}, args, tmp_path / "flow")
    i = ask.index("--disallowedTools")
    assert set(ask[i + 1].split(",")) >= {"Write", "Edit", "NotebookEdit"}
    task = runner.command_for({"id": "r", "skill": "shipyard-task", "container": CASE, "produces": ["task.md"]},
                              {"tools": ["Read", "Write"]}, args, tmp_path / "flow")
    assert "--disallowedTools" not in task


def test_an_ask_that_tries_to_write_is_refused_with_a_reason(tmp_path):
    data, _, _, guard, _ = guard_for(tmp_path, [])
    why = write(guard, data / CASE / "stages.html")
    assert why and "stages.html" in why and "delivers no file" in why
    assert write(guard, data / CASE / "review.md")              # the runner writes the answer into the thread, not the helper


def test_the_task_writer_writes_the_task_and_the_thread_and_nothing_else(tmp_path):
    data, _, _, guard, _ = guard_for(tmp_path, ["task.md"])
    for ok in ("task.md", "task.v2.md", "review.md"):
        assert write(guard, data / CASE / ok) is None, ok
    for bad in ("index.html", "meta.json", "pr.md", "sub/task.md"):
        why = write(guard, data / CASE / bad)
        assert why and bad.split("/")[-1] in why, bad
    assert write(guard, data / "10-task" / "SW-2026-010-y" / "task.md")   # another case is not this helper's
    assert G.decide(guard, "Edit", {"file_path": str(data / CASE / "meta.json")})
    assert G.decide(guard, "Read", {"file_path": str(data / CASE / "meta.json")}) is None


def test_the_builder_still_writes_in_its_checkout(tmp_path):
    data, _, checkout, guard, _ = guard_for(tmp_path, ["pr.md"], write=("{container}", "CHECKOUT"))
    assert write(guard, checkout / "apps" / "x.py") is None
    assert write(guard, data / CASE / "pr.md") is None
    assert write(guard, data / CASE / "notes.md")


def test_the_hook_refuses_logs_and_the_runner_reads_it(tmp_path):
    data, home, _, _, log = guard_for(tmp_path, ["task.md"])
    settings = json.loads((home / ".claude" / "settings.json").read_text())
    hook = settings["hooks"]["PreToolUse"][0]
    assert "Write" in hook["matcher"] and "Edit" in hook["matcher"]
    call = {"tool_name": "Write", "tool_input": {"file_path": str(data / CASE / "page.html"), "content": "<html>"}}
    r = subprocess.run(hook["hooks"][0]["command"], shell=True, input=json.dumps(call), capture_output=True, text=True)
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert r.returncode == 0 and out["permissionDecision"] == "deny" and "page.html" in out["permissionDecisionReason"]
    call["tool_input"]["file_path"] = str(data / CASE / "task.md")
    r = subprocess.run(hook["hooks"][0]["command"], shell=True, input=json.dumps(call), capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == ""
    refused = runner.refusals(log)
    assert len(refused) == 1 and "page.html" in refused[0]["why"]


def test_an_order_without_a_delivery_is_not_guarded(tmp_path):
    data, home, _ = tree(tmp_path)
    assert G.install(home, {"id": "r", "skill": "s", "container": CASE}, {"write": ["{container}"]}, data, sys.executable, PIPE) is None
    assert not (home / ".claude" / "settings.json").exists()
    assert runner.refusals(None) == []
