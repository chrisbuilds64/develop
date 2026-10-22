"""The public demo: a sandbox per visitor, start over, switch worlds, sweep, cap, rate limit."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from casefile.api.app import Settings, World, create_app
from casefile.demo.worlds import CONFIG, build_claims, build_pressroom

HERE = Path(__file__).resolve().parents[1] / "casefile" / "demo"


@pytest.fixture
def demo(tmp_path):
    build_claims(tmp_path / "w" / "claims")
    build_pressroom(tmp_path / "w" / "pressroom")
    settings = Settings(secret="t", demo=True, samples_dir=HERE / "samples", replies_dir=None, sessions_dir=tmp_path / "sessions", session_cap=3,
                        worlds={"claims": World(config_dir=CONFIG / "claims-demo", template=tmp_path / "w" / "claims", person="du", lang="de"),
                                "pressroom": World(config_dir=CONFIG / "pressroom", template=tmp_path / "w" / "pressroom", person="chris", lang="en")})
    app = create_app(settings)
    return app, tmp_path / "sessions"


def test_every_visitor_gets_a_sandbox_and_sees_only_their_own_moves(demo):
    app, sessions = demo
    a, b = TestClient(app), TestClient(app)
    me_a = a.get("/api/me").json()
    me_b = b.get("/api/me").json()
    assert me_a["person"] == "du" and me_a["world"] == "claims" and me_a["demo"] and set(me_a["worlds"]) == {"claims", "pressroom"}
    assert a.cookies.get("cf_demo") != b.cookies.get("cf_demo") and len(list(sessions.iterdir())) == 2
    cid = "HR-2026-0417-wasserschaden-badezimmer"
    r = a.post(f"/api/cases/{cid}/samples", json={"slot": "rechnung.pdf", "step_id": "s1"})
    assert r.status_code == 200
    assert a.get(f"/api/cases/{cid}").json()["group"] == "claude"
    assert b.get(f"/api/cases/{cid}").json()["group"] == "you"                  # b's copy is untouched


def test_start_over_and_switch_world(demo):
    app, sessions = demo
    a = TestClient(app)
    first = a.get("/api/me").json()
    sid1 = a.cookies.get("cf_demo")
    r = a.post("/api/demo/session", json={})
    assert r.status_code == 200 and a.cookies.get("cf_demo") != sid1 and r.json()["world"] == "claims"
    r = a.post("/api/demo/session", json={"world": "pressroom"})
    assert r.status_code == 200 and r.json()["world"] == "pressroom" and r.json()["person"] == "chris" and r.json()["lang"] == "en"
    groups = {g["key"]: g for g in a.get("/api/cases").json()}
    assert any(c["id"] == "POD-ARC-02-the-arc-spoken" for c in groups["you"]["cases"])
    # a person switch inside the sandbox: Akhil's view
    assert a.post("/api/session", json={"person": "akhil"}).status_code == 200
    you = {c["id"] for c in {g["key"]: g for g in a.get("/api/cases").json()}["you"]["cases"]}
    assert "FN-042-seven-checks-before-merge" in you and "POD-ARC-02-the-arc-spoken" not in you
    assert a.post("/api/demo/session", json={"world": "nowhere"}).status_code == 404
    assert first["product"] == "Schadenakte"


def test_the_cap_removes_the_oldest_sandboxes(demo):
    app, sessions = demo
    clients = [TestClient(app) for _ in range(5)]
    for c in clients:
        assert c.get("/api/me").status_code == 200
    assert len([p for p in sessions.iterdir() if p.is_dir()]) == 3
    # the first visitor's sandbox is gone; they get a fresh one on the next call
    assert clients[0].get("/api/me").status_code == 200


def test_the_rate_limit_answers_429(tmp_path):
    build_claims(tmp_path / "w" / "claims")
    settings = Settings(secret="t", demo=True, samples_dir=HERE / "samples", replies_dir=None, sessions_dir=tmp_path / "sessions", rate_per_minute=5,
                        worlds={"claims": World(config_dir=CONFIG / "claims-demo", template=tmp_path / "w" / "claims", person="du", lang="de")})
    client = TestClient(create_app(settings))
    codes = [client.get("/api/me").status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[5] == 429


def test_the_single_pipeline_mode_still_works(tmp_path):
    root = build_claims(tmp_path / "claims")
    client = TestClient(create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t")))
    assert client.get("/api/me/turns").status_code == 401
    assert client.post("/api/session", json={"person": "du"}).status_code == 200
    assert client.get("/api/me").json()["world"] is None
    assert client.post("/api/demo/session", json={}).status_code == 404


def test_a_sandbox_links_documents_copies_text_and_the_world_brings_its_own_samples_and_replies(tmp_path):
    """Documents are hard-linked into the sandbox (the core never writes into one), review.md is a real copy; a `_samples/`
    folder at the world's root is what the frames offer, a `_replies/` folder answers an order — for one case first."""
    import json
    from casefile.demo.replay import load_reply
    from casefile.demo.sandbox import copy_world
    build_claims(tmp_path / "w" / "claims")
    world = tmp_path / "w" / "claims"
    (world / "_samples").mkdir()
    (world / "_samples" / "rechnung.pdf").write_bytes(b"%PDF-1.4 own sample")
    (world / "_replies").mkdir()
    (world / "_replies" / "reconcile.HR-2026-0417-wasserschaden-badezimmer.json").write_text(json.dumps({"delay_s": 0, "files": {}, "entry": {"title": "own", "text": "for this case"}, "to": None}))
    (world / "_replies" / "ask.json").write_text(json.dumps({"delay_s": 0, "files": {}, "entry": {"title": "own ask", "text": "for the world"}, "to": None}))
    copy_world(world, tmp_path / "sb")
    photo = tmp_path / "sb" / "30-pruefung" / "HR-2026-0417-wasserschaden-badezimmer" / "fotos-1.jpg"
    review = tmp_path / "sb" / "30-pruefung" / "HR-2026-0417-wasserschaden-badezimmer" / "review.md"
    assert photo.stat().st_nlink == 2 and review.stat().st_nlink == 1
    from casefile.config import DomainConfig
    config = DomainConfig.load(CONFIG / "claims-demo", world)
    r, _ = load_reply(HERE / "replies", "reconcile", config, world, "HR-2026-0417-wasserschaden-badezimmer")
    assert r["entry"]["title"] == "own"
    r, _ = load_reply(HERE / "replies", "reconcile", config, world, "WG-2026-0421-sturmschaden-carport")
    assert r["entry"]["title"] == "Rechnung abgeglichen"      # the domain's reply for every other case
    r, _ = load_reply(HERE / "replies", "ask", config, world, "x")
    assert r["entry"]["title"] == "own ask"
    settings = Settings(secret="t", demo=True, samples_dir=HERE / "samples", replies_dir=None, sessions_dir=tmp_path / "sessions",
                        worlds={"claims": World(config_dir=CONFIG / "claims-demo", template=world, person="du", lang="de")})
    client = TestClient(create_app(settings))
    client.post("/api/demo/session", json={"world": "claims"})
    cfg = client.get("/api/config").json()
    assert cfg["theme"]["samples"] == ["rechnung.pdf"]
    r = client.post("/api/cases/HR-2026-0417-wasserschaden-badezimmer/samples", json={"slot": "rechnung.pdf", "step_id": "s1"})
    assert r.status_code == 200
    body = client.get("/api/cases/HR-2026-0417-wasserschaden-badezimmer/files/rechnung.pdf").content
    assert body == b"%PDF-1.4 own sample"


