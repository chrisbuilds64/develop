"""The demo: both worlds build, the invoice triggers the reconciliation, the replay plays it, the approval needs an amount, the sample lands."""

from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.demo.replay import play
from casefile.demo.worlds import CONFIG, build_claims, build_pressroom
from casefile.domain import cases, step as stepping
from casefile.domain import turn as whose
from casefile.models import StepRequest
from casefile.store import FsStore

HERE = Path(__file__).resolve().parents[1] / "casefile" / "demo"


def test_both_worlds_build_and_every_case_is_fictional(tmp_path):
    for name, build in (("claims", build_claims), ("pressroom", build_pressroom)):
        root = build(tmp_path / name)
        store = FsStore(root)
        config = DomainConfig.load(CONFIG / ("claims-demo" if name == "claims" else "pressroom"), root)
        all_cases = cases.load_all(store, config)
        assert len(all_cases) >= 8
        assert all(c.meta.get("fictional") is True and c.meta.get("configVersion") for c in all_cases)
        assert (root / "DEMO.md").exists()


def test_the_claims_path_invoice_reconcile_approve(tmp_path):
    root = build_claims(tmp_path / "claims")
    store, config = FsStore(root), DomainConfig.load(CONFIG / "claims-demo", root)
    cid = "HR-2026-0417-wasserschaden-badezimmer"
    # before: your move, but the invoice is missing
    t = whose.turn(cases.load(store, config, cid), config, "de")[0]
    assert t.actor == "role:approver" and t.action == "approve_settlement" and "rechnung.pdf" in t.blocked_by
    # the invoice lands: a deliver step, and the stage's auto rule orders the reconciliation
    r = stepping.step(store, config, cid, StepRequest(action="deliver", step_id="d1", payload={"files": ["rechnung.pdf"]}), "du")
    assert r.ok and r.run and "reconcile" in r.run
    (root / "30-pruefung" / cid / "rechnung.pdf").write_bytes(b"%PDF-1.4 fictional")
    assert whose.turn(cases.load(store, config, cid), config, "de")[0].actor == "claude"
    # the replay plays the prepared answer without waiting
    played = play(store, config, r.run + ".json", HERE / "replies", wait=False)   # falls through to config/claims-demo/replies
    assert played
    case = cases.load(store, config, cid)
    assert case.entries[-1].author == "KI" and "abgleich.md" in case.files and case.last_run.status == "done"
    t = whose.turn(case, config, "de")[0]
    assert t.action == "approve_settlement" and t.blocked_by == [] and t.label == "Freigeben und zur Regulierung"
    # the approval needs an amount, then moves the file
    r = stepping.step(store, config, cid, StepRequest(action="approve_settlement", step_id="a1", payload={}), "du")
    assert not r.ok and "amount" in r.reason
    r = stepping.step(store, config, cid, StepRequest(action="approve_settlement", step_id="a2", payload={"amount": "4.370 €"}), "du")
    assert r.ok and r.to == "40-regulierung"
    assert cases.load(store, config, cid).entries[-1].amount == "4.370 €"


def test_the_sample_invoice_through_the_api(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, samples_dir=HERE / "samples", replies_dir=None))
    client = TestClient(app)
    assert client.post("/api/session", json={"person": "du"}).status_code == 200
    cfg = client.get("/api/config").json()
    assert cfg["theme"]["demo"] is True and "rechnung.pdf" in cfg["theme"]["samples"]
    cid = "HR-2026-0417-wasserschaden-badezimmer"
    r = client.post(f"/api/cases/{cid}/samples", json={"slot": "rechnung.pdf", "step_id": "s1"})
    assert r.status_code == 200 and r.json()["name"] == "rechnung.pdf" and r.json()["step"]["run"]
    r2 = client.post(f"/api/cases/{cid}/samples", json={"slot": "rechnung.pdf", "step_id": "s1"})
    assert r2.status_code == 200 and r2.json()["step"]["replayed"]
    assert client.post(f"/api/cases/{cid}/samples", json={"slot": "nothing.pdf", "step_id": "s2"}).status_code == 404
    v = client.get(f"/api/cases/{cid}").json()
    assert v["group"] == "claude"


