"""Rating: the core computes the quote from the questionnaire and the rate table; a missing answer refuses and nothing moves.
And the inbox's hand-off opens a quote file whose first helper starts at once."""

import json
from email.message import EmailMessage
from pathlib import Path

import pytest

from casefile.config import DomainConfig
from casefile.connectors import mailbox
from casefile.domain import rating
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config"
TARIFF = json.loads((CFG / "angebot" / "tarif.json").read_text(encoding="utf-8"))
STAGES = ("10-anfrage", "20-rueckfrage", "30-angebot", "40-versand", "50-versendet")


def form(**values) -> dict:
    return {"product": "KFZ", "fields": [{"id": k, "word": k, "value": v, "quote": "…"} for k, v in values.items()]}


KFZ = dict(sf_klasse=12, sf_klasse_vk=12, fahrleistung=10000, juengster_fahrer=41, garage="ja", kasko="vollkasko")


def test_the_quote_follows_the_table_line_by_line():
    q = rating.rate(form(**KFZ), TARIFF)
    kh, vk = q["lines"]
    assert kh["amount"] == round(420 * 0.50 * 1.00 * 1.00 * 0.92, 2)
    assert vk["amount"] == round(560 * 0.48 * 1.00 * 1.00 * 0.92, 2)
    assert [f["answer"] for f in kh["factors"]] == [12, 10000, 41, "ja"]
    assert q["net"] == round(kh["amount"] + vk["amount"], 2) and q["tax"]["amount"] == 83.70 and q["gross"] == 524.20
    assert "Teilkasko" not in json.dumps(q)                      # a coverage applies only when its condition holds


def test_a_missing_answer_is_named_never_guessed():
    values = {k: v for k, v in KFZ.items() if k != "fahrleistung"}
    with pytest.raises(rating.RatingError, match="fahrleistung"):
        rating.rate(form(**values), TARIFF)
    marked = form(**KFZ)
    marked["fields"][2]["missing"] = True                         # a field the helper marked missing counts as missing
    with pytest.raises(rating.RatingError):
        rating.rate(marked, TARIFF)


def test_contents_rate_by_living_space():
    q = rating.rate({"product": "HR", "fields": [{"id": "wohnflaeche", "value": 85}, {"id": "tarifzone", "value": "2"},
                                                 {"id": "vorschaeden", "value": "0"}, {"id": "elementar", "value": "ja"}, {"id": "fahrrad", "value": "nein"}]}, TARIFF)
    assert [l["id"] for l in q["lines"]] == ["hr", "el"] and q["lines"][0]["amount"] == round(85 * 1.30, 2)


@pytest.fixture
def quotes(tmp_path):
    root = tmp_path / "angebot"
    for st in STAGES:
        (root / st).mkdir(parents=True)
    (root / "_runs").mkdir()
    store = FsStore(root)
    store.mkcase("10-anfrage", "KFZ-2026-0001-golf")
    store.write_json("10-anfrage/KFZ-2026-0001-golf/meta.json", {"label": "KFZ", "number": "2026-0001", "title": "Golf"})
    return store, DomainConfig.load(CFG / "angebot", root)


def test_calculate_writes_the_quote_or_refuses_without_moving(quotes):
    store, config = quotes
    cid = "KFZ-2026-0001-golf"
    store.write_json(f"10-anfrage/{cid}/fragebogen.json", form(**{k: v for k, v in KFZ.items() if k != "garage"}))
    r = stepping.step(store, config, cid, StepRequest(action="calculate", step_id="q1"), "chris")
    assert not r.ok and "garage" in r.reason and store.find(cid) == "10-anfrage" and not store.exists(f"10-anfrage/{cid}/angebot.md")
    store.write_json(f"10-anfrage/{cid}/fragebogen.v2.json", form(**KFZ))           # the customer's answer came in as a new version
    r = stepping.step(store, config, cid, StepRequest(action="calculate", step_id="q2"), "chris")
    assert r.ok and store.find(cid) == "30-angebot"
    md = store.case_text(cid, "angebot.md")
    assert "Jahresbeitrag" in md and "SF-Klasse Haftpflicht" in md and "nicht von der KI" in md


def test_a_quote_request_mail_opens_a_quote_file_and_starts_the_questionnaire(tmp_path, quotes):
    qstore, _ = quotes
    inbox = tmp_path / "inbox"
    for st in ("10-eingang", "30-erledigt", "40-abgelegt"):
        (inbox / st).mkdir(parents=True)
    (inbox / "_runs").mkdir()
    (inbox / "targets.json").write_text(json.dumps({"angebot": {"label": "Angebotsakte", "root": str(qstore.root), "config": str(CFG / "angebot")}}))
    store, config = FsStore(inbox), DomainConfig.load(CFG / "posteingang", inbox)
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = "Kim Muster <kim@example.invalid>", "agentur@example.invalid", "Angebot für meinen neuen Wagen", "<q1@example.invalid>"
    m.set_content("Bitte ein Angebot für meinen Golf, SF 12, 10.000 km im Jahr.")
    cid, _ = mailbox.ingest(store, config, bytes(m))
    (inbox / "10-eingang" / cid / "einordnung.json").write_text(json.dumps({"kind": "angebotsanfrage-kfz", "rule": "R-05",
                                                                           "fields": {"title": "Golf, Neuvertrag", "customer": "Kim Muster"}}))
    r = stepping.step(store, config, cid, StepRequest(action="confirm", step_id="h1"), "chris")
    assert r.ok
    act = json.loads((inbox / "30-erledigt" / cid / "aktion.json").read_text())
    assert act["case"].startswith("KFZ-2026-0002-") and (qstore.root / "10-anfrage" / act["case"] / "anfrage.md").is_file()
    run = json.loads((qstore.root / "_runs" / f"{act['run']}.json").read_text())
    assert run["skill"] == "angebot-fragebogen" and run["container"] == f"10-anfrage/{act['case']}"
