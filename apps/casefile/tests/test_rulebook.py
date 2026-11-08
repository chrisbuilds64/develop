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


def test_what_the_ai_proposes_waits_and_a_person_accepts_or_rejects_it_with_a_reason(tmp_path):
    from casefile.demo.worlds import build_claims
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    du = TestClient(app)
    assert du.post("/api/session", json={"person": "du"}).status_code == 200
    rules = du.get("/api/rules").json()
    waiting = {m["id"]: m for m in rules["modules"] if not m["in_force"]}
    assert set(waiting) == {"R-10", "R-11", "R-12"} and rules["may_decide"]                     # proposals are listed, nothing of them holds
    assert waiting["R-10"]["draft_text"].startswith("Glasschäden") and waiting["R-10"]["source"].startswith("Aus einem Gespräch")
    assert {a["key"] for a in rules["areas"]} >= {"HR", "WG", "KFZ"} and all(a["color"] for a in rules["areas"])
    ok = du.post("/api/rulebook/R-10/approve").json()                                           # the AI wrote it, so a person may accept it
    assert ok["in_force"]["version"] == 1 and ok["in_force"]["approved_by"] == "Du"
    assert not du.post("/api/rulebook/R-11/reject", json={"reason": ""}).json().get("versions")   # a reason is required
    no = du.post("/api/rulebook/R-11/reject", json={"reason": "Gilt schon über die Hausrichtlinie"}).json()
    assert no["in_force"] is None and no["draft"] is None and no["versions"][-1]["status"] == "verworfen"
    assert no["versions"][-1]["reason"] == "Gilt schon über die Hausrichtlinie"                 # nothing deleted, the reason on record
    after = {m["id"]: m for m in du.get("/api/rules").json()["modules"]}
    assert after["R-10"]["in_force"] and "R-11" not in after                                    # accepted holds; rejected is gone from the list
    again = du.post("/api/rulebook/R-11/draft", json={"text": "Neu formuliert.", "title": "Diebstahl", "kind": "Regel"}).json()
    assert again["draft"]["version"] == 2                                                       # a new draft after a rejection does not overwrite it


def test_a_letter_only_ever_takes_the_original_text_and_a_reader_sees_their_language(tmp_path):
    from casefile.demo.worlds import build_claims
    root = build_claims(tmp_path / "claims")
    store = FsStore(root)
    b01 = rulebook.current(store)["B-01"]
    assert "Sehr geehrte" in b01["body"] and "Dear" not in b01["body"] and b01["body_en"].startswith("Dear")   # compose takes body
    assert "Dear" not in rulebook.in_force_at(store, None)["B-01"]["body"]
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    c = TestClient(app)
    c.post("/api/session", json={"person": "du"})
    c.post("/api/session/lang", json={"lang": "en"})
    m = {x["id"]: x for x in c.get("/api/rules").json()["modules"]}
    assert m["B-01"]["text"].startswith("Dear") and m["B-01"]["title"] == "Greeting and case reference" and m["R-01"]["approved_by"] == "Management"
    c.post("/api/session/lang", json={"lang": "de"})
    assert {x["id"]: x for x in c.get("/api/rules").json()["modules"]}["B-01"]["text"].startswith("Sehr geehrte")


def test_a_change_brought_into_force_after_a_case_started_that_same_day_does_not_reach_it(tmp_path):
    """Review S3: the day alone let a version approved at 14:00 into a case created at 09:00 the same day."""
    root, c = _clients(tmp_path)
    c["du"].post("/api/rulebook/R-05/draft", json={"text": "Neue Fassung."})
    c["innendienst"].post("/api/rulebook/R-05/approve")
    store = FsStore(root)
    v2 = rulebook.current(store)["R-05"]
    since = v2["in_force_since"]
    assert v2["version"] == "2" or int(v2["version"]) == 2
    before = (dt.datetime.fromisoformat(since) - dt.timedelta(hours=1)).isoformat(timespec="seconds")
    after = (dt.datetime.fromisoformat(since) + dt.timedelta(minutes=1)).isoformat(timespec="seconds")
    assert int(rulebook.in_force_at(store, before)["R-05"]["version"]) == 1                  # the case began under v1
    assert int(rulebook.in_force_at(store, after)["R-05"]["version"]) == 2


def test_every_rulebook_entry_point_refuses_an_id_that_is_not_one(tmp_path):
    """Review S5: only the draft checked the id; the others put it into a file pattern."""
    root, c = _clients(tmp_path)
    for path in ("/api/rulebook/R-*/approve", "/api/rulebook/R-*/retire", "/api/rulebook/R-*/reject"):
        r = c["innendienst"].post(path, json={"note": "x", "reason": "x"})
        assert r.status_code in (404, 409, 422) and not list((root / "_bausteine").rglob("*\\**")), path
    assert c["du"].get("/api/rulebook/R-*").status_code == 404


def test_four_eyes_goes_by_the_person_not_by_the_name(tmp_path):
    """Review S6: a namesake could approve a draft as if they were somebody else, and a renamed person their own."""
    root, c = _clients(tmp_path)
    c["du"].post("/api/rulebook/R-05/draft", json={"text": "Neue Fassung."})
    store = FsStore(root)
    from casefile.config import DomainConfig
    config = DomainConfig.load(CONFIG / "egutachten", root)
    me = config.person("du")
    me.name = "Umbenannt"                                                                      # the same person, another name
    try:
        rulebook.approve(store, config, "R-05", "du")
        assert False, "the author approved their own draft"
    except rulebook.RulebookError as exc:
        assert "four eyes" in str(exc)