def test_the_pressroom_demo_has_the_two_people_story(tmp_path):
    root = build_pressroom(tmp_path / "pressroom")
    store, config = FsStore(root), DomainConfig.load(CONFIG / "pressroom", root)
    all_cases = cases.load_all(store, config)
    chris = {(c.id, t.action) for c, t in whose.turns_for("chris", all_cases, config)}
    akhil = {(c.id, t.action) for c, t in whose.turns_for("akhil", all_cases, config)}
    assert ("POD-ARC-02-the-arc-spoken", "approve_to_visual") in chris
    assert ("FN-043-the-review-that-reads-itself", "answer") in chris
    assert ("FN-042-seven-checks-before-merge", "deliver") in akhil
    r = stepping.step(store, config, "POD-ARC-02-the-arc-spoken", StepRequest(action="approve_to_visual", step_id="p1", payload={}), "chris")
    assert r.ok and r.to == "40-asset-generation"
    assert ("POD-ARC-02-the-arc-spoken", "deliver") in {(c.id, t.action) for c, t in whose.turns_for("akhil", cases.load_all(store, config), config)}


def test_the_e_report_path_draft_precheck_approve_letter(tmp_path):
    """The assessor's draft goes to the AI's pre-check, the reviewer approves, the letter is drafted from approved modules, the back office sends."""
    from casefile.demo.worlds import build_egutachten
    root = build_egutachten(tmp_path / "egut")
    store, config = FsStore(root), DomainConfig.load(CONFIG / "egutachten", root)
    assert (root / "_bausteine" / "B-01-haftungshinweis.md").is_file()
    # your move: approve the report that has draft + pre-check
    cid = "KH-2026-1182-auffahrunfall-a3-kleinwagen"
    t = whose.turn(cases.load(store, config, cid), config, "de")[0]
    assert t.actor == "role:approver" and t.action == "approve_report" and t.blocked_by == []
    r = stepping.step(store, config, cid, StepRequest(action="approve_report", step_id="g1", payload={}), "du")
    assert r.ok and r.to == "50-versand" and r.run and "anschreiben" in r.run
    played = play(store, config, r.run + ".json", HERE / "replies", wait=False)
    assert played
    case = cases.load(store, config, cid)
    assert "anschreiben.md" in case.files and "B-01" in (root / "50-versand" / cid / "anschreiben.md").read_text(encoding="utf-8")
    t = whose.turn(case, config, "de")[0]
    assert t.actor == "role:operator" and t.action == "send" and t.blocked_by == []
    # the assessor's draft: deliver_draft orders the pre-check, the replay moves it to the reviewer
    cid2 = "KK-2026-1190-parkschaden-tiefgarage"
    d = root / "20-besichtigung" / cid2
    for name in ("gutachten.md", "fotos-1.jpg", "kalkulation.pdf"):
        (d / name).write_bytes(b"x")
    r = stepping.step(store, config, cid2, StepRequest(action="deliver_draft", step_id="g2", payload={}), "kaya")
    assert r.ok and r.to == "30-vorpruefung" and r.run and "vorpruefung" in r.run
    assert play(store, config, r.run + ".json", HERE / "replies", wait=False)
    case2 = cases.load(store, config, cid2)
    assert case2.stage == "40-fachpruefung" and "pruefbericht.md" in case2.files
    # a follow-up in 60-versendet: a new report version triggers the pre-check again
    cid3 = "KK-2026-0902-wildunfall-landstrasse"
    (root / "60-versendet" / cid3 / "gutachten.v2.md").write_text("# Nachtrag\n", encoding="utf-8")
    r = stepping.step(store, config, cid3, StepRequest(action="deliver", step_id="g3", payload={"files": ["gutachten.v2.md"]}), "lenz")
    assert r.ok and r.run and "vorpruefung" in r.run
