"""Personal tokens: reaching a workspace's API from outside the server (ADR-031 decision 6, REQ-005 IF-01 to IF-03).

A token belongs to one person or one agent. It names the workspaces it opens and whether it may write; it expires; it
can be revoked at once. Only a hash is kept — the token itself is shown once, when it is issued, and never again.

    cbt_<id>_<secret>                      sent as `Authorization: Bearer cbt_…`

Who may issue: the owner for themselves, or the person an agent belongs to (its account's `bill_to`, ADR-020). The
token's owner is the identity every request with it works as, so every step it makes is journaled under that name.
The file is `tokens.json` beside the accounts, mode 600.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

PREFIX = "cbt_"
FORMAT = re.compile(r"^cbt_([a-f0-9]{8})_([A-Za-z0-9_-]{32,})$")
READ_METHODS = ("GET", "HEAD", "OPTIONS")
MAX_DAYS = 365


class TokenError(Exception):
    """A refusal, in the sentence the person reads."""


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class Tokens:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _load(self) -> list[dict]:
        try:
            doc = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [t for t in doc.get("tokens", []) if isinstance(t, dict)]

    def _save(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.tmp-{os.getpid()}")
        tmp.write_text(json.dumps({"tokens": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    # ------------------------------------------------------------------ issuing
    def issue(self, owner: str, issued_by: str, workspaces: list[str], write: bool, days: int, may_issue_for) -> str:
        """A new token; returns it in full, once. `may_issue_for(issued_by, owner)` says whether that person may."""
        owner, issued_by = owner.strip().lower(), issued_by.strip().lower()
        if not owner or not workspaces:
            raise TokenError("a token needs an owner and at least one workspace")
        if not may_issue_for(issued_by, owner):
            raise TokenError(f"{issued_by} may not issue a token for {owner}")
        if not 1 <= days <= MAX_DAYS:
            raise TokenError(f"a token lives between 1 and {MAX_DAYS} days")
        tid, secret = secrets.token_hex(4), secrets.token_urlsafe(32)
        items = self._load()
        items.append({"id": tid, "hash": _hash(secret), "owner": owner, "issued_by": issued_by,
                      "workspaces": sorted(set(workspaces)), "write": bool(write),
                      "created": _now().isoformat(timespec="seconds"),
                      "expires": (_now() + dt.timedelta(days=days)).isoformat(timespec="seconds"), "revoked": None})
        self._save(items)
        return f"{PREFIX}{tid}_{secret}"

    def revoke(self, tid: str, by: str) -> dict:
        items = self._load()
        t = next((x for x in items if x["id"] == tid), None)
        if t is None:
            raise TokenError(f"no token '{tid}'")
        by = by.strip().lower()
        if by not in (t["owner"], t["issued_by"]):
            raise TokenError(f"{by} may not revoke token '{tid}'")
        t["revoked"] = _now().isoformat(timespec="seconds")
        self._save(items)
        return t

    def listing(self, person: str) -> list[dict]:
        """Tokens a person owns or issued, without their hashes."""
        person = person.strip().lower()
        return [{k: v for k, v in t.items() if k != "hash"} for t in self._load() if person in (t["owner"], t["issued_by"])]

    # ------------------------------------------------------------------ using
    def owner(self, raw: str | None) -> dict | None:
        """The live token behind a bearer value, or None: unknown, malformed, expired or revoked."""
        m = FORMAT.match((raw or "").strip())
        if not m:
            return None
        t = next((x for x in self._load() if x["id"] == m.group(1)), None)
        if t is None or t.get("revoked") or not hmac.compare_digest(t["hash"], _hash(m.group(2))):
            return None
        if dt.datetime.fromisoformat(t["expires"]) <= _now():
            return None
        return t

    @staticmethod
    def allows(t: dict, workspace: str, method: str) -> str | None:
        """Why this token may not do this request, or None."""
        if workspace not in t["workspaces"]:
            return "this token does not open this workspace"
        if method.upper() not in READ_METHODS and not t["write"]:
            return "this token may only read"
        return None


def bearer(headers) -> str | None:
    v = headers.get("authorization") or ""
    return v[7:].strip() if v.lower().startswith("bearer ") else None
