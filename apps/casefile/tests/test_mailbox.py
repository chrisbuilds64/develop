"""The inbox (ADR-022): a mail becomes a case once, the helper's reading picks a row of the matrix, a person confirms and the
hand-off opens a case in another application — or refuses, and nothing moves."""

import json
from email.message import EmailMessage
from pathlib import Path

import pytest

from casefile.config import DomainConfig
from casefile.connectors import mailbox
from casefile.domain import cases as reading
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config"


def mail(subject="Unfall auf der A3", with_photo=True) -> bytes:
    m = EmailMessage()
    m["From"] = "Erika Muster <erika@example.invalid>"
    m["To"] = "schaden@example.invalid"
    m["Subject"] = subject
    m["Date"] = "Mon, 26 Oct 2026 09:12:00 +0100"
    m["Message-ID"] = f"<{abs(hash(subject))}@example.invalid>"
    m.set_content("Guten Tag,\nmir ist gestern jemand hinten aufgefahren. Kennzeichen MU-ST 123, Police KFZ 1234-5678.\nFoto anbei.\nErika Muster")
    if with_photo:
        m.add_attachment(b"\xff\xd8\xff fake jpeg", maintype="image", subtype="jpeg", filename="heck.jpg")
    return bytes(m)


@pytest.fixture
def world(tmp_path):
    inbox = tmp_path / "inbox"
    for st in ("10-eingang", "30-erledigt", "40-abgelegt"):
        (inbox / st).mkdir(parents=True)
    (inbox / "_runs").mkdir()
    claims = tmp_path / "claims"
    for st in ("10-meldung", "20-besichtigung", "25-abgleich", "30-pruefung", "40-regulierung", "60-abgeschlossen"):
        (claims / st).mkdir(parents=True)
    (inbox / "targets.json").write_text(json.dumps({"schadenakte": {"label": "Schadenakte", "root": str(claims), "config": str(CFG / "claims-demo"),
                                                                    "url": "../schadenakte", "external_prefix": "SN-"}}))
    store = FsStore(inbox)
    config = DomainConfig.load(CFG / "posteingang", inbox)
    return store, config, claims


def test_a_mail_becomes_one_case(world):
    store, config, _ = world
    cid, made = mailbox.ingest(store, config, mail())
    assert made and cid.startswith("MAIL-") and store.find(cid) == "10-eingang"
    files = store.files(cid)
    assert {"mail.eml", "mail.md", "heck.jpg", "meta.json", "review.md"} <= set(files)
    assert "Kennzeichen MU-ST 123" in store.case_text(cid, "mail.md")
    again, made2 = mailbox.ingest(store, config, mail())
    assert again == cid and not made2                         # the same Message-ID is the same case
    run = json.loads((store.root / "_runs" / store.runs()[0]).read_text())
    assert run["skill"] == "posteingang-einordnen"


def test_confirm_opens_a_claim_and_carries_the_photo(world):
    store, config, claims = world
    cid, _ = mailbox.ingest(store, config, mail())
    blocked = stepping.step(store, config, cid, StepRequest(action="confirm", step_id="c0"), "chris")
    assert not blocked.ok and "einordnung.json" in blocked.reason   # nothing to confirm before the reading
    (store.root / "10-eingang" / cid / "einordnung.json").write_text(json.dumps({
        "kind": "schadensmeldung", "rule": "R-01", "summary": "Auffahrunfall, Heckschaden.",
        "fields": {"title": "Auffahrunfall A3, Heckschaden", "summary_short": "Heck, Kennzeichen MU-ST 123", "policy": "KFZ 1234-5678"}}))
    done = stepping.step(store, config, cid, StepRequest(action="confirm", step_id="c1"), "chris")
    assert done.ok and done.to == "30-erledigt"
    act = json.loads((store.root / "30-erledigt" / cid / "aktion.json").read_text())
    target = claims / "10-meldung" / act["case"]
    assert act["case"].startswith("KFZ-") and target.is_dir()
    meta = json.loads((target / "meta.json").read_text())
    assert meta["title"] == "Auffahrunfall A3, Heckschaden" and meta["policy"] == "KFZ 1234-5678" and meta["external_id"].startswith("SN-")
    assert (target / "fotos-1.jpg").is_file() and (target / "meldung.md").is_file()
    case = reading.load(FsStore(claims), DomainConfig.load(CFG / "claims-demo", claims), act["case"])
    assert any("Posteingang" in e.author for e in case.entries)
    again = stepping.step(store, config, cid, StepRequest(action="confirm", step_id="c1"), "chris")
    assert again.replayed and len(list((claims / "10-meldung").iterdir())) == 1   # the same step twice opens one claim


