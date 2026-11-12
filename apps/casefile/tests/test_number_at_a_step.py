"""A step gives a waiting case its number (REQ-001 C-11): the idea that stood as FN-xxx-… is FN-081-… from the step that
starts the work, in one move with the stage change — and the helper's own moves are steps like anybody's. Nothing here
is PressRoom's alone: the action says `number`, the application's own rule says which name still waits."""

import json
import shutil
from pathlib import Path

from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import opening
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

PRESSROOM = Path(__file__).resolve().parents[1] / "config" / "pressroom"
STAGES = ("10-ideas", "15-interpretation", "20-produce", "30-review-human", "60-published")


def world(tmp_path):
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    (root / "60-published" / "FN-079-the-one-before").mkdir()
    (root / "60-published" / "FN-SIM-03-a-series-piece").mkdir()
    cfg = tmp_path / "config"
    shutil.copytree(PRESSROOM, cfg)
    return root, FsStore(root), DomainConfig.load(cfg, root)


def idea(store, config, title="Chicken and Egg", step_id="n-1"):
    cid, stage = opening.open_case(store, config, "chris", title, step_id)
    assert stage == "10-ideas" and cid == "FN-xxx-chicken-and-egg"
    return cid


def test_working_an_idea_out_numbers_it_and_moves_it_in_one_step(tmp_path):
    root, store, config = world(tmp_path)
    cid = idea(store, config)
    r = stepping.step(store, config, cid, StepRequest(action="work_out", step_id="w-1"), "chris")
    assert r.ok, r.reason
    assert r.case == "FN-080-chicken-and-egg" and r.to == "15-interpretation"         # the next free number of its label; the series counts apart
    assert not (root / "10-ideas" / cid).exists()
    folder = root / "15-interpretation" / "FN-080-chicken-and-egg"
    assert json.loads((folder / "meta.json").read_text())["number"] == "080"
    run = json.loads(next((root / "_runs").glob("*.json")).read_text())
    assert run["container"] == "15-interpretation/FN-080-chicken-and-egg"             # the helper is ordered where the case stands, under its name
    case = reading.load(store, config, "FN-080-chicken-and-egg")
    assert case.entries[-1].from_ == "10-ideas" and case.entries[-1].to == "15-interpretation"
    assert stepping.detect(store, config) == []                                       # nothing moved by hand


def test_the_same_step_twice_is_the_same_numbered_case(tmp_path):
    root, store, config = world(tmp_path)
    cid = idea(store, config)
    first = stepping.step(store, config, cid, StepRequest(action="work_out", step_id="w-1"), "chris")
    again = stepping.step(store, config, cid, StepRequest(action="work_out", step_id="w-1"), "chris")
    assert again.replayed and again.case == first.case == "FN-080-chicken-and-egg"
    assert len(list((root / "_runs").glob("*.json"))) == 1


def test_a_step_left_after_the_move_is_completed_under_the_new_name(tmp_path):
    root, store, config = world(tmp_path)
    cid = idea(store, config)
    stepping.step(store, config, cid, StepRequest(action="work_out", step_id="w-1"), "chris")
    j = json.loads((root / "_steps" / "w-1.json").read_text())
    j.update(status="intent", case=cid)                                               # the crash: moved, the journal line not written
    j.pop("finished", None)
    (root / "_steps" / "w-1.json").write_text(json.dumps(j))
    out = stepping.recover(store, config)
    assert [o.ok for o in out] == [True] and out[0].case == "FN-080-chicken-and-egg"


def test_a_case_that_has_its_number_keeps_it(tmp_path):
    root, store, config = world(tmp_path)
    (root / "10-ideas" / "FN-SIM-04-in-a-series").mkdir()
    (root / "10-ideas" / "FN-SIM-04-in-a-series" / "meta.json").write_text(json.dumps({"label": "FN", "number": "SIM-04", "title": "In a series"}))
    r = stepping.step(store, config, "FN-SIM-04-in-a-series", StepRequest(action="work_out", step_id="w-2"), "chris")
    assert r.ok, r.reason
    assert r.case == "FN-SIM-04-in-a-series" and (root / "15-interpretation" / "FN-SIM-04-in-a-series").is_dir()


def test_the_helpers_own_moves_are_steps_and_a_person_cannot_make_them(tmp_path):
    root, store, config = world(tmp_path)
    cid = stepping.step(store, config, idea(store, config), StepRequest(action="work_out", step_id="w-1"), "chris").case
    early = stepping.step(store, config, cid, StepRequest(action="interpreted", step_id="h-0"), "axel")
    assert not early.ok and "missing" in early.reason                                 # the interpretation is not there yet
    (root / "15-interpretation" / cid / "interpretation.md").write_text("# Interpretation\n")
    person = stepping.step(store, config, cid, StepRequest(action="interpreted", step_id="h-p"), "akhil")
    assert not person.ok
    r = stepping.step(store, config, cid, StepRequest(action="interpreted", step_id="h-1"), "axel")
    assert r.ok and r.to == "20-produce", r.reason
    (root / "20-produce" / cid / "substack.md").write_text("# Draft\n")
    r = stepping.step(store, config, cid, StepRequest(action="draft_ready", step_id="h-2"), "axel")
    assert r.ok and r.to == "30-review-human", r.reason
    assert stepping.detect(store, config) == []


def test_the_text_gate_waits_for_the_questions_the_helper_brought(tmp_path):
    from casefile.domain import protocol as gate
    root, store, config = world(tmp_path)
    d = root / "30-review-human" / "FN-078-a-draft"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "FN", "number": "078", "title": "A draft"}))
    (d / "substack.md").write_text("# Draft\n")
    (root / "40-asset-generation").mkdir()
    title = {"id": "title", "question": {"en": "Which title?"}, "type": "choice", "options": ["A", "B"], "criterion": {"allowed": ["A", "B"]}}
    gate.start(store, config, "FN-078-a-draft", "text", "axel", items=[title])
    doc = gate._read(store, "FN-078-a-draft", "protocol-text.json")
    assert [i["id"] for i in doc["items"]] == ["facts", "boundaries", "voice", "title"]
    r = stepping.step(store, config, "FN-078-a-draft", StepRequest(action="approve_to_visual", step_id="a-1"), "chris")
    assert not r.ok and "missing" in r.reason


def test_a_piece_nobody_raised_a_question_about_passes_the_text_gate(tmp_path):
    """`protocol_on_demand`: the pieces that stood in review before the protocol came, and every replay, go on as they did."""
    root, store, config = world(tmp_path)
    d = root / "30-review-human" / "FN-077-an-older-draft"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "FN", "number": "077", "title": "An older draft"}))
    (d / "substack.md").write_text("# Draft\n")
    (root / "40-asset-generation").mkdir(exist_ok=True)
    r = stepping.step(store, config, "FN-077-an-older-draft", StepRequest(action="approve_to_visual", step_id="a-2"), "chris")
    assert r.ok, r.reason
