"""The conversation as a deliverable (ADR-021): no preset marker, a move per respondent, background follow-ups that block
nobody, decisions only by the decider, the canon compiled on approval — and nobody reads another person's answers."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import interview as talk
from casefile.domain import step as stepping
from casefile.domain.turn import turn
from casefile.models import StepRequest
from casefile.store import FsStore

CONFIG = Path(__file__).resolve().parents[1] / "config" / "gatehouse"

PACK = '''
[pack]
name = "Test pack"
version = "0.1"

[[trigger]]
cue = "says usually"
ask = "And when not?"
seeks = "hidden from the surface"
match = ["usually", "normally"]

[[block]]
id = "result"
title = "What comes out"
canon = "What is correct"

  [[block.question]]
  text = "What leaves the house?"
  why = "Without it nothing can be steered."
  yields = "hidden"

  [[block.question]]
  text = "How do you know it is good?"

[[block]]
id = "way"
title = "The way"
canon = "Way and gates"

  [[block.question]]
  text = "Walk me through the last piece."
'''

PEOPLE = {"people": [
    {"id": "mo", "name": "Mo", "kind": "human", "roles": ["moderator", "respondent", "decider"]},
    {"id": "ann", "name": "Ann", "kind": "human", "roles": ["respondent"]},
    {"id": "ki", "name": "KI", "kind": "agent", "roles": []},
]}

CASE = "ERH-2026-01-test"


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "flow"
    for st in ("10-vorbereitung", "20-gespraech", "30-klaerung", "40-kanon", "50-zweiter-durchgang", "60-abgeschlossen"):
        (root / st).mkdir(parents=True)
    (root / "_packs").mkdir()
    (root / "_packs" / "test.toml").write_text(PACK, encoding="utf-8")
    (root / "people.json").write_text(json.dumps(PEOPLE), encoding="utf-8")
    d = root / "20-gespraech" / CASE
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "ERH", "title": "Test", "pack": "test", "respondents": ["mo", "ann"]}), encoding="utf-8")
    return root


def ctx(root):
    return FsStore(root), DomainConfig.load(CONFIG, root)


def test_pack_hides_the_craft(tree):
    pack = talk.load_pack(tree, "test")
    assert [q["id"] for b in pack["blocks"] for q in b["questions"]] == ["result.1", "result.2", "way.1"]
    assert pack["blocks"][0]["questions"][0]["why"].startswith("Without")
    assert "yields" not in json.dumps(pack) and "hidden" not in json.dumps(pack)
    assert pack["triggers"][0]["match"] == ["usually", "normally"]


def test_no_marker_no_answer(tree):
    store, config = ctx(tree)
    with pytest.raises(talk.InterviewError):
        talk.answer(store, config, CASE, "ann", "result.1", "Drawings", "", "s1")
    a = talk.answer(store, config, CASE, "ann", "result.1", "Drawings", "is", "s1")
    assert a["marker"] == "is"
    again = talk.answer(store, config, CASE, "ann", "result.1", "Something else", "is", "s1")      # same step id: nothing changes
    assert again["text"] == "Drawings"
    with pytest.raises(talk.InterviewError):
        talk.answer(store, config, CASE, "ki", "result.1", "x", "is", "s2")                          # not asked
    with pytest.raises(talk.InterviewError):
        talk.answer(store, config, CASE, "ann", "nope.1", "x", "is", "s3")


def test_every_respondent_has_a_move_and_evaluation_waits_for_one_done(tree):
    store, config = ctx(tree)
    turns = turn(reading.load(store, config, CASE), config, "en")
    actors = [t.actor for t in turns if t.action == "interview"]
    assert actors == ["mo", "ann"]
    ev = next(t for t in turns if t.action == "evaluate")
    assert ev.blocked_by == ["answered"]
    talk.answer(store, config, CASE, "ann", "result.1", "Drawings", "is", "s1")
    assert talk.finish(store, config, CASE, "ann", "f1") is True
    turns = turn(reading.load(store, config, CASE), config, "en")
    assert [t.actor for t in turns if t.action == "interview"] == ["mo"]
    assert next(t for t in turns if t.action == "evaluate").blocked_by == []


def test_a_follow_up_runs_beside_the_people(tree):
    store, config = ctx(tree)
    talk.answer(store, config, CASE, "ann", "result.1", "Usually drawings", "is", "s1")
    run = talk.chapter(store, config, CASE, "ann", "result", "gatehouse-nachhaken", "c1")
    assert run and json.loads((tree / "_runs" / f"{run}.json").read_text())["background"] is True
    case = reading.load(store, config, CASE)
    assert case.last_run is None                                   # a background run is nobody's move
    assert any(t.action == "interview" for t in turn(case, config, "en"))
    # the helper's file is collected, not a slot of its own, and read with the case
    (tree / "20-gespraech" / CASE / "nachfragen-ann.json").write_text(json.dumps({"followups": [{"id": "f1", "question": "result.1", "ask": "And when not?"}]}))
    case = reading.load(store, config, CASE)
    assert "nachfragen-ann.json" in case.data and not case.slot("nachfragen-ann.json")
    assert talk.followup(store, config, CASE, "ann", "f1", "When the client calls", "fu1")["text"].startswith("When")
    with pytest.raises(talk.InterviewError):
        talk.followup(store, config, CASE, "mo", "f1", "not mine", "fu2")


def test_decisions_and_the_compiled_canon(tree):
    store, config = ctx(tree)
    talk.answer(store, config, CASE, "ann", "result.1", "Drawings", "is", "s1")
    talk.finish(store, config, CASE, "ann", "f1")
    r = stepping.step(store, config, CASE, StepRequest(action="evaluate", step_id="ev1"), "mo")
    assert r.ok and r.to == "30-klaerung" and r.run
    d = tree / "30-klaerung" / CASE
    (d / "kanon-entwurf.json").write_text(json.dumps({"lines": [
        {"id": "K-01", "block": "result", "text": "A drawing leaves the house only checked.", "marker": "should", "sources": [{"person": "ann", "question": "result.1", "quote": "Drawings"}]},
        {"id": "K-02", "block": "way", "text": "Nobody checks.", "marker": "is", "sources": []}]}))
    run_file = tree / "_runs" / f"{r.run}.json"
    run_file.write_text(json.dumps({**json.loads(run_file.read_text()), "status": "done"}))
    blocked = stepping.step(store, config, CASE, StepRequest(action="approve_canon", step_id="ap0"), "mo")
    assert not blocked.ok and "still missing" in blocked.reason
    with pytest.raises(talk.InterviewError):
        talk.decide(store, config, CASE, "ann", "K-01", "accept", "", "d0", "kanon-entwurf.json", "entscheide.json")
    talk.decide(store, config, CASE, "mo", "K-01", "edit", "A drawing leaves only when checked by a second person.", "d1", "kanon-entwurf.json", "entscheide.json")
    talk.decide(store, config, CASE, "mo", "K-02", "reject", "", "d2", "kanon-entwurf.json", "entscheide.json")
    ok = stepping.step(store, config, CASE, StepRequest(action="approve_canon", step_id="ap1"), "mo")
    assert ok.ok and ok.to == "40-kanon"
    canon = (tree / "40-kanon" / CASE / "canon.md").read_text()
    assert "second person" in canon and "Nobody checks" not in canon and "„Drawings“ — Ann" in canon
    assert "Basis und Marke stehen darüber" in canon                    # an area canon says it is one part, not the whole


def test_the_canon_map_shows_the_layers_above_and_the_areas_beside(tree):
    store, _ = ctx(tree)
    m = talk.canon_map(store, CASE)
    assert m["basis"]["present"] is False and m["marke"]["present"] is False       # nothing above yet: both stay open
    assert [(a["case"], a["current"], a["version"]) for a in m["areas"]] == [(CASE, True, 0)]
    (tree / "_kanon").mkdir()
    (tree / "_kanon" / "basis.md").write_text("# Foundation\n\n## 1. One\n\nx\n\n## 2. Two\n\ny\n")
    m = talk.canon_map(store, CASE)
    assert m["basis"] == {"present": True, "title": "Foundation", "rules": 2} and m["marke"]["present"] is False


def test_api_shows_only_my_answers_and_starts_a_case(tree):
    app = create_app(Settings(root=tree, config_dir=CONFIG, secret="x", recover_on_start=False))
    client = TestClient(app)
    client.post("/api/session", json={"person": "ann"})
    assert client.post(f"/api/cases/{CASE}/interview/answer", json={"question": "result.1", "text": "Drawings", "marker": "", "step_id": "a0"}).status_code == 409
    assert client.post(f"/api/cases/{CASE}/interview/answer", json={"question": "result.1", "text": "Drawings", "marker": "is", "step_id": "a1"}).json()["ok"]
    client.post("/api/session", json={"person": "mo"})
    v = client.get(f"/api/cases/{CASE}/interview").json()
    assert v["answers"] == {} and v["can_answer"] is True
    assert {r["id"]: r["answered"] for r in v["respondents"]} == {"mo": 0, "ann": 1}
    made = client.post("/api/cases", json={"title": "Angebote für Bäder", "step_id": "new1"}).json()
    assert made["id"] == f"ERH-{made['id'].split('-')[1]}-02-angebote-fuer-baeder" and made["stage"] == "10-vorbereitung"
    assert client.post("/api/cases", json={"title": "Angebote für Bäder", "step_id": "new1"}).json()["id"] == made["id"]
    meta = json.loads((tree / "10-vorbereitung" / made["id"] / "meta.json").read_text())
    assert meta["pack"] == "core-de"
    client.post("/api/session", json={"person": "ann"})
    assert client.post("/api/cases", json={"title": "x", "step_id": "new2"}).status_code == 409
