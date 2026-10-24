"""Accounts: what a person configures for themselves, and the secrets they bring.

A user in `users.json` is a login (password, role, context). An account is the rest: settings the
person chooses (how their runs are billed, later more) and secrets they own (their subscription token
for the runner). One directory per person, shared by every stage of the cockpit, because a person is
one person on ENTW, TEST and PROD alike:

    <accounts>/<name>/settings.json      visible settings and, per secret, only *that* it is set and when
    <accounts>/<name>/secrets.env        KEY=value, mode 600 — read by the runner, shown to nobody

Three rules, like everywhere in the cockpit: nothing is written here that a tool does not validate
first; a secret's value never leaves this module except into the environment of the person's own run;
and the status of a secret is "set since <date>" or "not set", never a prefix, never a length.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

BILLING = ("auto", "subscription", "api-key")
# auto: the person's subscription token when one is set, the shared API key otherwise
SETTINGS = {"billing": BILLING, "locale": ("de", "en")}
# the secrets a person may bring, and the shape each one must have — a wrong shape is refused before anything is written
SECRETS = {
    "CLAUDE_CODE_OAUTH_TOKEN": re.compile(r"^sk-ant-oat01-[A-Za-z0-9_-]{40,}$"),   # `claude setup-token`, one year
    "ANTHROPIC_API_KEY": re.compile(r"^sk-ant-api03-[A-Za-z0-9_-]{40,}$"),        # a personal key, if someone prefers one
    "OPENAI_API_KEY": re.compile(r"^sk-(proj-|svcacct-)?[A-Za-z0-9_-]{20,}$"),     # for agents on the openai engine; billed by OpenAI's API, not a ChatGPT plan
}
NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class AccountError(Exception):
    """A sentence for the person, never a stack trace."""


@dataclass(frozen=True)
class Billing:
    mode: str              # "subscription" | "api-key" | "none" (nothing of the person's own, and the shared key is not allowed)
    env: dict              # the environment the run gets: the token set and the shared key removed, or untouched
    source: str            # one line for the log and the run record


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Accounts:
    def __init__(self, root: Path):
        self.root = Path(root)

    # ----------------------------------------------------------------- paths
    def dir(self, name: str) -> Path:
        if not NAME.match(name):
            raise AccountError(f"'{name}' is not an account name (lower-case letters, digits, - and _)")
        return self.root / name

    def _settings_path(self, name: str) -> Path:
        return self.dir(name) / "settings.json"

    def _secrets_path(self, name: str) -> Path:
        return self.dir(name) / "secrets.env"

    def _ensure(self, name: str) -> Path:
        d = self.dir(name)
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o700)
        return d

    # -------------------------------------------------------------- settings
    def settings(self, name: str) -> dict:
        p = self._settings_path(name)
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise AccountError(f"{p} is not valid JSON: {exc}") from exc

    def _save(self, name: str, data: dict) -> None:
        self._ensure(name)
        data["updated"] = _now()
        p = self._settings_path(name)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(p, 0o600)

    def set(self, name: str, key: str, value: str) -> dict:
        if key not in SETTINGS:
            raise AccountError(f"'{key}' is not a setting — one of: {', '.join(SETTINGS)}")
        if value not in SETTINGS[key]:
            raise AccountError(f"{key} = '{value}' is not allowed — one of: {', '.join(SETTINGS[key])}")
        data = self.settings(name)
        data[key] = value
        self._save(name, data)
        return data

    # --------------------------------------------------------------- secrets
    def _read_secrets(self, name: str) -> dict[str, str]:
        p = self._secrets_path(name)
        if not p.exists():
            return {}
        out = {}
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def _write_secrets(self, name: str, secrets: dict[str, str]) -> None:
        self._ensure(name)
        p = self._secrets_path(name)
        body = "# Secrets of this account — read by the runner for this person's own runs. Never shown, never copied.\n"
        body += "".join(f"{k}={v}\n" for k, v in sorted(secrets.items()))
        tmp = p.with_suffix(".tmp")
        tmp.write_text(body, encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(p)

    def set_secret(self, name: str, key: str, value: str) -> None:
        if key not in SECRETS:
            raise AccountError(f"'{key}' is not a secret this account can hold — one of: {', '.join(SECRETS)}")
        value = value.strip()
        if not SECRETS[key].match(value):
            raise AccountError(f"{key}: that does not look like a valid value — nothing was written")
        secrets = self._read_secrets(name)
        secrets[key] = value
        self._write_secrets(name, secrets)
        data = self.settings(name)
        data.setdefault("secrets", {})[key] = _now()          # when, never what
        self._save(name, data)

    def clear_secret(self, name: str, key: str) -> bool:
        secrets = self._read_secrets(name)
        had = secrets.pop(key, None) is not None
        if had:
            self._write_secrets(name, secrets)
            data = self.settings(name)
            data.get("secrets", {}).pop(key, None)
            self._save(name, data)
        return had

    # ---------------------------------------------------------------- status
    def status(self, name: str) -> dict:
        """Everything a person or a page may see: settings, and for each secret whether it is set and since when."""
        data = self.settings(name)
        present = self._read_secrets(name)
        return {
            "name": name,
            "billing": data.get("billing", "auto"),
            "locale": data.get("locale"),
            "secrets": {k: {"set": k in present, "since": data.get("secrets", {}).get(k)} for k in SECRETS},
            "updated": data.get("updated"),
        }

    # --------------------------------------------------------------- billing
    def openai_key(self, name: str | None) -> str | None:
        """The person's own OpenAI key, for agents on the openai engine. There is no shared one."""
        if name and NAME.match(name) and self.dir(name).exists():
            return self._read_secrets(name).get("OPENAI_API_KEY")
        return None

    def billing(self, name: str | None, base_env: dict, allow_shared: bool = False) -> Billing:
        """The environment for one run, chosen by the orderer's account.

        Subscription when the person has a token and has not said otherwise; the shared API key then
        leaves the environment, because Claude Code prefers the key whenever it sees one. A personal
        API key replaces the shared one. Without anything of their own the run is billed to nobody —
        mode "none" — unless the policy allows the shared key (`allow_shared`, a guest path that is
        off by default: everything runs on somebody's own account, never silently on the operator's).
        """
        if name and NAME.match(name) and self.dir(name).exists():
            data, secrets = self.settings(name), self._read_secrets(name)
            mode = data.get("billing", "auto")
            token = secrets.get("CLAUDE_CODE_OAUTH_TOKEN")
            if mode in ("auto", "subscription") and token:
                env = {k: v for k, v in base_env.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
                env["CLAUDE_CODE_OAUTH_TOKEN"] = token
                return Billing("subscription", env, f"subscription of {name}")
            if mode == "subscription":
                return Billing("api-key", dict(base_env), f"{name} asks for subscription but has no token — shared API key")
            if secrets.get("ANTHROPIC_API_KEY"):
                env = dict(base_env, ANTHROPIC_API_KEY=secrets["ANTHROPIC_API_KEY"])
                env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
                return Billing("api-key", env, f"personal API key of {name}")
        if allow_shared:
            return Billing("api-key", dict(base_env), "shared API key (allowed by policy)")
        who = name or "the orderer"
        return Billing("none", {}, f"{who} has no subscription token and no personal API key — the shared key is not allowed")
