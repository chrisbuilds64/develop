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
