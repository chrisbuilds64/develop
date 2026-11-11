"""Work that runs outside a case, who holds a case a helper works on, and how the way back is named (SW-2026-014).

REQ-001 T-08: work handed out for a case (a deploy through the server's request service) is recorded in the case by
whoever hands it out and ended by the report that comes back; while it stands, the case shows it like a helper at work,
with the application's words and its start time, and nobody holds the case.
REQ-001 T-09: when a stage's work is a helper's, the case names the helper as its holder, never the only person who
shares the helper's role; a reminder never goes to an agent.
REQ-001 S-19: "Take it back" and "Move back" name the target stage with its station word, not its status sentence.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api import views
from casefile.api.app import Settings, create_app
from casefile.cli import step as cli
from casefile.config import DomainConfig
from casefile.demo.worlds import CONFIG, build_claims
from casefile.domain import cases as reading
from casefile.domain import step as stepping
from casefile.domain.turn import turn as whose
from casefile.models import StepRequest

from .test_shipyard import CFG, CID, Steps, world


def to_release(root, store, config):
    """A change merged: the case stands in the release stage and the release helper has finished there."""
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    go("accept_task", "chris")
    go.deliver(root, "pr.md", "axel", "https://example.org/pull/4")
    go("open_pr", "axel")
    go.deliver(root, "checks.md", "axel")
    go("checks_green", "axel")
    r = go("merge", "chris")
    assert r.ok and r.run, r.reason
    finish(root, r.run)
    return go, r.run


def finish(root: Path, run_id: str, status: str = "done"):
    f = root / "_runs" / f"{run_id}.json"
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": status, "finished": "2026-11-11T12:00:00+01:00"}))


def report(root: Path, case_stage: str, created: str = "2099-01-01T00:00:00+01:00") -> str:
    """The server's deploy report: a queued order for the verify helper, written after the request (requests.report)."""
    rid = f"20990101-000000_shipyard-verify_{CID}"
    (root / "_runs" / f"{rid}.json").write_text(json.dumps({"id": rid, "skill": "shipyard-verify", "container": f"{case_stage}/{CID}",
                                                            "requested_by": "axel", "status": "queued", "created": created}))
    return rid


# ------------------------------------------------------------------------------------------------ T-08 outside work

def test_outside_work_shows_like_a_helper_at_work_with_its_words_and_nobody_holds_the_case(tmp_path):
    root, store, config = world(tmp_path)
    go, _ = to_release(root, store, config)
    before = whose(reading.load(store, config, CID), config, "de")[0]
    assert before.actor != "claude"                                              # the helper is done: before this change, a person's
    r = go("outside", "axel", what="deploy_entw")
    assert r.ok, r.reason
    case = reading.load(store, config, CID)
    main = whose(case, config, "de")[0]
    assert (main.actor, main.action, main.reason) == ("claude", "wait", "Deploy auf ENTW läuft")
    assert main.since and main.since == case.meta["outside"]["since"]
    assert whose(case, config, "en")[0].reason == "Deploy to ENTW running"
    assert stepping.holders(config, case, "chris") == []                          # no "With …", no reminder
    assert views.again(config, case, "chris", "de") is None                      # nothing to send again while it runs
    v = views.view(config, case, "chris", "de", lambda c, n: n, store=store)
    assert v.held_by == [] and v.outside and v.outside.word == "Deploy auf ENTW läuft" and v.outside.by == "Axel"
    assert any(e.title == "Deploy to ENTW running" and e.author == "Axel" for e in case.entries)  # who handed it out, on record (the thread's language)


def test_the_report_that_comes_back_ends_the_outside_work(tmp_path):
    root, store, config = world(tmp_path)
    go, _ = to_release(root, store, config)
    assert go("outside", "axel", what="deploy_entw").ok
    rid = report(root, "50-release")
    case = reading.load(store, config, CID)
    assert whose(case, config, "de")[0].reason != "Deploy auf ENTW läuft"         # the report is a helper at work now
    finish(root, rid)
    case = reading.load(store, config, CID)
    assert whose(case, config, "de")[0].actor != "claude"                         # the report came back: outside work is over
    assert views.view(config, case, "chris", "de", lambda c, n: n, store=store).outside is None


def test_the_helper_ends_outside_work_explicitly_and_only_who_may_hand_work_out_records_it(tmp_path):
    root, store, config = world(tmp_path)
    go, _ = to_release(root, store, config)
    assert not go("outside", "axel").ok                                          # it says what runs outside
    assert not go("outside", "axel", what="../x").ok
    refused = go("outside", "chris", what="deploy_entw")                         # the release is the developer's stage, not his
    assert not refused.ok
    assert go("outside", "axel", what="deploy_entw").ok
    assert not go("outside", "axel", what="deploy_entw").ok                      # one at a time
    assert go("outside_end", "axel").ok
    case = reading.load(store, config, CID)
    assert "outside" not in case.meta and whose(case, config, "de")[0].actor != "claude"
    assert not go("outside_end", "axel").ok                                      # nothing stands


