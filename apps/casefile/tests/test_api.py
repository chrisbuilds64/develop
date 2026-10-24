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


def test_a_text_file_is_rendered_for_the_viewer_with_raw_html_shown_not_run(api):
    client, root = api
    sign_in(client)
    (root / "30-review-human" / "FN-105-the-review-that-reads-itself" / "substack.v2.md").write_text("# Safe\n\n<script>alert(1)</script> [x](javascript:alert(1))\n\n- a\n- b\n")
    r = client.get("/api/cases/FN-105-the-review-that-reads-itself/read/substack.v2.md")
    assert r.status_code == 200 and r.json()["kind"] == "md"
    h = r.json()["html"]
    assert "<h1>Safe</h1>" in h and "<li>a</li>" in h and "<script>" not in h and "&lt;script&gt;" in h and 'href="javascript:' not in h
    r = client.get("/api/cases/FN-105-the-review-that-reads-itself/read/linkedin-post.txt")
    assert r.status_code == 200 and r.json()["html"].startswith("<pre>")
    assert client.get("/api/cases/POD-110-the-silent-failure/read/thumbnail-16x9.png").status_code == 415


def test_the_rulebook_reads_configuration_and_modules(tmp_path):
    """/api/rules: the stages with their gates, the skills with does/never, the modules from _bausteine/ with versions."""
    from fastapi.testclient import TestClient
    from casefile.api.app import Settings, create_app
    from casefile.demo.worlds import CONFIG, build_egutachten
    root = build_egutachten(tmp_path / "egut")
    client = TestClient(create_app(Settings(root=root, config_dir=CONFIG / "egutachten", secret="t", demo=True, samples_dir=None, replies_dir=None)))
    client.post("/api/session", json={"person": "du"})
    r = client.get("/api/rules")
    assert r.status_code == 200
    body = r.json()
    folders = [s["folder"] for s in body["stages"]]
    assert folders[0] == "10-auftrag" and "70-abgeschlossen" in folders
    review = next(s for s in body["stages"] if s["folder"] == "40-fachpruefung")
    approve = next(a for a in review["actions"] if a["id"] == "approve_report")
    assert approve["run"] == "anschreiben" and "Gutachten" in approve["requires"] and review["turn_word"] == "Prüfung"
    sent = next(s for s in body["stages"] if s["folder"] == "60-versendet")
    assert any(a["skill"] == "vorpruefung" for a in sent["auto"])
    vor = next(s for s in body["skills"] if s["name"] == "vorpruefung")
    assert vor["never"].startswith("Gibt ein Gutachten frei") and "R-02 Fotostandard" in vor["rules"]
    ids = {m["id"]: m for m in body["modules"]}
    assert ids["B-01"]["version"] == 3 and ids["B-01"]["kind"] == "Baustein" and ids["R-02"]["kind"] == "Regel" and "Pflichtansichten" in ids["R-02"]["text"]


def test_a_quote_in_markdown_stays_a_quote_and_tags_stay_text():
    from casefile.api.text import render
    out = render("> **[B-01]** Zitat\n\n<script>x()</script>", "md")
    assert "<blockquote>" in out and "<script>" not in out and "&lt;script&gt;" in out


def test_the_rulebook_lists_the_connectors_with_their_standards(tmp_path):
    from fastapi.testclient import TestClient
    from casefile.api.app import Settings, create_app
    from casefile.demo.worlds import CONFIG, build_egutachten
    root = build_egutachten(tmp_path / "egut")
    client = TestClient(create_app(Settings(root=root, config_dir=CONFIG / "egutachten", secret="t", demo=True, samples_dir=None, replies_dir=None)))
    client.post("/api/session", json={"person": "du"})
    body = client.get("/api/rules").json()
    by = {k["id"]: k for k in body["connectors"]}
    assert "GDV" in by["versicherer"]["standard"] and "BiPRO" in by["vermittler"]["standard"] and "DAT" in by["kalkulation"]["standard"]
    assert {m["id"] for m in body["modules"]} >= {"R-01", "R-07", "B-01"}


