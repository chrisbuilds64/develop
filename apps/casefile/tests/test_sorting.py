"""Sorting before reading: a rule that decides writes the reading itself and no AI reads the mail; with automatic approval
the case is done at once; a sender on the privacy list waits for a person; what no rule decides goes to the helper."""

import json
from email.message import EmailMessage

import pytest

from casefile.config import DomainConfig
from casefile.connectors import mailbox
from casefile.domain import sorting
from casefile.store import FsStore

from .test_mailbox import CFG


def mail(subject: str, sender: str = "Erika Muster <erika@example.invalid>", **headers) -> bytes:
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, "schaden@example.invalid", subject
    m["Date"], m["Message-ID"] = "Mon, 26 Oct 2026 09:12:00 +0100", f"<{abs(hash((subject, sender)))}@example.invalid>"
    for k, v in headers.items():
        m[k.replace("_", "-")] = v
    m.set_content("Guten Tag")
    return bytes(m)


@pytest.fixture
def inbox(tmp_path):
    root = tmp_path / "inbox"
    for st in ("10-eingang", "30-erledigt", "40-abgelegt"):
        (root / st).mkdir(parents=True)
    (root / "_runs").mkdir()
    rules = json.loads((CFG / "posteingang" / "regeln.json").read_text(encoding="utf-8"))
    rules["privacy"] = {"never_ai": ["arzt.example"]}
    (root / "regeln.json").write_text(json.dumps(rules), encoding="utf-8")
    return FsStore(root), DomainConfig.load(CFG / "posteingang", root)


def reading(store, cid):
    return json.loads((store.root / store.find(cid) / cid / "einordnung.json").read_text())


def test_a_newsletter_is_sorted_by_its_headers_and_no_ai_reads_it(inbox):
    store, config = inbox
    cid, _ = mailbox.ingest(store, config, mail("Herbstaktion", "News <news@shop.example>", List_Unsubscribe="<mailto:x@shop.example>"))
    r = reading(store, cid)
    assert r["rule"] == "R-09" and r["by"] == "rule" and r["reasons"] == ["list/bulk headers"]
    assert store.runs() == [] and store.find(cid) == "10-eingang"          # approval is human: a person confirms


def test_automatic_approval_files_the_case_at_once(inbox):
    store, config = inbox
    doc = json.loads((store.root / "regeln.json").read_text())
    next(r for r in doc["rules"] if r["id"] == "R-09")["approval"] = "auto"
    (store.root / "regeln.json").write_text(json.dumps(doc))
    cid, _ = mailbox.ingest(store, config, mail("Newsletter", "News <news@shop.example>", Precedence="bulk"))
    assert store.find(cid) == "40-abgelegt" and store.runs() == []           # filed away, never deleted


def test_a_reference_in_the_subject_becomes_a_field(inbox):
    store, config = inbox
    cid, _ = mailbox.ingest(store, config, mail("Rückfrage zu SN-2026-00430"))
    r = reading(store, cid)
    assert r["rule"] == "R-03" and r["fields"]["reference"] == "SN-2026-00430" and store.runs() == []


def test_a_sender_on_the_privacy_list_waits_for_a_person(inbox):
    store, config = inbox
    cid, _ = mailbox.ingest(store, config, mail("Befund", "Praxis <post@arzt.example>"))
    assert store.runs() == [] and not (store.root / "10-eingang" / cid / "einordnung.json").exists()
    assert "arzt.example" in (store.root / "10-eingang" / cid / "review.md").read_text()


def test_what_no_rule_decides_goes_to_the_helper(inbox):
    store, config = inbox
    mailbox.ingest(store, config, mail("Unfall auf der A3"))
    assert json.loads((store.root / "_runs" / store.runs()[0]).read_text())["skill"] == "posteingang-einordnen"


def test_the_longest_domain_wins_and_subdomains_count():
    rows = [{"id": "a", "sort": {"domains": ["example.com"]}}, {"id": "b", "sort": {"domains": ["shop.example.com"]}}]
    assert sorting.classify({"domain": "mail.shop.example.com", "subject": ""}, rows)[0]["id"] == "b"
    assert sorting.classify({"domain": "other.org", "subject": ""}, rows) is None