def test_the_release_helper_records_outside_work_through_the_command_line(tmp_path, monkeypatch, capsys):
    root, store, config = world(tmp_path)
    to_release(root, store, config)
    monkeypatch.setenv("COCKPIT_DATA_DIR", str(root))
    monkeypatch.setenv("PRESSROOM_AGENT", "axel")
    monkeypatch.setenv("PRESSROOM_RUN_ID", "20261111-120000_shipyard-release_" + CID)
    assert cli.main([CID, "outside", "--config", str(CFG), "--what", "deploy_entw"]) == 0
    assert reading.load(store, config, CID).meta["outside"]["what"] == "deploy_entw"
    assert cli.main([CID, "outside_end", "--config", str(CFG)]) == 0
    assert "outside" not in reading.load(store, config, CID).meta


def test_every_stage_that_deploys_has_words_for_its_outside_work():
    vocab = json.loads((CFG / "vocabulary.json").read_text(encoding="utf-8"))
    stages = json.loads((CFG / "stages.json").read_text(encoding="utf-8"))["stages"]
    for lang in ("de", "en"):
        assert "{what}" in vocab[lang]["texts"]["outside_running"]
        for s in stages:
            if s.get("deploys"):
                assert vocab[lang]["outside"][f"deploy_{s['deploys']}"]


# ------------------------------------------------------------------------------------------------ T-09 helper holds

def test_a_stage_a_helper_worked_in_names_the_helper_as_holder_and_no_reminder_goes_to_it(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "chris")
    finish(root, r.run)                                                          # the build helper stopped without a pull request
    case = reading.load(store, config, CID)
    assert [p.id for p in stepping.holders(config, case, "chris")] == ["axel"]   # not Akhil, the only person with the role
    assert stepping.holders(config, case, "akhil") == []                         # a developer's own stage is not held from him
    v = views.view(config, case, "chris", "de", lambda c, n: n, store=store)
    assert v.held_by == ["Axel"] and v.held_by_helper and v.again               # send the helper again instead
    no = stepping.step(store, config, CID, StepRequest(action="remind", step_id="rm1"), "chris")
    assert not no.ok and "helper" in no.reason
    assert not any(e.title in ("Erinnerung", "Reminder") for e in reading.load(store, config, CID).entries)


def test_a_stage_no_helper_worked_in_still_names_the_people(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    go("accept_task", "chris")
    for f in (root / "_runs").glob("*.json"):
        f.unlink()                                                               # a change built by hand: no helper ran here
    case = reading.load(store, config, CID)
    assert [p.id for p in stepping.holders(config, case, "chris")] == ["akhil"]
    asked = go("ask", "chris", text="What is the state of the branch?")         # a free question is no stretch of the stage's work
    finish(root, asked.run)
    assert [p.id for p in stepping.holders(config, reading.load(store, config, CID), "chris")] == ["akhil"]


# ------------------------------------------------------------------------------------------------ S-19 the stage's name

def test_take_back_and_move_back_name_the_stage_by_its_station_word(tmp_path):
    root, store, config = world(tmp_path)
    go, _ = to_release(root, store, config)
    case = reading.load(store, config, CID)
    for lang, word in (("de", "Freigabe"), ("en", "Approval")):
        v = views.view(config, case, "chris", lang, lambda c, n: n, store=store)
        assert v.take_back_to == "40-approval" and v.take_back_word == word
    go.deliver(root, "release.md", "axel")
    go("deploy_entw", "axel")
    go("approve_test", "chris")
    go.deliver(root, "test.md", "axel")
    go("approve_prod", "chris")
    go.deliver(root, "prod.md", "axel")
    assert go("close", "axel").ok
    case = reading.load(store, config, CID)
    for lang, word in (("de", "PROD"), ("en", "PROD")):
        v = views.view(config, case, "akhil", lang, lambda c, n: n, store=store)   # the developer's stage: his to reopen
        assert v.reopen_to == "80-prod" and v.reopen_word == word


def test_a_second_application_names_the_stage_and_reminders_to_people_still_work(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    du = TestClient(app)
    du.post("/api/session", json={"person": "du"})
    v = du.get("/api/cases/WG-2026-0425-glasbruch-wintergarten").json()
    assert v["take_back_word"] == "Meldung" and v["held_by"] == ["Gutachter Berger"] and not v["held_by_helper"]
    assert du.post("/api/cases/WG-2026-0425-glasbruch-wintergarten/steps", json={"action": "remind", "step_id": "r1"}).json()["ok"]
    closed = du.get("/api/cases/KFZ-2026-0790-parkrempler").json()
    cfg = DomainConfig.load(CONFIG / "claims-demo", root)
    station = cfg.word("stations", cfg.stage(closed["reopen_to"]).key, "de", "")
    assert closed["reopen_word"] == station and closed["reopen_word"] != cfg.word("stages", closed["reopen_to"], "de", "")
