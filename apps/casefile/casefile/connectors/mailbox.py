"""A mailbox as an inbox of cases: every message becomes a case in the application's first stage.

The message is kept as it came (`mail.eml`), shown as a document (`mail.md`), its attachments laid beside it; the case's
`meta.json` carries sender, subject, date and the Message-ID, which also makes ingesting idempotent — the same message
twice is one case. Then the helper is ordered that reads it and proposes what the rule matrix should do (`theme.mailbox`
names the helper and the stage). Reading the mailbox is IMAP over TLS with credentials from the environment, never
from a file in the tree; a message is marked seen only after its case exists.
"""

from __future__ import annotations

import datetime as dt
import email
import email.policy
import hashlib
import html
import imaplib
import json
import re
from email.message import EmailMessage
from email.utils import getaddresses, parsedate_to_datetime

from ..config import DomainConfig
from ..domain import runs as ordering
from ..domain import step as stepping
from ..store import FsStore, StoreError

SAFE = re.compile(r"[^A-Za-z0-9._-]+")
MAX_ATTACH = 15 * 1024 * 1024


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse(raw: bytes) -> dict:
    """The message as the core needs it: sender, recipients, subject, date, the text body, the attachments."""
    msg: EmailMessage = email.message_from_bytes(raw, policy=email.policy.default)        # type: ignore[assignment]
    body = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        text = body.get_content()
        if body.get_content_type() == "text/html":                                        # a html-only mail: tags out, text stays
            text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", text)))
            text = re.sub(r"[ \t]+", " ", text)
    attachments = []
    for part in msg.iter_attachments():
        name = part.get_filename() or "anhang"
        data = part.get_payload(decode=True) or b""
        if data and len(data) <= MAX_ATTACH:
            attachments.append({"name": SAFE.sub("-", name).strip("-")[:80] or "anhang", "type": part.get_content_type(), "data": data})
    try:
        date = parsedate_to_datetime(str(msg.get("date"))).astimezone().isoformat(timespec="seconds")
    except (TypeError, ValueError):
        date = _now()
    sender = getaddresses([str(msg.get("from", ""))])
    return {"message_id": str(msg.get("message-id") or "").strip() or "sha1:" + hashlib.sha1(raw).hexdigest(),
            "from_name": sender[0][0] if sender else "", "from": sender[0][1] if sender else "",
            "to": ", ".join(a for _, a in getaddresses([str(msg.get("to", ""))])), "subject": str(msg.get("subject") or "").strip(),
            "date": date, "text": text.strip(), "attachments": attachments}


def render(m: dict, lang: str = "de") -> str:
    """The message as a document for the reader."""
    w = {"de": ("Von", "An", "Datum", "Anhänge"), "en": ("From", "To", "Date", "Attachments")}.get(lang, ("From", "To", "Date", "Attachments"))
    who = f"{m['from_name']} <{m['from']}>" if m["from_name"] else m["from"]
    head = [f"# {m['subject'] or '—'}", "", f"**{w[0]}:** {who}  ", f"**{w[1]}:** {m['to']}  ", f"**{w[2]}:** {m['date'][:16].replace('T', ' ')}"]
    if m["attachments"]:
        head.append(f"  \n**{w[3]}:** " + ", ".join(a["name"] for a in m["attachments"]))
    return "\n".join(head) + "\n\n---\n\n" + m["text"] + "\n"


def _known(store: FsStore, message_id: str) -> str | None:
    for st in store.stages():
        for cid in store.cases(st):
            p = f"{st}/{cid}/meta.json"
            if store.exists(p):
                try:
                    if store.read_json(p).get("message_id") == message_id:
                        return cid
                except (OSError, ValueError):
                    continue
    return None


def ingest(store: FsStore, config: DomainConfig, raw: bytes, by: str = "", source: str = "") -> tuple[str, bool]:
    """One message → one case. Returns (case id, created). The same message twice returns the first case."""
    conf = config.theme.get("mailbox") or {}
    m = parse(raw)
    prior = _known(store, m["message_id"])
    if prior:
        return prior, False
    stage = conf.get("stage") or next((s.folder for s in config.stages if s.group != "archive"), None)
    if not stage or stage not in store.stages():
        raise StoreError("the inbox stage folder is missing")
    label = conf.get("label", "MAIL")
    year = dt.date.today().year
    numbers = [int(x.group(1)) for st in store.stages() for cid in store.cases(st) if (x := re.match(rf"^{re.escape(label)}-{year}-(\d+)", cid))]
    number = f"{year}-{(max(numbers) + 1) if numbers else 1:04d}"
    slug = re.sub(r"[^a-z0-9]+", "-", m["subject"].lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))).strip("-")[:40] or "mail"
    cid = f"{label}-{number}-{slug}"
    store.mkcase(stage, cid)
    meta = {"configVersion": config.config_version, "label": label, "number": number, "title": m["subject"] or "—",
            "subtitle": m["from_name"] or m["from"], "created": m["date"][:10], "message_id": m["message_id"], "from": m["from"],
            "from_name": m["from_name"], "received": m["date"], "source": source}
    store.write_json(f"{stage}/{cid}/meta.json", meta)
    store.put_bytes(cid, "mail.eml", raw)
    store.write_atomic(f"{stage}/{cid}/mail.md", render(m, config.lang))
    names = []
    for a in m["attachments"]:
        name = a["name"]
        n = 1
        while store.exists(f"{stage}/{cid}/{name}") or name in ("mail.md", "mail.eml", "meta.json", "review.md"):
            n += 1
            stem, dot, ext = a["name"].rpartition(".")
            name = f"{stem or a['name']}-{n}.{ext}" if dot else f"{a['name']}-{n}"
        store.put_bytes(cid, name, a["data"])
        names.append(name)
    agent = config.agent
    stepping._append_entry(store, config, cid, stage, {"author": m["from_name"] or m["from"] or "?", "status": "info",
                           "title": config.word("texts", "mail_in", None, "Mail received"), "text": (m["text"][:600] + ("…" if len(m["text"]) > 600 else "")) or "—",
                           "files": ["mail.md", *names]})
    helper = conf.get("helper")
    if helper and helper in (config.run_policy.get("skills") or {}):
        orderer = by or next((p.id for p in config.people if p.kind == "human" and "operator" in p.roles), "")
        ordering.order(store, config, cid, stage, helper, orderer, f"message={m['message_id']}", request_id=f"mail-{hashlib.sha1(m['message_id'].encode()).hexdigest()[:16]}")
    return cid, True


def poll_imap(store: FsStore, config: DomainConfig, host: str, user: str, password: str, port: int = 993, folder: str = "INBOX",
              limit: int = 20, by: str = "") -> list[str]:
    """Unseen messages → cases, oldest first; each is flagged seen after its case exists. Returns the case ids created."""
    made: list[str] = []
    with imaplib.IMAP4_SSL(host, port, timeout=30) as box:
        box.login(user, password)
        box.select(folder)
        typ, data = box.search(None, "UNSEEN")
        if typ != "OK":
            return made
        for num in (data[0].split() if data and data[0] else [])[:limit]:
            typ, parts = box.fetch(num, "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None) if typ == "OK" else None
            if not raw:
                continue
            cid, created = ingest(store, config, raw, by=by, source=f"imap:{user}")
            box.store(num, "+FLAGS", "\\Seen")
            if created:
                made.append(cid)
    return made


def state(root, write: dict | None = None) -> dict:
    """The poller's own memory beside the tree (`_mailbox/state.json`): when it last looked, what it found."""
    from pathlib import Path
    p = Path(root) / "_mailbox" / "state.json"
    if write is not None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(write, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return write
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
