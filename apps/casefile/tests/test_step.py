"""step(): whole or not at all. Double click, stale precondition, crash after the entry, manual move, recovery."""

import json
from unittest import mock

from casefile.domain import cases, step as stepping
from casefile.domain import entries as thread
from casefile.models import StepRequest
from casefile.store import StoreError


def req(action, step_id, **payload):
    return StepRequest(action=action, step_id=step_id, payload=payload)


def test_approve_moves_the_case_and_writes_one_entry_with_the_step_id(store, config):
    r = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "s1"), "chris")
    assert r.ok and r.from_ == "30-review-human" and r.to == "40-asset-generation" and r.entry == "REV-002"
    assert store.find("FN-105-the-review-that-reads-itself") == "40-asset-generation"
    entries = thread.parse(store.case_text("FN-105-the-review-that-reads-itself", "review.md"))
    e = entries[-1]
    assert e.status == "approved" and e.step == "s1" and e.from_ == "30-review-human" and e.to == "40-asset-generation" and e.author == "Chris"
    j = json.loads(store.read_text("_steps/s1.json"))
    assert j["status"] == "done" and j["entry"] == "REV-002"
    # afterwards it is Akhil's move
    from casefile.domain import turn as whose
    assert whose.turn(cases.load(store, config, "FN-105-the-review-that-reads-itself"), config)[0].actor == "role:visual"


def test_the_same_step_twice_is_a_no_op_with_the_same_outcome(store, config):
    a = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "dbl"), "chris")
    b = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "dbl"), "chris")
    assert a.ok and b.ok and b.replayed and a.entry == b.entry == "REV-002"
    entries = thread.parse(store.case_text("FN-105-the-review-that-reads-itself", "review.md"))
    assert len(entries) == 2                                       # one, not two


def test_a_stale_precondition_is_refused_with_a_reason(store, config):
    store.move("FN-105-the-review-that-reads-itself", "50-ready-to-publish")
    r = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "stale"), "chris")
    assert not r.ok and "not an action while the case stands in 50-ready-to-publish" in r.reason
    assert json.loads(store.read_text("_steps/stale.json"))["status"] == "refused"


def test_missing_deliverable_rights_and_four_eyes_refuse(store, config):
    r = stepping.step(store, config, "FN-108-missing-draft", req("approve_to_visual", "m1"), "chris")
    assert not r.ok and "substack.md" in r.reason
    r = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "m2"), "akhil")
    assert not r.ok and "may not" in r.reason
    r = stepping.step(store, config, "SP-107-written-by-chris", req("approve_to_visual", "m3"), "chris")
    assert not r.ok and "four eyes" in r.reason
    r = stepping.step(store, config, "SP-107-written-by-chris", req("approve_to_visual", "m4"), "sam")
    assert r.ok and store.find("SP-107-written-by-chris") == "40-asset-generation"
    r = stepping.step(store, config, "FN-111-the-boring-win", req("schedule", "m5"), "chris")
    assert not r.ok and "'date' is required" in r.reason
    r = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "bad id!"), "chris")
    assert not r.ok and "step id" in r.reason
    assert not store.exists("_steps/bad id!.json")


def test_a_crash_after_the_entry_is_completed_on_recovery(store, config):
    """The journal says intent, the entry is written, the folder has not moved: recover() moves it, once."""
    with mock.patch.object(store, "move", side_effect=RuntimeError("power cut")):
        try:
            stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "crash"), "chris")
        except RuntimeError:
            pass
    j = json.loads(store.read_text("_steps/crash.json"))
    assert j["status"] == "intent" and j["entry"] == "REV-002"
    assert store.find("FN-105-the-review-that-reads-itself") == "30-review-human"
    done = stepping.recover(store, config)
    assert [r.ok for r in done] == [True]
    assert store.find("FN-105-the-review-that-reads-itself") == "40-asset-generation"
    assert len(thread.parse(store.case_text("FN-105-the-review-that-reads-itself", "review.md"))) == 2
    # the same step id after recovery replays the recorded outcome
    r = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "crash"), "chris")
    assert r.ok and r.replayed and r.to == "40-asset-generation"


def test_a_crash_before_the_entry_is_completed_on_recovery_too(store, config):
    with mock.patch.object(stepping, "_append_entry", side_effect=RuntimeError("power cut")):
        try:
            stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "crash2"), "chris")
        except RuntimeError:
            pass
    assert json.loads(store.read_text("_steps/crash2.json"))["status"] == "intent"
    stepping.recover(store, config)
    entries = thread.parse(store.case_text("FN-105-the-review-that-reads-itself", "review.md"))
    assert entries[-1].step == "crash2" and store.find("FN-105-the-review-that-reads-itself") == "40-asset-generation"


