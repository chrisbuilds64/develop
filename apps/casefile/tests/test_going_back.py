"""Going back, and resuming where the case stood (ADR-035, REQ-001 T-14 to T-19).

The story of the first PressRoom piece: the text is approved, the images are made and approved, the piece waits for its
date — and the author wants to change the text. It goes back to the review; the text is approved again; the image's
approval still stands because nobody touched the images; the piece is back at its date in one step."""

import json
import shutil
from pathlib import Path

from casefile.config import DomainConfig
from casefile.domain import back
from casefile.domain import cases as reading
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

CONFIGS = Path(__file__).resolve().parents[1] / "config"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
CID = "FN-080-a-piece"
n = iter(range(1000))


def world(tmp_path):
    root = tmp_path / "flow"
    for s in ("30-review-human", "40-asset-generation", "50-ready-to-publish", "55-scheduled", "60-published"):
        (root / s).mkdir(parents=True)
    d = root / "30-review-human" / CID
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "FN", "number": "080", "title": "A piece"}))
    (d / "substack.md").write_text("# Draft\n")
    (d / "visual-brief.md").write_text("# Brief\n")
    cfg = tmp_path / "config"
    shutil.copytree(CONFIGS / "pressroom", cfg)
    return root, FsStore(root), DomainConfig.load(cfg, root)


def do(store, config, action, by="chris", **payload):
    return stepping.step(store, config, CID, StepRequest(action=action, step_id=f"s-{next(n)}", payload=payload), by)


def case(store, config):
    return reading.load(store, config, CID)


def at_the_date(tmp_path):
    """Text approved, images made and approved: the piece waits for its date."""
    root, store, config = world(tmp_path)
    assert do(store, config, "approve_to_visual").ok
    (root / "40-asset-generation" / CID / "header-16x9.png").write_bytes(PNG)
    r = do(store, config, "approve_visual")
    assert r.ok and r.to == "50-ready-to-publish", r.reason
    return root, store, config


def test_a_passed_gate_records_what_it_covered(tmp_path):
    root, store, config = at_the_date(tmp_path)
    gates = case(store, config).meta["gates"]
    assert gates["30-review-human"]["covered"]["substack.md"]["file"] == "substack.md"
    assert gates["30-review-human"]["covered"]["substack.md"]["print"].startswith("sha256:")
    assert list(gates["40-asset-generation"]["covered"]) == ["header-16x9.png"] and gates["40-asset-generation"]["by"] == "chris"


def test_a_person_takes_the_case_back_to_a_stage_it_stood_in_with_a_reason(tmp_path):
    root, store, config = at_the_date(tmp_path)
    assert back.back_targets(config, case(store, config)) == ["30-review-human", "40-asset-generation"]
    assert not do(store, config, "go_back", to="30-review-human").ok                       # a reason, always
    assert not do(store, config, "go_back", to="55-scheduled", note="x").ok                # never forward, never where it has not been
    assert not do(store, config, "go_back", by="axel", to="30-review-human", note="x").ok  # never a helper
    r = do(store, config, "go_back", to="30-review-human", note="One more paragraph on the phone case")
    assert r.ok and r.to == "30-review-human", r.reason
    c = case(store, config)
    assert c.stage == "30-review-human" and c.entries[-1].from_ == "50-ready-to-publish" and "paragraph" in c.entries[-1].text
    assert back.mark(config, c) == "50-ready-to-publish"                                   # it knows how far it had come


def test_unchanged_work_keeps_its_approval_and_the_case_resumes_where_it_stood(tmp_path):
    root, store, config = at_the_date(tmp_path)
    do(store, config, "go_back", to="30-review-human", note="check a line")
    assert back.resume_target(store, config, case(store, config)) == "50-ready-to-publish"  # nothing changed: both gates hold
    r = do(store, config, "resume")
    assert r.ok and r.to == "50-ready-to-publish", r.reason
    assert case(store, config).stage == "50-ready-to-publish"
    assert not do(store, config, "resume").ok                                               # and never beyond where it stood


def test_changed_text_is_approved_again_and_the_image_gate_still_holds(tmp_path):
    root, store, config = at_the_date(tmp_path)
    do(store, config, "go_back", to="30-review-human", note="one more paragraph")
    (root / "30-review-human" / CID / "substack.v2.md").write_text("# Draft, with one more paragraph\n")
    c = case(store, config)
    assert not back.holds(store, config, c, "30-review-human")                              # a new version: the text gate asks again
    assert back.resume_target(store, config, c) is None and not do(store, config, "resume").ok
    assert do(store, config, "approve_to_visual").ok                                        # approved again, like the first time
    c = case(store, config)
    assert c.stage == "40-asset-generation" and back.holds(store, config, c, "40-asset-generation")
    r = do(store, config, "resume")                                                         # the images are the same: no new approval
    assert r.ok and r.to == "50-ready-to-publish", r.reason
    assert case(store, config).meta["gates"]["30-review-human"]["covered"]["substack.md"]["file"] == "substack.v2.md"


def test_a_new_image_ends_the_image_gates_hold(tmp_path):
    root, store, config = at_the_date(tmp_path)
    do(store, config, "go_back", to="40-asset-generation", note="the phone should lie face down")
    assert back.resume_target(store, config, case(store, config)) == "50-ready-to-publish"
    (root / "40-asset-generation" / CID / "header-16x9.v2.png").write_bytes(PNG + b"1")
    assert back.resume_target(store, config, case(store, config)) is None                   # redone work is approved again
    assert do(store, config, "approve_visual").ok


def test_a_changed_file_under_the_same_name_ends_the_hold_too(tmp_path):
    root, store, config = at_the_date(tmp_path)
    do(store, config, "go_back", to="30-review-human", note="a typo")
    (root / "30-review-human" / CID / "substack.md").write_text("# Draft, one word changed\n")
    assert not back.holds(store, config, case(store, config), "30-review-human")


def test_a_published_piece_does_not_go_back(tmp_path):
    root, store, config = at_the_date(tmp_path)
    assert do(store, config, "schedule", date="2026-11-16").ok
    assert do(store, config, "published", url="https://example.invalid/p").ok
    c = case(store, config)
    assert back.is_final(config, c) and back.back_targets(config, c) == []
    assert not do(store, config, "go_back", to="30-review-human", note="too late").ok


def test_going_back_to_a_gate_with_a_sealed_protocol_starts_its_next_version(tmp_path):
    from casefile.domain import protocol as gate
    root, store, config = world(tmp_path)
    gate.start(store, config, CID, "text", "chris")
    for item in ("facts", "boundaries", "voice"):
        gate.answer(store, config, CID, "text", "chris", item, f"a-{item}", value=True)
    gate.seal(store, config, CID, "text", "chris", "seal-1")
    assert do(store, config, "approve_to_visual").ok
    assert do(store, config, "go_back", to="30-review-human", note="one more paragraph").ok
    c = case(store, config)
    assert "protocol-text.v2.json" in c.files                                               # the questions are asked again
    assert not do(store, config, "approve_to_visual").ok


def test_a_stage_that_deploys_is_never_resumed_into(tmp_path):
    cfg = DomainConfig.load(CONFIGS / "shipyard", tmp_path)
    assert [s.folder for s in cfg.stages if s.deploys] == ["50-release", "70-test", "80-prod"]
    assert [s.folder for s in cfg.stages if s.final] == ["80-prod"]
