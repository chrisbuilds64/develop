"""Users and sessions — elementary, and built so the rest can grow.

A user has a name, a role and a **context directory**: the Context Loop folder
that is theirs. Sources in the configuration may say `{user.context}`, and for
the signed-in user that resolves to their folder. That is how one cockpit
serves several people on their own state without a database.

Passwords are PBKDF2 hashes in `users.json` (standard library, no package).
A session is an HMAC-signed cookie over a secret kept in a file beside the
configuration, mode 600, created on first use. There is no password reset,
no lockout, no expiry policy beyond the cookie's age — this is the elementary
version, and it says so.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class User:
    name: str
    role: str
    context: Path
    display: str = ""

    def as_vars(self) -> dict:
        return {"user.name": self.name, "user.context": str(self.context), "user.role": self.role}


class Users:
    def __init__(self, path: Path, secret_path: Path):
        self._path = Path(path)
        self._secret_path = Path(secret_path)
        self._data = json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {"users": {}}

    # ---------------------------------------------------------------- store
    def save(self) -> None:
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def add(self, name: str, password: str, role: str, context: str, display: str = "") -> None:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        self._data["users"][name] = {
            "role": role, "context": context, "display": display or name,
            "salt": base64.b64encode(salt).decode(), "hash": base64.b64encode(digest).decode(),
        }
        self.save()

    def remove(self, name: str) -> bool:
        return self._data["users"].pop(name, None) is not None

    def names(self) -> list[str]:
        return sorted(self._data["users"])

    def get(self, name: str, base: Path) -> User | None:
        u = self._data["users"].get(name)
        if not u:
            return None
        ctx = Path(u["context"]).expanduser()
        return User(name=name, role=u["role"], context=ctx if ctx.is_absolute() else base / ctx,
                    display=u.get("display", name))

    def verify(self, name: str, password: str) -> bool:
        u = self._data["users"].get(name)
        if not u:
            hashlib.pbkdf2_hmac("sha256", b"x", b"x" * 16, 200_000)   # same cost for unknown names
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(u["salt"]), 200_000)
        return hmac.compare_digest(digest, base64.b64decode(u["hash"]))

    # ------------------------------------------------------------- sessions
    def _secret(self) -> bytes:
        if not self._secret_path.exists():
            self._secret_path.write_bytes(secrets.token_bytes(32))
            os.chmod(self._secret_path, 0o600)
        return self._secret_path.read_bytes()

    def issue(self, name: str, max_age: int = 12 * 3600) -> str:
        payload = f"{name}|{int(time.time()) + max_age}"
        sig = hmac.new(self._secret(), payload.encode(), "sha256").hexdigest()
        return f"{payload}|{sig}"

    def redeem(self, token: str | None) -> str | None:
        if not token or token.count("|") != 2:
            return None
        name, expires, sig = token.split("|")
        good = hmac.new(self._secret(), f"{name}|{expires}".encode(), "sha256").hexdigest()
        if not hmac.compare_digest(sig, good) or int(expires) < time.time():
            return None
        return name if name in self._data["users"] else None
