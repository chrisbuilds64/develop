"""A hand-off is one mechanism for every application: a claim orders an assessment (create), the e-report returns to the
claim that waits for it (deliver) — both described in the configuration, none in code. And an application orders only its own
skills: the content helper has no business in a claim."""

import json
from pathlib import Path

from casefile.config import DomainConfig
from casefile.domain import handoff
from casefile.domain import runs as ordering
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config"


def spec(domain: str, action: str) -> dict:
    d = json.loads((CFG / domain / "stages.json").read_text(encoding="utf-8"))
    return next(a["handover"] for s in d["stages"] for a in s.get("actions", []) if a["id"] == action)


def tree(root: Path, domain: str) -> tuple[FsStore, DomainConfig]:
    for s in json.loads((CFG / domain / "stages.json").read_text(encoding="utf-8"))["stages"]:
        (root / s["folder"]).mkdir(parents=True, exist_ok=True)
    return FsStore(root), DomainConfig.load(CFG / domain, root)


def case(root: Path, stage: str, cid: str, meta: dict, files: dict) -> None:
    d = root / stage / cid
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    for n, c in files.items():
        (d / n).write_bytes(c if isinstance(c, bytes) else c.encode())


def test_a_claim_orders_an_assessment_and_the_report_finds_its_way_back(tmp_path):
    cs, cc = tree(tmp_path / "claims", "claims-demo")
    gs, gc = tree(tmp_path / "gutachten", "egutachten")
    claim = "KFZ-2026-0417-auffahrunfall-a3"
    case(tmp_path / "claims", "10-meldung", claim, {"label": "KFZ", "number": "2026-0417", "title": "Auffahrunfall A3", "external_id": "SN-2026-00417", "fictional": True},
         {"meldung.md": "# Meldung", "fotos-1.jpg": b"\xff\xd8", "notiz.md": "intern"})
    to_g = handoff.Target("egutachten", gs, gc, "Gutachtenakte")
    done = handoff.hand_over(cs, cc, claim, to_g, spec("claims-demo", "order_assessment"), "du", "s1")
    order = gs.find(done["case"]) and tmp_path / "gutachten" / "10-auftrag" / done["case"]
    assert done["case"] == "KH-2026-0417-auffahrunfall-a3" and done["ref"] == "GA-2026-00417"
    assert sorted(p.name for p in order.iterdir() if p.name != "review.md") == ["auftrag.md", "fotos-1.jpg", "meta.json"]   # what the spec names, nothing else
    meta = json.loads((order / "meta.json").read_text())
    assert meta["schaden_nr"] == "SN-2026-00417" and meta["fictional"] and meta["origin"]["case"] == claim
    assert "GA-2026-00417" in (order / "review.md").read_text()
    assert json.loads((tmp_path / "claims" / "10-meldung" / claim / "meta.json").read_text())["gutachten_auftrag"] == "GA-2026-00417"
    assert handoff.hand_over(cs, cc, claim, to_g, spec("claims-demo", "order_assessment"), "du", "s1").get("note") == "already there"

    (tmp_path / "claims" / "10-meldung" / claim).rename(tmp_path / "claims" / "20-besichtigung" / claim)     # the claim waits at the inspection
    (order / "gutachten.md").write_text("v1"); (order / "gutachten.v2.md").write_text("v2")
    to_c = handoff.Target("claims", cs, cc, "Schadenakte")
    back = handoff.hand_over(gs, gc, done["case"], to_c, spec("egutachten", "send"), "kaya", "s2")
    assert back["case"] == claim and cs.find(claim) == "25-abgleich"                                       # the claim took its step
    assert (tmp_path / "claims" / "25-abgleich" / claim / "gutachten.md").read_text() == "v2"                # the newest version travels


def test_a_report_nobody_waits_for_is_refused_out_loud(tmp_path):
    cs, cc = tree(tmp_path / "claims", "claims-demo")
    gs, gc = tree(tmp_path / "gutachten", "egutachten")
    case(tmp_path / "gutachten", "50-versand", "KH-2026-0001-x", {"label": "KH", "title": "x", "external_id": "GA-2026-09999"}, {"gutachten.md": "g"})
    try:
        handoff.hand_over(gs, gc, "KH-2026-0001-x", handoff.Target("claims", cs, cc, "Schadenakte"), spec("egutachten", "send"), "kaya", "s3")
        raise AssertionError("delivered to nobody")
    except handoff.HandoffError as exc:
        assert "waits for GA-2026-09999" in str(exc)


def test_an_application_orders_only_its_own_skills(tmp_path):
    _, cc = tree(tmp_path / "claims", "claims-demo")
    du = cc.person("du")
    assert ordering.may_order(cc, "reconcile", du) is None
    assert "not a skill of this application" in ordering.may_order(cc, "interpret", du)
    assert ordering.may_order(cc, "ask", du) is None                                          # the built-in question stays