def test_a_folder_moved_by_hand_is_detected_and_recorded_once(store, config):
    noted = stepping.detect(store, config)
    assert noted == ["FN-116-moved-by-hand: 30-review-human → 40-asset-generation"]
    entries = thread.parse(store.case_text("FN-116-moved-by-hand", "review.md"))
    assert entries[-1].to == "40-asset-generation" and entries[-1].from_ == "30-review-human"
    assert stepping.detect(store, config) == []


def test_schedule_and_published_carry_their_payload_into_meta(store, config):
    r = stepping.step(store, config, "FN-111-the-boring-win", req("schedule", "d1", date="2026-10-29"), "chris")
    assert r.ok and store.find("FN-111-the-boring-win") == "55-scheduled"
    assert store.case_json("FN-111-the-boring-win", "meta.json")["publishDate"] == "2026-10-29"
    r = stepping.step(store, config, "FN-111-the-boring-win", req("published", "d2", url="https://example.invalid/p"), "chris")
    assert r.ok and store.find("FN-111-the-boring-win") == "60-published"
    assert store.case_json("FN-111-the-boring-win", "meta.json")["publishUrl"].startswith("https://")


def test_work_out_orders_a_run_once(store, config):
    r = stepping.step(store, config, "FN-101-the-quiet-audit", req("work_out", "w1"), "chris")
    assert r.ok and r.run and r.run.endswith("_interpret_FN-101-the-quiet-audit") and r.to is None
    runs = [json.loads(store.read_text(f"_runs/{n}")) for n in store.runs() if "FN-101" in n]
    assert len(runs) == 1 and runs[0]["status"] == "queued" and runs[0]["request_id"] == "w1"
    r2 = stepping.step(store, config, "FN-101-the-quiet-audit", req("work_out", "w1"), "chris")
    assert r2.replayed and r2.run == r.run
    # now it is Claude's move
    from casefile.domain import turn as whose
    assert whose.turn(cases.load(store, config, "FN-101-the-quiet-audit"), config)[0].actor == "claude"
    # a person without the role cannot order
    r3 = stepping.step(store, config, "POD-102-the-handoff", req("work_out", "w2"), "akhil")
    assert not r3.ok and "operator" in r3.reason


def test_answer_done_note_and_deliver_write_entries_only(store, config):
    r = stepping.step(store, config, "FN-106-two-models-agreeing", req("answer", "a1", resolves="REV-002", text="B."), "chris")
    assert r.ok and r.entry == "REV-004" and r.to is None
    entries = thread.parse(store.case_text("FN-106-two-models-agreeing", "review.md"))
    assert entries[-1].resolves == "REV-002" and entries[-1].for_ == "Axel" and entries[-1].status == "resolved"
    from casefile.domain import turn as whose
    actors = [t.actor for t in whose.turn(cases.load(store, config, "FN-106-two-models-agreeing"), config)]
    assert "chris" not in actors and "akhil" in actors
    r = stepping.step(store, config, "FN-106-two-models-agreeing", req("done", "a2", resolves="REV-003"), "akhil")
    assert r.ok
    r = stepping.step(store, config, "FN-106-two-models-agreeing", req("note", "a3", text="Think about the title.", **{"for": "akhil"}), "chris")
    assert r.ok and thread.parse(store.case_text("FN-106-two-models-agreeing", "review.md"))[-1].status == "open"
    r = stepping.step(store, config, "SP-109-the-intern", req("deliver", "a4", files=["linkedin-image.png"]), "akhil")
    assert r.ok and thread.parse(store.case_text("SP-109-the-intern", "review.md"))[-1].files == ["linkedin-image.png"]
    r = stepping.step(store, config, "FN-106-two-models-agreeing", req("answer", "a5", resolves="REV-999", text="x"), "chris")
    assert not r.ok and "REV-999" in r.reason


def test_unknown_person_and_unknown_case_are_refused(store, config):
    r = stepping.step(store, config, "FN-105-the-review-that-reads-itself", req("approve_to_visual", "u1"), "nobody")
    assert not r.ok and "people.json" in r.reason
    r = stepping.step(store, config, "FN-999-none", req("approve_to_visual", "u2"), "chris")
    assert not r.ok and "not found" in r.reason
