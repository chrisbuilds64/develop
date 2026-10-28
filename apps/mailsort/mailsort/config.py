"""Account configuration. Lives outside the repo; passwords live in one file per account."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG = Path(os.environ.get("MAILSORT_CONFIG", "~/.config/mailsort/accounts.toml")).expanduser()
SECRETS = Path(os.environ.get("MAILSORT_SECRETS", "~/.secrets/mailsort")).expanduser()


@dataclass(frozen=True)
class Account:
    address: str
    host: str
    port: int = 993
    user: str | None = None
    secrets_dir: str | None = None

    @property
    def login(self) -> str:
        return self.user or self.address

    def password(self) -> str:
        base = Path(self.secrets_dir).expanduser() if self.secrets_dir else SECRETS
        return (base / self.address).read_text()


def load() -> tuple[str, list[Account]]:
    data = tomllib.loads(CONFIG.read_text())
    accounts = [Account(**a, secrets_dir=data.get("secrets_dir")) for a in data["account"]]
    return data["target"], accounts
