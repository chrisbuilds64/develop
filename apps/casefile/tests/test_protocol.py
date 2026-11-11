"""Gate protocols (ADR-029, REQ-003 GP-01 – GP-13): what a person checked before a gate opened. Played on a Shipyard case
with a workspace template in the tree that includes a catalogue entry (the Definition of Done)."""

import json

import pytest

from casefile.domain import cases as reading
from casefile.domain import protocol as P
from casefile.domain.turn import missing_for
from casefile.models import Action

from .test_shipyard import CID, Steps, world


def setup(tmp_path):
    root, store, config = world(tmp_path)
    (root / "_protocols").mkdir()
    (root / "_protocols" / "dod-software.json").write_text(json.dumps({"id": "dod-software", "items": [
        {"id": "guards", "question": {"en": "Design and architecture guards are clean"}, "type": "yesno", "must": True,
         "role": "developer", "agent": True, "rule": "dod:guards"}]}))
    (root / "_protocols" / "entw.json").write_text(json.dumps({"id": "entw", "title": {"en": "Developer acceptance on ENTW"},
        "include": ["dod-software"], "items": [
            {"id": "installed", "question": {"en": "The tag runs on ENTW"}, "type": "yesno", "must": True, "role": "product_owner"},
            {"id": "errors", "question": {"en": "New errors in the log"}, "type": "number", "criterion": {"max": 0}, "must": True, "role": "product_owner"},
            {"id": "looks", "question": {"en": "How it looks"}, "type": "choice", "options": ["good", "acceptable", "broken"],
             "criterion": {"allowed": ["good", "acceptable"]}, "must": False, "role": "product_owner"},
            {"id": "shot", "question": {"en": "Screenshot of the station line"}, "type": "evidence", "must": True, "role": "product_owner"}]}))
    Steps(store, config).deliver(root, "task.md", "axel", "# Task\n\nno criteria yet\n")
    return root, store, config


def test_a_protocol_is_the_template_with_what_it_includes_and_nothing_is_preset(tmp_path):
    root, store, config = setup(tmp_path)
    name = P.start(store, config, CID, "entw", "chris", items=[{"id": "ac-1", "question": {"en": "Words never overlap at 480 px"},
                                                                "type": "yesno", "role": "product_owner", "origin": "task:AC-1"}])
    doc = json.loads((root / "10-task" / CID / name).read_text())
    assert [i["id"] for i in doc["items"]] == ["guards", "installed", "errors", "looks", "shot", "ac-1"]
    assert {i["id"]: i["origin"] for i in doc["items"]}["guards"] == "catalogue:dod-software"
    assert {i["id"]: i["origin"] for i in doc["items"]}["ac-1"] == "task:AC-1"
    assert doc["answers"] == {} and P.state(doc)["open"] == ["guards", "installed", "errors", "looks", "shot", "ac-1"]   # GP-06


def test_items_are_shaped_before_the_first_verdict_only(tmp_path):
    root, store, config = setup(tmp_path)
    P.start(store, config, CID, "entw", "chris")
    with pytest.raises(P.ProtocolError, match="reason"):
        P.strike_item(store, config, CID, "entw", "chris", "looks", "", "s1")
    P.strike_item(store, config, CID, "entw", "chris", "looks", "no surface change", "s1")
    P.add_item(store, config, CID, "entw", "chris", {"id": "extra", "question": {"en": "x"}, "type": "yesno"}, "s2")
    P.answer(store, config, CID, "entw", "chris", "installed", "s3", value=True)
    with pytest.raises(P.ProtocolError, match="before the first verdict"):
        P.add_item(store, config, CID, "entw", "chris", {"id": "late", "question": {"en": "x"}, "type": "yesno"}, "s4")


def test_each_type_is_judged_by_its_criterion_and_a_fail_or_na_needs_words(tmp_path):
    root, store, config = setup(tmp_path)
    P.start(store, config, CID, "entw", "chris")
    with pytest.raises(P.ProtocolError, match="what was seen"):
        P.answer(store, config, CID, "entw", "chris", "errors", "a1", value=2)
    doc = P.answer(store, config, CID, "entw", "chris", "errors", "a1", value=2, note="two 500s on /api/home")
    assert doc["answers"]["errors"]["verdict"] == "fail"
    with pytest.raises(P.ProtocolError, match="choose one of"):
        P.answer(store, config, CID, "entw", "chris", "looks", "a2", value="fine")
    assert P.answer(store, config, CID, "entw", "chris", "looks", "a2", value="acceptable")["answers"]["looks"]["verdict"] == "pass"
    with pytest.raises(P.ProtocolError, match="evidence"):
        P.answer(store, config, CID, "entw", "chris", "shot", "a3")
    with pytest.raises(P.ProtocolError, match="reason"):
        P.answer(store, config, CID, "entw", "chris", "installed", "a4", na=True)
    again = P.answer(store, config, CID, "entw", "chris", "looks", "a2", value="broken", note="x")    # the same step twice
    assert again["answers"]["looks"]["value"] == "acceptable"