def test_signals_are_hints_with_their_files(tmp_path):
    from fastapi.testclient import TestClient
    from casefile.api.app import Settings, create_app
    from casefile.demo.worlds import CONFIG, build_egutachten
    root = build_egutachten(tmp_path / "egut")
    client = TestClient(create_app(Settings(root=root, config_dir=CONFIG / "egutachten", secret="t", demo=True, samples_dir=None, replies_dir=None)))
    client.post("/api/session", json={"person": "du"})
    body = client.get("/api/signals").json()
    assert [s["id"] for s in body] == ["M-002", "M-001"]
    dup = next(s for s in body if s["id"] == "M-001")
    assert dup["kind"] == "Dublette" and len(dup["cases"]) == 2 and dup["cases"][0]["title"] == "Parkrempler Supermarkt" and "keine Feststellung" in dup["text"]


# ------------------------------------------------------------------- identity from outside, writes through another path, any prefix

def test_identity_from_outside_replaces_the_cookie_and_closes_the_picker(tmp_path):
    from fastapi.testclient import TestClient
    from tests.world import build
    root = build(tmp_path / "flow")
    who = {"name": None}
    app = create_app(Settings(root=root, config_dir=root.parent / "config", lang="en", secret="t", identity=lambda request: who["name"], web_dist=None))
    client = TestClient(app)
    me = client.get("/api/me").json()
    assert me["person"] is None and me["open_identity"] is False
    assert client.post("/api/session", json={"person": "chris"}).status_code == 403     # nobody picks a person here
    who["name"] = "chris"
    me = client.get("/api/me").json()
    assert me["person"] == "chris" and me["identity"] == "chris"
    who["name"] = "stranger"
    me = client.get("/api/me").json()
    assert me["person"] is None and me["identity"] == "stranger"                        # the gate says so instead of a picker
    assert client.get("/api/cases").status_code == 401


def test_writes_go_through_the_write_root_and_reads_stay_on_the_root(tmp_path):
    import os
    from casefile.store import FsStore
    from tests.world import build
    root = build(tmp_path / "flow")
    mirror = tmp_path / "mount"
    os.symlink(root, mirror)                                   # the same tree through another path, as a WebDAV mount would be
    store = FsStore(root, write_root=mirror)
    store.write_json("_steps/x.json", {"a": 1})
    assert (root / "_steps" / "x.json").is_file() and store.read_json("_steps/x.json") == {"a": 1}
    case = store.cases(store.stages()[1])[0] if store.cases(store.stages()[1]) else None
    if case:
        frm, to = store.move(case, store.stages()[2])
        assert (root / to / case).is_dir() and not (root / frm / case).exists()


def test_the_surface_is_served_under_any_prefix(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from tests.world import build
    root = build(tmp_path / "flow")
    dist = tmp_path / "dist"; (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><html><head><title>x</title></head><body><script src="/assets/a.js"></script><link rel="manifest" href="/m.json"></body></html>')
    (dist / "assets" / "a.js").write_text("1")
    inner = create_app(Settings(root=root, config_dir=root.parent / "config", lang="en", secret="t", web_dist=dist))
    shell = FastAPI(); shell.mount("/w/one", inner)
    client = TestClient(shell)
    html = client.get("/w/one/case/abc").text
    assert '<meta name="cf-base" content="/w/one" />' in html and 'src="/w/one/assets/a.js"' in html and 'href="/w/one/m.json"' in html
    assert client.get("/w/one/assets/a.js").text == "1"
    plain = TestClient(inner).get("/").text
    assert 'content=""' in plain and 'src="/assets/a.js"' in plain


def test_roles_missing_at_the_root_are_lent_by_the_domain(tmp_path):
    import json
    from casefile.config import DomainConfig
    from tests.world import CONFIG, build
    root = build(tmp_path / "flow")
    people = json.loads((root / "people.json").read_text())
    for p in people["people"]:
        p.pop("roles", None)                                   # the production file: persons, no roles
    (root / "people.json").write_text(json.dumps(people))
    cfg = DomainConfig.load(CONFIG, root)                      # the PressRoom domain knows chris's roles
    chris = cfg.person("chris")
    assert chris is not None and chris.roles                   # lent by config/people.json
    assert cfg.may_act("chris", "role:" + chris.roles[0])
