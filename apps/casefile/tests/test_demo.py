"""The demo: both worlds build, the invoice triggers the reconciliation, the replay plays it, the approval needs an amount, the sample lands."""

import json
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


def test_every_entry_says_whether_a_person_or_the_ai_made_it(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    client = TestClient(app)
    assert client.post("/api/session", json={"person": "du"}).status_code == 200
    actors = {}
    for group in client.get("/api/cases").json():
        for card in group["cases"]:
            for e in client.get(f"/api/cases/{card['id']}").json()["entries"]:
                actors.setdefault(e["actor"], set()).add(e["author"])
    assert "KI" in actors.get("ai", set()), actors          # the agent of people.json
    assert actors.get("person") and not (actors["person"] & actors.get("ai", set()))
    assert "**Actor:**" not in "".join(p.read_text(encoding="utf-8") for p in root.rglob("review.md"))   # derived, never written


def test_a_closed_case_moves_back_to_where_it_left_the_work(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    client = TestClient(app)
    assert client.post("/api/session", json={"person": "du"}).status_code == 200
    cid = "KFZ-2026-0790-parkrempler"
    v = client.get(f"/api/cases/{cid}").json()
    assert v["stage"] == "60-abgeschlossen" and v["reopen_to"] == "40-regulierung" and v["reopen_word"]
    r = client.post(f"/api/cases/{cid}/steps", json={"action": "reopen", "step_id": "back-1", "payload": {"text": "Rechnung fehlte"}}).json()
    assert r["ok"] and r["from"] == "60-abgeschlossen" and r["to"] == "40-regulierung", r
    v = client.get(f"/api/cases/{cid}").json()
    assert v["stage"] == "40-regulierung" and v["reopen_to"] == "" and v["entries"][-1]["text"] == "Rechnung fehlte"
    again = client.post(f"/api/cases/{cid}/steps", json={"action": "reopen", "step_id": "back-1"}).json()
    assert again["replayed"] and again["to"] == "40-regulierung"                          # the same step twice is one step
    no = client.post(f"/api/cases/{cid}/steps", json={"action": "reopen", "step_id": "back-2"}).json()
    assert not no["ok"] and "not closed" in no["reason"]                                    # it is in the work again
    other = "HR-2026-0388-leitungswasser-kueche"
    bad = client.post(f"/api/cases/{other}/steps", json={"action": "reopen", "step_id": "back-3", "payload": {"to": "60-abgeschlossen"}}).json()
    assert not bad["ok"] and "not an open stage" in bad["reason"]
    store, config = FsStore(root), DomainConfig.load(CONFIG / "claims-demo", root)
    ai = stepping.step(store, config, other, StepRequest(action="reopen", step_id="back-4"), by="ki")
    assert not ai.ok and "a person does that" in ai.reason                                  # the AI never reopens


def test_read_and_unread_are_per_person_like_mail(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    du, berger = TestClient(app), TestClient(app)
    assert du.post("/api/session", json={"person": "du"}).status_code == 200
    assert berger.post("/api/session", json={"person": "gutachter"}).status_code == 200

    def unread(client, cid):
        return next(c["unread"] for g in client.get("/api/cases").json() for c in g["cases"] if c["id"] == cid)

    cid = "HR-2026-0417-wasserschaden-badezimmer"
    assert unread(du, cid) and unread(berger, cid)                                        # never opened: new to both
    assert du.post(f"/api/cases/{cid}/seen", json={}).json() == {"case": cid, "unread": False}
    assert not unread(du, cid) and unread(berger, cid)                                    # per person
    assert not du.get(f"/api/cases/{cid}").json()["unread"]
    du.post(f"/api/cases/{cid}/entries", json={"kind": "note", "step_id": "n1", "text": "Fotos angefragt"})
    assert not unread(du, cid)                                                            # my own note is nothing new to me
    berger.post(f"/api/cases/{cid}/entries", json={"kind": "note", "step_id": "n2", "text": "Termin steht"})
    assert unread(du, cid)                                                                # somebody else wrote since
    du.post(f"/api/cases/{cid}/seen", json={})
    assert du.post(f"/api/cases/{cid}/seen", json={"unread": True}).json()["unread"] is True   # mark as unread again
    assert unread(du, cid)
    closed = "KFZ-2026-0790-parkrempler"
    assert not unread(du, closed)                                                         # a closed case has nothing new
    assert du.post("/api/cases/nothing/seen", json={}).status_code == 404
    assert (root / "_seen" / "du.json").is_file() and not any(p.name == "_seen" for p in root.iterdir() if p.name[:2].isdigit())


def test_a_case_somebody_else_holds_can_be_reminded_or_taken_back(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    du, berger = TestClient(app), TestClient(app)
    du.post("/api/session", json={"person": "du"})
    berger.post("/api/session", json={"person": "gutachter"})
    cid = "WG-2026-0425-glasbruch-wintergarten"
    v = du.get(f"/api/cases/{cid}").json()
    assert v["held_by"] == ["Gutachter Berger"] and v["take_back_to"] == "10-meldung" and v["take_back_word"]
    assert berger.get(f"/api/cases/{cid}").json()["held_by"] == []                       # it is his own move
    berger.post(f"/api/cases/{cid}/seen", json={})
    r = du.post(f"/api/cases/{cid}/steps", json={"action": "remind", "step_id": "r1"}).json()
    assert r["ok"] and r["entry"], r
    last = du.get(f"/api/cases/{cid}").json()["entries"][-1]
    assert last["for"] == "Gutachter Berger" and last["status"] == "info" and last["text"]
    turns = berger.get(f"/api/cases/{cid}").json()["turns"]
    assert [t["action"] for t in turns].count("answer") == 0                              # a nudge, not a new task
    assert next(c["unread"] for g in berger.get("/api/cases").json() for c in g["cases"] if c["id"] == cid)   # but new to him
    no = berger.post(f"/api/cases/{cid}/steps", json={"action": "remind", "step_id": "r2"}).json()
    assert not no["ok"] and "nobody else" in no["reason"]
    assert not berger.post(f"/api/cases/{cid}/steps", json={"action": "take_back", "step_id": "t0"}).json()["ok"]
    r = du.post(f"/api/cases/{cid}/steps", json={"action": "take_back", "step_id": "t1"}).json()
    assert r["ok"] and r["from"] == "20-besichtigung" and r["to"] == "10-meldung", r
    v = du.get(f"/api/cases/{cid}").json()
    assert v["held_by"] == [] and v["take_back_to"] == "" and any(t["actor"] == "du" or t["actor"].startswith("role:") for t in v["my_turns"])
    nohist = du.get("/api/cases/KFZ-2026-0811-auffahrunfall-a3").json()
    assert nohist["take_back_to"] == "10-meldung"                                       # no move on record: the stage before


def test_undo_until_the_case_goes_on_then_only_a_correction(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    du, reg = TestClient(app), TestClient(app)
    du.post("/api/session", json={"person": "du"})
    reg.post("/api/session", json={"person": "regulierung"})
    cid = "WG-2026-0402-hagelschaden-reihenhaus"
    ok = du.post(f"/api/cases/{cid}/steps", json={"action": "approve_settlement", "step_id": "a1", "payload": {"amount": "4.200 €"}}).json()
    assert ok["ok"] and ok["to"] == "40-regulierung", ok
    v = du.get(f"/api/cases/{cid}").json()
    assert v["undo_step"] == "a1" and v["undo_word"] and reg.get(f"/api/cases/{cid}").json()["undo_step"] == ""   # only the one who did it
    assert not reg.post(f"/api/cases/{cid}/steps", json={"action": "undo", "step_id": "u0"}).json()["ok"]
    u = du.post(f"/api/cases/{cid}/steps", json={"action": "undo", "step_id": "u1"}).json()
    assert u["ok"] and u["from"] == "40-regulierung" and u["to"] == "30-pruefung", u
    v = du.get(f"/api/cases/{cid}").json()
    decision, undone = v["entries"][-2], v["entries"][-1]
    assert undone["status"] == "undone" and undone["corrects"] == decision["id"] and decision["corrected_by"] == [undone["id"]]
    assert v["stage"] == "30-pruefung" and v["undo_step"] == ""                            # an undo is not undone again
    assert json.loads((root / "_steps" / "a1.json").read_text())["status"] == "undone"   # and no longer counts as done
    assert du.post(f"/api/cases/{cid}/steps", json={"action": "undo", "step_id": "u1"}).json()["replayed"]

    # approve again; this time the settlement desk goes on, so the decision is sealed
    du.post(f"/api/cases/{cid}/steps", json={"action": "approve_settlement", "step_id": "a2", "payload": {"amount": "4.200 €"}})
    reg.post(f"/api/cases/{cid}/entries", json={"kind": "note", "step_id": "n1", "text": "Zahlung vorbereitet"})
    assert du.get(f"/api/cases/{cid}").json()["undo_step"] == ""
    late = du.post(f"/api/cases/{cid}/steps", json={"action": "undo", "step_id": "u2"}).json()
    assert not late["ok"] and "gone on" in late["reason"]
    sealed = next(e for e in du.get(f"/api/cases/{cid}").json()["entries"] if e.get("step") == "a2")
    assert not du.post(f"/api/cases/{cid}/steps", json={"action": "correct", "step_id": "c0", "payload": {"corrects": sealed["id"]}}).json()["ok"]   # a reason is required
    c = du.post(f"/api/cases/{cid}/steps", json={"action": "correct", "step_id": "c1",
                                                 "payload": {"corrects": sealed["id"], "text": "Selbstbehalt nicht abgezogen", "amount": "3.700 €"}}).json()
    assert c["ok"], c
    v = du.get(f"/api/cases/{cid}").json()
    corr = v["entries"][-1]
    assert corr["status"] == "correction" and corr["amount"] == "3.700 €" and corr["corrects"] == sealed["id"] and v["stage"] == "40-regulierung"
    assert next(e for e in v["entries"] if e["id"] == sealed["id"])["amount"] == "4.200 €"   # the original stands
    assert not du.post(f"/api/cases/{cid}/steps", json={"action": "correct", "step_id": "c2", "payload": {"corrects": undone["id"], "text": "x"}}).json()["ok"]
    assert "**Corrects:** " + sealed["id"] in next(root.rglob(f"{cid}/review.md")).read_text(encoding="utf-8")


def test_an_undo_left_half_way_is_completed_on_the_next_start(tmp_path):
    root = build_claims(tmp_path / "claims")
    store, config = FsStore(root), DomainConfig.load(CONFIG / "claims-demo", root)
    cid = "WG-2026-0402-hagelschaden-reihenhaus"
    assert stepping.step(store, config, cid, StepRequest(action="approve_settlement", step_id="a1", payload={"amount": "1 €"}), by="du").ok
    store.write_json("_steps/u9.json", {"step_id": "u9", "case": cid, "action": "undo", "by": "du", "status": "intent", "from": "40-regulierung",
                                        "to": "30-pruefung", "payload": {"step": "a1"}, "created": "2026-11-05T10:00:00+01:00"})
    done = stepping.recover(store, config)
    assert [r.ok for r in done] == [True] and store.find(cid) == "30-pruefung"
    assert store.read_json("_steps/a1.json")["status"] == "undone"


def test_content_follows_the_viewers_language_and_the_original_stays(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    client = TestClient(app)
    client.post("/api/session", json={"person": "du"})
    client.post("/api/session/lang", json={"lang": "en"})
    store, config = FsStore(root), DomainConfig.load(CONFIG / "claims-demo", root)
    cid = "WG-2026-0425-glasbruch-wintergarten"

    # a helper's titles and facts in several languages: the viewer's wins, the original stays on record
    meta = store.case_json(cid, "meta.json")
    store.write_json(f"{store.find(cid)}/{cid}/meta.json", {**meta, "lang": "de", "i18n": {"en": {"title": "Conservatory glass cracked"}}})
    card = next(c for g in client.get("/api/cases").json() for c in g["cases"] if c["id"] == cid)
    v = client.get(f"/api/cases/{cid}").json()
    assert card["title"] == v["title"] == "Conservatory glass cracked" and v["meta"]["lang"] == "de"
    assert store.case_json(cid, "meta.json")["title"] == meta["title"]                  # nothing overwritten

    # every order says the language the helper writes in
    r = client.post(f"/api/cases/{cid}/runs", json={"skill": "ask", "note": "Status?", "request_id": "q1"}).json()
    assert store.read_json(f"_runs/{r['run']}.json")["lang"] == "en"

    # "Show translation": ordered once, written beside the original, then answered at once
    t = client.post(f"/api/cases/{cid}/translate", json={"file": "meldung.md", "request_id": "t1"}).json()
    assert t == {"original": "meldung.md", "lang": "en", "name": "meldung.en.md", "ready": False, "run": t["run"]} and t["run"]
    order = store.read_json(f"_runs/{t['run']}.json")
    assert order["background"] and order["file"] == "meldung.md" and order["out"] == "meldung.en.md"
    entries_before = len(client.get(f"/api/cases/{cid}").json()["entries"])
    assert play(store, config, t["run"] + ".json", HERE / "replies", wait=False)
    v = client.get(f"/api/cases/{cid}").json()
    assert v["translations"] == {"meldung.md": {"en": "meldung.en.md"}} and len(v["entries"]) == entries_before   # no thread noise
    assert "meldung.md" in store.case_text(cid, "meldung.en.md") and store.case_text(cid, "meldung.md").startswith("# Schadenmeldung")
    again = client.post(f"/api/cases/{cid}/translate", json={"file": "meldung.md", "request_id": "t2"}).json()
    assert again["ready"] and again["run"] is None
    assert client.post(f"/api/cases/{cid}/translate", json={"file": "meta.json", "request_id": "t3"}).status_code == 404
    assert client.post(f"/api/cases/{cid}/translate", json={"file": "meldung.md", "lang": "english", "request_id": "t4"}).status_code == 422


def test_the_menu_knows_its_workspaces_and_each_card_who_it_is_from(tmp_path):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, replies_dir=None))
    client = TestClient(app)
    me = client.post("/api/session", json={"person": "du"}).json()
    assert [(p["current"], bool(p["name"])) for p in me["places"]] == [(True, True)]          # one pipeline: this workspace only
    assert me["places"][0]["color"].startswith("#")                                           # theme.app
    cards = [c for g in client.get("/api/cases").json() for c in g["cases"]]
    assert any(c["party"] == "Familie Beispiel" for c in cards)                               # meta.reported_by, before the address