def test_who_answers_is_a_role_and_an_agent_decides_only_what_is_objective(tmp_path):
    root, store, config = setup(tmp_path)
    P.start(store, config, CID, "entw", "chris")
    with pytest.raises(P.ProtocolError, match="role product_owner"):
        P.answer(store, config, CID, "entw", "akhil", "installed", "r1", value=True)
    doc = P.answer(store, config, CID, "entw", "axel", "installed", "r2", value=True, note="v2026.11.16 on ENTW")
    assert "installed" not in doc["answers"] and doc["observations"]["installed"][0]["suggests"] == "pass"   # judgement: observed only
    doc = P.answer(store, config, CID, "entw", "axel", "guards", "r3", value=True, evidence=["guards: clean"])
    assert doc["answers"]["guards"]["verdict"] == "pass"                                                        # objective: for good


def test_the_gate_opens_only_on_a_sealed_protocol_with_every_must_passed_and_a_failed_must_offers_the_way_back(tmp_path):
    root, store, config = setup(tmp_path)
    accept = Action(id="approve", label="approve", requires=["protocol:entw"])
    back = Action(id="send_back", label="back", when=["failed:entw"])
    P.start(store, config, CID, "entw", "chris")
    case = lambda: reading.load(store, config, CID)  # noqa: E731
    assert missing_for(config, case(), accept) == ["protocol:entw"]
    for i, (iid, kw) in enumerate([("guards", {"value": True}), ("installed", {"value": True}), ("errors", {"value": 0}),
                                   ("looks", {"value": "broken", "note": "labels clipped"}), ("shot", {"value": "station-480.png"})]):
        P.answer(store, config, CID, "entw", "chris" if iid != "guards" else "axel", iid, f"g{i}", **kw)
    with pytest.raises(P.ProtocolError, match="sealed by a person"):
        P.seal(store, config, CID, "entw", "axel", "seal-a")
    P.seal(store, config, CID, "entw", "chris", "seal-1")
    assert missing_for(config, case(), accept) == []                       # a failed should-item does not block (GP-13)
    record = (root / "10-task" / CID / "protocol-entw.md").read_text()
    assert "Sealed by chris" in record and "labels clipped" in record and "catalogue:dod-software" in record
    with pytest.raises(P.ProtocolError, match="sealed"):
        P.answer(store, config, CID, "entw", "chris", "errors", "g9", value=1, note="x")
    name = P.start(store, config, CID, "entw", "chris")                    # the case came back: a new version (GP-12)
    assert name == "protocol-entw.v2.json" and missing_for(config, case(), accept) == ["protocol:entw"]
    P.answer(store, config, CID, "entw", "chris", "errors", "v2-1", value=3, note="3 errors after the redeploy")
    assert missing_for(config, case(), back) == []                         # the way back is offered (GP-10)
    assert (root / "10-task" / CID / "protocol-entw.json").exists()        # the earlier version stays


def test_the_protocol_is_worked_through_over_the_api_and_sealing_says_so_in_the_thread(tmp_path):
    from fastapi.testclient import TestClient
    from casefile.api.app import Settings, create_app
    from .test_shipyard import CFG
    root, store, config = setup(tmp_path)
    client = TestClient(create_app(Settings(root=root, config_dir=CFG, secret="t", open_identity=True)))
    assert client.post("/api/session", json={"person": "chris"}).status_code == 200
    assert client.post(f"/api/cases/{CID}/protocols/start", json={"template": "entw"}).json()["file"] == "protocol-entw.json"
    r = client.post(f"/api/cases/{CID}/protocols/entw/answer", json={"item": "errors", "step_id": "x1", "value": 5})
    assert r.status_code == 409 and "what was seen" in r.json()["reason"]
    for i, (iid, body) in enumerate([("installed", {"value": True}), ("errors", {"value": 0}), ("looks", {"value": "good"}), ("shot", {"value": "shot.png"})]):
        assert client.post(f"/api/cases/{CID}/protocols/entw/answer", json={"item": iid, "step_id": f"p{i}", **body}).json()["ok"]
    r = client.post(f"/api/cases/{CID}/protocols/entw/seal", json={"step_id": "seal"})
    assert r.status_code == 409 and "guards" in r.json()["reason"]                      # the agent's item is still open
    P.answer(store, config, CID, "entw", "axel", "guards", "g", value=True, evidence=["guards: clean"])   # an agent answers in its run, not by signing in
    assert client.post(f"/api/cases/{CID}/protocols/entw/seal", json={"step_id": "seal"}).json()["state"]["gate_open"]
    listed = client.get(f"/api/cases/{CID}/protocols").json()["protocols"]
    assert listed[0]["template"] == "entw" and listed[0]["state"]["gate_open"]
    case = reading.load(store, config, CID)
    assert any("Protocol sealed" in e.title for e in case.entries)


