"""Read-only IMAP access: folders, counts, header blocks. Nothing here changes a mailbox."""

import base64
import imaplib
import re
from contextlib import contextmanager
from email import policy
from email.parser import HeaderParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

from .config import Account

HEADER_FIELDS = (
    "FROM TO CC DELIVERED-TO X-ORIGINAL-TO SUBJECT DATE MESSAGE-ID LIST-ID LIST-UNSUBSCRIBE "
    "PRECEDENCE AUTO-SUBMITTED X-AUTO-RESPONSE-SUPPRESS RETURN-PATH"
)
_LIST_RE = re.compile(rb'\((?P<flags>[^)]*)\) (?P<delim>"[^"]*"|NIL) (?P<name>.+)')


@contextmanager
def connect(account: Account):
    conn = imaplib.IMAP4_SSL(account.host, account.port, timeout=60)
    try:
        conn.login(account.login, account.password())
        yield conn
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def decode_folder(raw: str) -> str:
    """IMAP modified UTF-7 (RFC 3501) to str."""
    def repl(m):
        chunk = m.group(1)
        if not chunk:
            return "&"
        b64 = chunk.replace(",", "/")
        b64 += "=" * (-len(b64) % 4)
        return base64.b64decode(b64).decode("utf-16-be")
    return re.sub(r"&([^-]*)-", repl, raw)


def folders(conn) -> list[dict]:
    typ, lines = conn.list()
    out = []
    for line in lines or []:
        m = _LIST_RE.match(line)
        if not m:
            continue
        name = m.group("name").decode().strip()
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        flags = m.group("flags").decode()
        out.append({"raw": name, "name": decode_folder(name), "flags": flags})
    return out


def quote(raw: str) -> str:
    return '"' + raw.replace("\\", "\\\\").replace('"', '\\"') + '"'


def select(conn, raw: str) -> int | None:
    typ, data = conn.select(quote(raw), readonly=True)
    if typ != "OK":
        return None
    return int(data[0])


def search_uids(conn, criteria: str) -> list[bytes]:
    typ, data = conn.uid("SEARCH", None, criteria)
    return data[0].split() if typ == "OK" and data and data[0] else []


def all_uids(conn) -> list[bytes]:
    return search_uids(conn, "ALL")


def fetch_headers(conn, uids: list[bytes], batch: int = 200):
    """Yields (uid, header-dict). BODY.PEEK leaves the \\Seen flag untouched."""
    parser = HeaderParser(policy=policy.default)
    for i in range(0, len(uids), batch):
        chunk = b",".join(uids[i:i + batch]).decode()
        typ, data = conn.uid("FETCH", chunk, f"(UID RFC822.SIZE BODY.PEEK[HEADER.FIELDS ({HEADER_FIELDS})])")
        if typ != "OK":
            continue
        for item in data:
            if not isinstance(item, tuple):
                continue
            meta = item[0].decode(errors="replace")
            uid = re.search(r"UID (\d+)", meta)
            size = re.search(r"RFC822\.SIZE (\d+)", meta)
            yield (uid.group(1) if uid else None), summarize(parser.parsestr(item[1].decode(errors="replace")),
                                                            int(size.group(1)) if size else None)


def _h(msg, name) -> str:
    try:
        v = msg.get(name)
        return str(v).strip() if v is not None else ""
    except Exception:
        return ""


def summarize(msg, size) -> dict:
    name, addr = parseaddr(_h(msg, "From"))
    addr = addr.lower()
    try:
        date = parsedate_to_datetime(_h(msg, "Date")).isoformat()
    except Exception:
        date = None
    rcpt = [a.lower() for _, a in getaddresses([_h(msg, "To"), _h(msg, "Cc"), _h(msg, "Delivered-To"),
                                                 _h(msg, "X-Original-To")]) if a]
    return {
        "from_name": name,
        "from": addr,
        "domain": addr.rsplit("@", 1)[-1] if "@" in addr else "",
        "rcpt": sorted(set(rcpt)),
        "subject": _h(msg, "Subject"),
        "date": date,
        "message_id": _h(msg, "Message-ID"),
        "list_id": _h(msg, "List-Id"),
        "unsubscribe": bool(_h(msg, "List-Unsubscribe")),
        "precedence": _h(msg, "Precedence").lower(),
        "auto_submitted": _h(msg, "Auto-Submitted").lower(),
        "size": size,
    }