def test_the_viewer_can_switch_the_language_the_world_speaks(demo):
    """The claims world speaks German by default; a cookie set through /api/session/lang turns every word English — and back."""
    app, _ = demo
    client = TestClient(app)
    client.post("/api/demo/session", json={"world": "claims"})
    assert client.get("/api/me").json()["lang"] == "de"
    groups = {g["key"]: g["word"] for g in client.get("/api/cases").json()}
    assert groups["you"] == "Du bist dran"
    assert client.post("/api/session/lang", json={"lang": "fr"}).status_code == 400
    assert client.post("/api/session/lang", json={"lang": "en"}).status_code == 200
    assert client.get("/api/me").json()["lang"] == "en"
    groups = {g["key"]: g["word"] for g in client.get("/api/cases").json()}
    assert groups["you"] == "Your move"
    assert client.get("/api/config").json()["lang"] == "en"
    client.post("/api/session/lang", json={"lang": "de"})
    assert client.get("/api/me").json()["lang"] == "de"


def test_the_round_trip_between_the_claim_and_the_e_report(tmp_path):
    """One visitor, two sandboxes: the claim orders the assessment (a case appears in the e-report world), the e-report is
    sent (the report lands in the claim that waits for it and the claim moves on); a world switch returns to the same sandbox."""
    import json
    from casefile.demo.worlds import build_egutachten
    build_claims(tmp_path / "w" / "claims")
    build_egutachten(tmp_path / "w" / "egutachten")
    settings = Settings(secret="t", demo=True, samples_dir=HERE / "samples", replies_dir=None, sessions_dir=tmp_path / "sessions",
                        worlds={"claims": World(config_dir=CONFIG / "claims-demo", template=tmp_path / "w" / "claims", person="du", lang="de"),
                                "egutachten": World(config_dir=CONFIG / "egutachten", template=tmp_path / "w" / "egutachten", person="du", lang="de")})
    client = TestClient(create_app(settings))
    # the claim orders its assessment
    me = client.post("/api/demo/session", json={"world": "claims"}).json()
    claims_sid = client.cookies.get("cf_demo")
    r = client.post("/api/cases/KFZ-2026-0815-parkschaden-tiefgarage/steps", json={"action": "order_assessment", "step_id": "o1", "payload": {"date": "2026-10-24"}})
    assert r.status_code == 200 and r.json()["to"] == "20-besichtigung"
    # … and it is there, in the e-report sandbox of the same visitor
    client.post("/api/demo/session", json={"world": "egutachten"})
    orders = {c["id"]: c for g in client.get("/api/cases").json() for c in g["cases"]}
    new = next(c for c in orders.values() if c["id"].startswith("KH-2026-0815"))
    assert new["stage"] == "10-auftrag" and new["external_id"] == "GA-2026-00815"
    view = client.get(f"/api/cases/{new['id']}").json()
    assert any(s["file"] == "auftrag.md" and s["present"] for s in view["slots"]) and any(s["file"] == "fotos-1.jpg" and s["present"] for s in view["slots"])
    # the e-report that waits for approval goes out and lands in its claim
    client.post("/api/cases/KH-2026-1182-auffahrunfall-a3-kleinwagen/steps", json={"action": "approve_report", "step_id": "a1", "payload": {}})
    sid = client.cookies.get("cf_demo").rsplit(".", 1)[0]
    (tmp_path / "sessions" / sid / "flow" / "50-versand" / "KH-2026-1182-auffahrunfall-a3-kleinwagen" / "anschreiben.md").write_text("# Anschreiben\n", encoding="utf-8")
    r = client.post("/api/cases/KH-2026-1182-auffahrunfall-a3-kleinwagen/steps", json={"action": "send", "step_id": "s1", "payload": {}})
    assert r.status_code == 200 and r.json()["to"] == "60-versendet"
    # back in the claims sandbox (the same one), the claim has the report and moved on to the reconciliation
    client.post("/api/demo/session", json={"world": "claims"})
    assert client.cookies.get("cf_demo") == claims_sid
    claim = client.get("/api/cases/KFZ-2026-0811-auffahrunfall-a3").json()
    assert claim["stage"] == "25-abgleich" and any(s["file"] == "gutachten.md" and s["present"] for s in claim["slots"])
    assert any("eGutachten" in (e["title"] + e["text"]) or "gutachten.md" in e.get("files", []) for e in claim["entries"])
    # the claim that was reported stays where the order put it
    assert client.get("/api/cases/KFZ-2026-0815-parkschaden-tiefgarage").json()["stage"] == "20-besichtigung"
    # start over gives a fresh sandbox for the current world only
    client.post("/api/demo/session", json={})
    assert client.cookies.get("cf_demo") != claims_sid
    assert json.loads("{}") == {}
