"""The API over the sample world: identity, the lists, a case, a step, an upload, an entry, a run, the audit."""

import json

import pytest
from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app

from .world import CONFIG, build

PNG = b"\x89PNG\r\n\x1a\n" + b"1" * 200


@pytest.fixture
def api(tmp_path):
    root = build(tmp_path / "flow")
    app = create_app(Settings(root=root, config_dir=root.parent / "config", lang="en", secret="test"))
    client = TestClient(app)
    return client, root


def sign_in(client, person="chris"):
    r = client.post("/api/session", json={"person": person})
    assert r.status_code == 200, r.text
    return r.json()


def test_identity_is_required_and_a_cookie_carries_it(api):
    client, _ = api
    assert client.get("/api/me/turns").status_code == 401
    me = sign_in(client)
    assert me["person"] == "chris" and "approver" in me["roles"] and me["product"] == "PressRoom"
    assert client.get("/api/me").json()["name"] == "Chris"
    assert client.post("/api/session", json={"person": "nobody"}).status_code == 404
    assert client.post("/api/session", json={"person": "axel"}).status_code == 404       # an agent cannot sign in


def test_my_turns_and_the_groups(api):
    client, _ = api
    sign_in(client)
    turns = client.get("/api/me/turns").json()
    pairs = {(t["case"]["id"], t["turn"]["action"]) for t in turns}
    assert ("FN-105-the-review-that-reads-itself", "approve_to_visual") in pairs
    assert ("FN-106-two-models-agreeing", "answer") in pairs
    assert all(t["case"]["mine"] for t in turns)
    groups = {g["key"]: g for g in client.get("/api/cases").json()}
    assert [c["id"] for c in groups["claude"]["cases"]] and groups["you"]["word"] == "Your move"
    you = {c["id"] for c in groups["you"]["cases"]}
    assert "FN-105-the-review-that-reads-itself" in you and "SP-109-the-intern" not in you
    assert "SP-109-the-intern" in {c["id"] for c in groups["others"]["cases"]}
    only = client.get("/api/cases?group=out").json()
    assert len(only) == 1 and only[0]["key"] == "out" and only[0]["cases"][0]["date"] >= only[0]["cases"][-1]["date"]


def test_a_case_view_carries_stations_slots_thread_and_my_moves(api):
    client, _ = api
    sign_in(client)
    v = client.get("/api/cases/POD-110-the-silent-failure").json()
    assert [s["state"] for s in v["stations"]] == ["done", "done", "done", "current", "todo", "todo"]
    thumb = next(s for s in v["slots"] if s["file"] == "thumbnail-16x9.png")
    assert thumb["present"] and thumb["shape"] == "image-16x9" and thumb["versions"][0]["url"].endswith("/files/thumbnail-16x9.png")
    assert client.get(thumb["versions"][0]["url"]).status_code == 200
    assert v["my_turns"][0]["action"] == "approve_visual" and v["my_turns"][0]["label"] == "Approve the visual"
    assert v["entries"][-1]["files"] == ["thumbnail-16x9.png"]
    assert client.get("/api/cases/FN-999-none").status_code == 404


def test_a_step_moves_the_case_and_the_second_click_replays(api):
    client, root = api
    sign_in(client)
    r = client.post("/api/cases/FN-105-the-review-that-reads-itself/steps", json={"action": "approve_to_visual", "step_id": "api-1", "payload": {}})
    assert r.status_code == 200 and r.json()["to"] == "40-asset-generation"
    r2 = client.post("/api/cases/FN-105-the-review-that-reads-itself/steps", json={"action": "approve_to_visual", "step_id": "api-1", "payload": {}})
    assert r2.status_code == 200 and r2.json()["replayed"]
    r3 = client.post("/api/cases/FN-105-the-review-that-reads-itself/steps", json={"action": "approve_to_visual", "step_id": "api-2", "payload": {}})
    assert r3.status_code == 409 and "not an action" in r3.json()["reason"]
    assert (root / "40-asset-generation" / "FN-105-the-review-that-reads-itself").is_dir()
    v = client.get("/api/cases/FN-105-the-review-that-reads-itself").json()
    assert v["group"] == "others" and v["turn"]["actor"] == "role:visual"


def test_an_upload_fills_a_slot_and_is_a_step(api):
    client, root = api
    sign_in(client, "akhil")
    r = client.post("/api/cases/SP-109-the-intern/assets", data={"slot": "linkedin-image.png", "step_id": "up-1"}, files={"file": ("final.png", PNG, "image/png")})
    assert r.status_code == 200 and r.json()["name"] == "linkedin-image.png" and r.json()["step"]["entry"] == "REV-002"
    r2 = client.post("/api/cases/SP-109-the-intern/assets", data={"slot": "linkedin-image.png", "step_id": "up-1"}, files={"file": ("final.png", PNG, "image/png")})
    assert r2.status_code == 200 and r2.json()["step"]["replayed"]
    assert sorted(p.name for p in (root / "40-asset-generation" / "SP-109-the-intern").iterdir() if p.name.startswith("linkedin-image")) == ["linkedin-image.png"]
    r3 = client.post("/api/cases/SP-109-the-intern/assets", data={"slot": "linkedin-image.png", "step_id": "up-2"}, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r3.status_code == 409
    # now Chris approves the visual
    sign_in(client, "chris")
    v = client.get("/api/cases/SP-109-the-intern").json()
    assert v["my_turns"][0]["action"] == "approve_visual" and v["group"] == "you"


def test_entries_and_runs_through_the_api(api):
    client, root = api
    sign_in(client)
    r = client.post("/api/cases/FN-106-two-models-agreeing/entries", json={"kind": "answer", "step_id": "e-1", "resolves": "REV-002", "text": "B."})
    assert r.status_code == 200 and r.json()["entry"] == "REV-004"
    r = client.post("/api/cases/FN-106-two-models-agreeing/entries", json={"kind": "note", "step_id": "e-2", "text": "Remember the date.", "for": "akhil"})
    assert r.status_code == 200
    r = client.post("/api/cases/FN-106-two-models-agreeing/entries", json={"kind": "shout", "step_id": "e-3", "text": "x"})
    assert r.status_code == 422
    r = client.post("/api/cases/FN-105-the-review-that-reads-itself/runs", json={"skill": "interpret", "note": "Shorter opening.", "request_id": "r-1"})
    assert r.status_code == 200 and r.json()["run"]
    runs = [json.loads(p.read_text()) for p in (root / "_runs").glob("*.json") if "FN-105" in p.name and "request_id" in p.read_text()]
    assert len(runs) == 1 and runs[0]["note"] == "Shorter opening."
    v = client.get("/api/cases/FN-105-the-review-that-reads-itself").json()
    assert v["group"] == "claude" and v["entries"][-1]["for"] == "Axel"


def test_stages_openapi_and_audit(api):
    client, root = api
    sign_in(client)
    st = client.get("/api/stages").json()
    assert [s["folder"] for s in st][:3] == ["00-archive", "05-operational-observations", "10-ideas"]
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/api/me/turns", "/api/cases", "/api/cases/{case_id}", "/api/cases/{case_id}/steps", "/api/cases/{case_id}/assets",
              "/api/cases/{case_id}/entries", "/api/cases/{case_id}/runs", "/api/stages", "/api/config", "/api/session"):
        assert p in paths, p
    lines = [json.loads(l) for l in (root / "_audit" / "api.jsonl").read_text().splitlines()]
    assert lines[-1]["path"] == "/openapi.json" or lines[-1]["path"].startswith("/api/")
    assert any(l["who"] == "chris" and l["path"] == "/api/stages" for l in lines)
