"""A case changes hands where it stands (REQ-001 T-10), and a helper is ordered by anyone in the process (T-11).

Somebody is ill and the process goes on: any person of the application takes the case's move in its stage over, or hands
it to somebody. The stage's move is then that one person's; a gate's own role stays where it was; it ends when the case
leaves the stage. Nothing here is PressRoom's alone."""

import json
import shutil
from pathlib import Path

from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import step as stepping
from casefile.domain.turn import turn as whose
from casefile.models import StepRequest
from casefile.store import FsStore

PRESSROOM = Path(__file__).resolve().parents[1] / "config" / "pressroom"


def world(tmp_path):
    root = tmp_path / "flow"
    for s in ("30-review-human", "40-asset-generation", "50-ready-to-publish"):
        (root / s).mkdir(parents=True)
    d = root / "40-asset-generation" / "FN-080-a-piece"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "FN", "number": "080", "title": "A piece"}))
    (d / "substack.md").write_text("# Draft\n")
    (d / "visual-brief.md").write_text("# Brief\n")
    cfg = tmp_path / "config"
    shutil.copytree(PRESSROOM, cfg)
    return root, FsStore(root), DomainConfig.load(cfg, root)


def main(store, config, cid="FN-080-a-piece"):
    return whose(reading.load(store, config, cid), config)


def test_the_visual_stage_is_akhils_until_somebody_takes_it_over(tmp_path):
    root, store, config = world(tmp_path)
    assert stepping.holders(config, reading.load(store, config, "FN-080-a-piece"), "chris")[0].id == "akhil"
    r = stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-1"), "chris")
    assert r.ok, r.reason
    case = reading.load(store, config, "FN-080-a-piece")
    assert case.meta["held"]["person"] == "chris" and case.meta["held"]["stage"] == "40-asset-generation"
    assert stepping.holders(config, case, "chris") == []                              # it waits for Chris now
    assert case.entries[-1].title == "Taken over" and case.stage == "40-asset-generation"   # recorded, and nothing moved
    again = stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-2"), "chris")
    assert not again.ok and "already" in again.reason
    back = stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-3", payload={"to": "akhil"}), "chris")
    assert back.ok, back.reason                                                      # and it can be handed back


def test_the_one_who_holds_a_stage_by_its_role_is_not_offered_the_case_again(tmp_path):
    root, store, config = world(tmp_path)
    case = reading.load(store, config, "FN-080-a-piece")
    chris, akhil = config.person("chris"), config.person("akhil")
    assert "already" in stepping.take_over_refusal(config, case, chris, akhil)        # Akhil is the visual role, alone
    assert stepping.take_over_refusal(config, case, chris, chris) is None             # Chris can take it: the emergency


def test_a_case_is_handed_to_somebody_and_only_to_a_person(tmp_path):
    root, store, config = world(tmp_path)
    stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-1"), "chris")
    r = stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-2", payload={"to": "akhil"}), "chris")
    assert r.ok, r.reason
    case = reading.load(store, config, "FN-080-a-piece")
    assert case.meta["held"]["person"] == "akhil" and case.meta["held"]["by"] == "chris"
    assert case.entries[-1].for_ == "Akhil" and "Akhil" in case.entries[-1].title
    assert not stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-3", payload={"to": "axel"}), "chris").ok
    assert not stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-4"), "axel").ok


def test_a_take_over_ends_when_the_case_leaves_the_stage(tmp_path):
    root, store, config = world(tmp_path)
    stepping.step(store, config, "FN-080-a-piece", StepRequest(action="take_over", step_id="t-1"), "chris")
    (root / "40-asset-generation" / "FN-080-a-piece" / "header-16x9.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    r = stepping.step(store, config, "FN-080-a-piece", StepRequest(action="approve_visual", step_id="a-1"), "chris")
    assert r.ok and r.to == "50-ready-to-publish", r.reason
    from casefile.domain.turn import stage_actor
    case = reading.load(store, config, "FN-080-a-piece")
    assert stage_actor(config.stage(case.stage), case) == config.stage(case.stage).turn    # the next stage is its own role's again


def test_anyone_in_the_process_orders_the_visual(tmp_path):
    root, store, config = world(tmp_path)
    assert [p.id for p in config.persons_for("anyone")] == ["chris", "akhil"]             # every person, never a helper
    r = stepping.step(store, config, "FN-080-a-piece", StepRequest(action="make_visual", step_id="v-1"), "chris")
    assert r.ok and r.run and "_asset_" in r.run, r.reason                                # Chris is not the visual role, and orders it
    run = json.loads(next((root / "_runs").glob("*.json")).read_text())
    assert run["skill"] == "asset" and run["container"] == "40-asset-generation/FN-080-a-piece"


def test_a_question_is_settled_when_its_addressee_moves_the_case_on(tmp_path):
    """REQ-001 T-12: 'Draft ready for your review' is not Chris's move any more once Chris approved the text."""
    from casefile.domain import entries as thread
    root, store, config = world(tmp_path)
    d = root / "30-review-human" / "FN-081-next"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "FN", "number": "081", "title": "Next"}))
    (d / "substack.md").write_text("# Draft\n")
    r = stepping.step(store, config, "FN-081-next", StepRequest(action="note", step_id="q-1", payload={"text": "Which title?", "title": "Draft ready", "for": "chris"}), "akhil")
    assert r.ok, r.reason
    assert [e.title for e in thread.open_for(reading.load(store, config, "FN-081-next").entries, "Chris")] == ["Draft ready"]
    r = stepping.step(store, config, "FN-081-next", StepRequest(action="approve_to_visual", step_id="a-1"), "chris")
    assert r.ok, r.reason
    case = reading.load(store, config, "FN-081-next")
    assert thread.open_for(case.entries, "Chris") == []
    assert [t.actor for t in whose(case, config) if t.action == "answer"] == []