TASK = """# Task: station words

The station line overlaps.

## Acceptance criteria

- AC-1 · ENTW · yes/no — Station words never overlap at 480 px.
- AC-2 · TEST · evidence — A screenshot of the case at 780 px.
- AC-3 · both · number ≤ 0 — New errors in the log after the deploy.
- AC-4 · TEST · choice good|acceptable / broken — How it looks on a phone.

## Notes

nothing
"""


def test_acceptance_criteria_are_read_from_the_task_and_a_bad_line_is_named():
    from casefile.domain import criteria
    found, bad = criteria.parse(TASK)
    assert [c["id"] for c in found] == ["AC-1", "AC-2", "AC-3", "AC-4"] and bad == []
    assert found[2]["stages"] == ["ENTW", "TEST"] and found[2]["criterion"] == {"max": 0.0}
    assert found[3]["criterion"] == {"allowed": ["good", "acceptable"]} and found[3]["options"] == ["good", "acceptable", "broken"]
    found, bad = criteria.parse(TASK.replace("number ≤ 0", "number about zero"))
    assert len(found) == 3 and "AC-3" in bad[0]
    assert [i["id"] for i in criteria.items_for(criteria.parse(TASK)[0], "ENTW")] == ["ac-1", "ac-3"]


def test_the_task_is_ready_only_with_readable_criteria_and_the_protocol_takes_those_of_its_stage(tmp_path):
    root, store, config = setup(tmp_path)
    ready = Action(id="accept_task", label="accept", requires=["task.md", "criteria"])
    case = lambda: reading.load(store, config, CID)  # noqa: E731
    assert missing_for(config, case(), ready) == ["criteria"]                  # the task has no criteria yet (GP-15)
    (root / "10-task" / CID / "task.md").write_text(TASK)
    assert missing_for(config, case(), ready) == []
    tpl = json.loads((root / "_protocols" / "entw.json").read_text())
    tpl["criteria"] = {"stage": "ENTW"}
    (root / "_protocols" / "entw.json").write_text(json.dumps(tpl))
    name = P.start(store, config, CID, "entw", "chris")
    items = json.loads((root / "10-task" / CID / name).read_text())["items"]
    assert [(i["id"], i["origin"]) for i in items if i["origin"].startswith("task:")] == [("ac-1", "task:AC-1"), ("ac-3", "task:AC-3")]   # GP-16


def test_a_helper_answers_objective_items_from_its_run_and_only_observes_the_rest(tmp_path, monkeypatch, capsys):
    from casefile.cli import protocol as cli
    from .test_shipyard import CFG
    root, store, config = setup(tmp_path)
    monkeypatch.setenv("COCKPIT_DATA_DIR", str(root))
    monkeypatch.setenv("PRESSROOM_AGENT", "Axel")
    monkeypatch.setenv("PRESSROOM_RUN_ID", "20261111-010000_shipyard-verify_x")
    assert cli.main([CID, "entw", "start", "--config", str(CFG)]) == 0
    assert cli.main([CID, "entw", "answer", "--config", str(CFG), "--item", "guards", "--yes", "--evidence", "design guard: clean"]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["decided"]
    assert cli.main([CID, "entw", "answer", "--config", str(CFG), "--item", "errors", "--value", "3", "--note", "3 errors since the deploy"]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["observed"]      # a judgement item: observed only
    monkeypatch.setenv("PRESSROOM_AGENT", "Chris")
    assert cli.main([CID, "entw", "answer", "--config", str(CFG), "--item", "installed", "--yes"]) == 2   # a person answers in the surface


def test_the_helpers_that_answer_objective_items_may_call_the_protocol_cli():
    """shipyard-checks and shipyard-verify answer the objective items of a protocol; the runner must let them call it."""
    import json
    from pathlib import Path
    policy = json.loads((Path(__file__).resolve().parents[1] / "config" / "shipyard" / "run-policy.json").read_text())
    skills = policy.get("skills", policy)
    for name in ("shipyard-checks", "shipyard-verify"):
        assert "Bash(python -m casefile.cli.protocol:*)" in skills[name]["tools"], name
    assert "Bash(python -m casefile.cli.step:*)" in skills["shipyard-task"]["tools"]
