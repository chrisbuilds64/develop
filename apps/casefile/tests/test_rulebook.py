"""The rulebook edited in the app (ADR-026): a change is a draft, a second person brings it into force, a retired
module is a version too, and a case keeps the rulebook it started with, in its areas."""

import datetime as dt

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.demo.worlds import CONFIG, build_egutachten
from casefile.domain import rulebook
from casefile.store import FsStore


def _clients(tmp_path):
    root = build_egutachten(tmp_path / "egut")
    app = create_app(Settings(root=root, config_dir=CONFIG / "egutachten", secret="t", demo=True, replies_dir=None))
    out = {}
    for pid in ("du", "innendienst", "lenz"):
        out[pid] = TestClient(app)
        assert out[pid].post("/api/session", json={"person": pid}).status_code == 200
    return root, out


def test_a_change_is_a_draft_until_a_second_person_brings_it_into_force(tmp_path):
    root, c = _clients(tmp_path)
    du, innen, lenz = c["du"], c["innendienst"], c["lenz"]
    before = du.get("/api/rulebook/R-05").json()
    assert before["in_force"]["version"] == 1 and before["draft"] is None and before["may_edit"]
    assert lenz.post("/api/rulebook/R-05/draft", json={"text": "x"}).status_code == 409          # an assessor does not change the rulebook
    h = du.post("/api/rulebook/R-05/draft", json={"text": "Über 1.200 € gibt eine zweite Person frei.", "note": "Schwelle genannt"}).json()
    assert h["draft"]["version"] == 2 and h["draft"]["status"] == "entwurf" and h["in_force"]["version"] == 1 and not h["may_approve"]
    rules = du.get("/api/rules").json()
    r05 = next(m for m in rules["modules"] if m["id"] == "R-05")
    assert r05["version"] == 1 and r05["draft"] == 2 and rules["may_edit"]                       # the version in force is still the one read
    no = du.post("/api/rulebook/R-05/approve").json()
    assert not no["ok"] and "four eyes" in no["reason"]
    assert innen.get("/api/rulebook/R-05").json()["may_approve"]
    ok = innen.post("/api/rulebook/R-05/approve").json()
    assert ok["in_force"]["version"] == 2 and ok["in_force"]["approved_by"] == "Innendienst" and ok["draft"] is None
    assert [v["version"] for v in ok["versions"]] == [1, 2] and ok["versions"][0]["status"] == "freigegeben"
    text = next((root / "_bausteine").glob("R-05-*.md")).read_text(encoding="utf-8")
    assert "version: 2" in text and "1.200" in text                                              # the file in force, same name as before


def test_retiring_is_a_version_and_a_case_keeps_the_rulebook_it_started_with(tmp_path):
    root, c = _clients(tmp_path)
    du, innen = c["du"], c["innendienst"]
    store = FsStore(root)
    assert not du.post("/api/rulebook/B-18/retire", json={"note": ""}).json().get("in_force")      # a reason is required
    was = du.get("/api/rulebook/B-18").json()["in_force"]["version"]
    r = du.post("/api/rulebook/B-18/retire", json={"note": "Fotos stehen jetzt im Anhang"}).json()
    assert r["in_force"]["status"] == "zurückgezogen" and r["in_force"]["version"] == was + 1 and r["versions"][-2]["status"] == "freigegeben"

    du.post("/api/rulebook/B-05/draft", json={"text": "Neue Fassung.", "areas": ["KH"]})
    innen.post("/api/rulebook/B-05/approve")
    du.post("/api/rulebook/B-19/draft", json={"text": "Ganz neu.", "title": "Neu", "kind": "Baustein"})
    innen.post("/api/rulebook/B-19/approve")

    week_ago = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    old = rulebook.in_force_at(store, week_ago, "KK")
    assert old["B-18"]["status"] == "freigegeben" and old["B-05"]["version"] == "2" and "Neue Fassung" not in old["B-05"]["body"]
    assert "B-19" not in old                                                                     # it did not exist when that case started
    new_kk = rulebook.in_force_at(store, dt.date.today().isoformat(), "KK")
    assert new_kk["B-18"]["status"] == "zurückgezogen" and new_kk["B-05"].get("_skip") and "B-19" in new_kk   # B-05 is for KH only now
    assert not rulebook.in_force_at(store, dt.date.today().isoformat(), "KH")["B-05"].get("_skip")
    assert "R-01" in old and not old["R-01"].get("_skip")                                        # never edited: as it stands