def test_an_unconnected_target_moves_nothing(world):
    store, config, _ = world
    cid, _ = mailbox.ingest(store, config, mail("Themenvorschlag", with_photo=False))
    (store.root / "10-eingang" / cid / "einordnung.json").write_text(json.dumps({"kind": "themenvorschlag", "rule": "R-04", "fields": {"title": "x"}}))
    r = stepping.step(store, config, cid, StepRequest(action="confirm", step_id="r1"), "chris")
    assert not r.ok and "not connected" in r.reason and store.find(cid) == "10-eingang"


def test_a_question_reaches_the_claim_it_names_or_nothing_moves(world):
    store, config, claims = world
    (claims / "20-besichtigung" / "KFZ-2026-0430-auffahrunfall").mkdir()
    (claims / "20-besichtigung" / "KFZ-2026-0430-auffahrunfall" / "meta.json").write_text(json.dumps({"label": "KFZ", "title": "Auffahrunfall", "external_id": "SN-2026-00430"}))
    cid, _ = mailbox.ingest(store, config, mail("Rückfrage SN-2026-00430"))
    rd = store.root / "10-eingang" / cid / "einordnung.json"
    rd.write_text(json.dumps({"kind": "rueckfrage", "rule": "R-03", "summary": "Fragt nach dem Stand.", "fields": {"reference": "SN-2026-00999"}}))
    r = stepping.step(store, config, cid, StepRequest(action="confirm", step_id="q1"), "chris")
    assert not r.ok and "waits for SN-2026-00999" in r.reason and store.find(cid) == "10-eingang"
    rd.write_text(json.dumps({"kind": "rueckfrage", "rule": "R-03", "summary": "Fragt nach dem Stand.", "fields": {"reference": "SN-2026-00430"}}))
    assert stepping.step(store, config, cid, StepRequest(action="confirm", step_id="q2"), "chris").ok
    claim = claims / "20-besichtigung" / "KFZ-2026-0430-auffahrunfall"
    assert (claim / "rueckfrage.md").is_file() and not (claim / "fotos-1.jpg").exists()      # what the row carries, nothing else
    assert "Fragt nach dem Stand." in (claim / "review.md").read_text()


def test_a_topic_mail_becomes_a_signal_in_pressroom(world, tmp_path):
    store, config, _ = world
    press = tmp_path / "press"
    for st in ("00-archive", "05-operational-observations", "10-ideas"):
        (press / st).mkdir(parents=True)
    t = json.loads((store.root / "targets.json").read_text())
    t["pressroom"] = {"label": "PressRoom", "root": str(press), "config": str(CFG / "pressroom")}
    (store.root / "targets.json").write_text(json.dumps(t))
    cid, _ = mailbox.ingest(store, config, mail("Idee: Agenten im Schadenprozess", with_photo=False))
    (store.root / "10-eingang" / cid / "einordnung.json").write_text(json.dumps({"kind": "themenvorschlag", "rule": "R-04", "fields": {"title": "Agenten im Schadenprozess"}}))
    assert stepping.step(store, config, cid, StepRequest(action="confirm", step_id="t1"), "chris").ok
    made = list((press / "05-operational-observations").iterdir())
    assert len(made) == 1 and made[0].name.startswith("SIG-") and (made[0] / "anregung.md").is_file()
    assert not list((press / "10-ideas").iterdir())                    # a signal, not yet an idea
