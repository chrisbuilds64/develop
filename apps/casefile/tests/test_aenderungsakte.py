"""A change through the gates: whoever released TEST cannot release PROD (four_eyes_of), and a refused PROD deploy
answers again once the restore point is set (a run per round)."""

import json
from pathlib import Path

from casefile.config import DomainConfig
from casefile.demo.replay import play
from casefile.domain import step as stepping
from casefile.models import Person, StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config" / "aenderungsakte"
STAGES = ("10-entw", "20-erfasst", "30-analysiert", "40-bereit", "50-test", "60-prod")
CID = "AE-2026-0011-liefertermin"


def world(tmp_path: Path) -> Path:
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    case = root / "10-entw" / CID
    case.mkdir()
    (case / "meta.json").write_text(json.dumps({"label": "AE", "title": "Liefertermin", "configVersion": "1", "fictional": True}), encoding="utf-8")
    (case / "review.md").write_text("", encoding="utf-8")
    rp = root / "_replies"
    rp.mkdir()
    for name, files, to in (("erfassen", {"erfasst.md": "x"}, None), ("analyse", {"analyse.md": "x"}, None), ("vorbereitung", {"paket.md": "x"}, None),
                            ("einspielen-test", {"test.md": "x"}, None), ("einspielen-prod.1", {}, None), ("restore-point", {"restore-point.md": "x"}, None),
                            ("einspielen-prod.2", {"prod.md": "x"}, "60-prod")):
        skill, _, n = name.partition(".")
        (rp / f"{skill}.{CID}{'.' + n if n else ''}.json").write_text(json.dumps(
            {"delay_s": 0, "files": {k: f"inline:{v}" for k, v in files.items()}, "entry": {"title": name, "text": "."}, "to": to}), encoding="utf-8")
    return root


def press(store, config, action, by, n):
    r = stepping.step(store, config, CID, StepRequest(action=action, step_id=f"s{n}"), by)
    if r.ok and r.run:
        assert play(store, config, r.run + ".json", None, wait=False)
    return r


def test_prod_is_refused_until_the_restore_point_then_moves(tmp_path):
    root = world(tmp_path)
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    for n, a in enumerate(("capture", "analyse", "prepare", "approve_test"), 1):
        assert press(store, config, a, "chris", n).ok
    assert store.find(CID) == "50-test"
    refused = stepping.step(store, config, CID, StepRequest(action="approve_prod", step_id="x1"), "chris")
    assert not refused.ok                                                                  # chris has no PROD role at all
    first = press(store, config, "approve_prod", "jana", 10)
    assert first.ok and store.find(CID) == "50-test"                                       # round 1: the core refused, nothing moved
    assert press(store, config, "set_restore_point", "jana", 11).ok
    assert press(store, config, "approve_prod", "jana", 12).ok
    assert store.find(CID) == "60-prod"


def test_four_eyes_of_refuses_the_releaser_of_test(tmp_path):
    root = world(tmp_path)
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    both = Person(id="sam", name="Sam", kind="human", roles=["developer", "approver_test", "approver_prod"])
    config.people.append(both)
    for n, a in enumerate(("capture", "analyse", "prepare", "approve_test"), 1):
        assert press(store, config, a, "sam", n).ok
    r = stepping.step(store, config, CID, StepRequest(action="approve_prod", step_id="p1"), "sam")
    assert not r.ok and "four eyes" in (r.reason or "")
