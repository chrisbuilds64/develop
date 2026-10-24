"""Accounts: settings a person chooses, secrets a person brings, and what the runner gets from them."""

import os

import pytest

from cockpit.account import AccountError, Accounts

TOKEN = "sk-ant-oat01-" + "a" * 60
KEY = "sk-ant-api03-" + "b" * 60


@pytest.fixture
def accounts(tmp_path):
    return Accounts(tmp_path / "accounts")


def test_a_secret_is_stored_privately_and_never_shown(accounts, tmp_path):
    accounts.set_secret("chris", "CLAUDE_CODE_OAUTH_TOKEN", TOKEN)
    d = tmp_path / "accounts" / "chris"
    assert oct(d.stat().st_mode & 0o777) == "0o700"
    assert oct((d / "secrets.env").stat().st_mode & 0o777) == "0o600"
    status = accounts.status("chris")
    assert status["secrets"]["CLAUDE_CODE_OAUTH_TOKEN"]["set"] is True
    assert status["secrets"]["CLAUDE_CODE_OAUTH_TOKEN"]["since"]
    assert status["secrets"]["ANTHROPIC_API_KEY"]["set"] is False
    assert TOKEN not in str(status) and TOKEN not in (d / "settings.json").read_text()


def test_a_malformed_secret_or_unknown_key_is_refused_before_anything_is_written(accounts, tmp_path):
    with pytest.raises(AccountError):
        accounts.set_secret("chris", "CLAUDE_CODE_OAUTH_TOKEN", "hello")
    with pytest.raises(AccountError):
        accounts.set_secret("chris", "GITHUB_TOKEN", TOKEN)
    with pytest.raises(AccountError):
        accounts.set("chris", "billing", "free")
    with pytest.raises(AccountError):
        accounts.dir("Chris Moser")
    assert not (tmp_path / "accounts" / "chris").exists()


def test_billing_picks_the_subscription_and_removes_the_shared_key(accounts):
    base = {"ANTHROPIC_API_KEY": "shared", "PATH": "/usr/bin"}
    assert accounts.billing("chris", base).mode == "api-key"               # no account yet: the shared key
    accounts.set_secret("chris", "CLAUDE_CODE_OAUTH_TOKEN", TOKEN)
    b = accounts.billing("chris", base)
    assert b.mode == "subscription" and b.env["CLAUDE_CODE_OAUTH_TOKEN"] == TOKEN
    assert "ANTHROPIC_API_KEY" not in b.env and b.env["PATH"] == "/usr/bin"
    assert base["ANTHROPIC_API_KEY"] == "shared"                            # the caller's environment is untouched
    accounts.set("chris", "billing", "api-key")                             # the person can insist on the key
    b = accounts.billing("chris", base)
    assert b.mode == "api-key" and b.env["ANTHROPIC_API_KEY"] == "shared" and "CLAUDE_CODE_OAUTH_TOKEN" not in b.env


def test_a_personal_key_replaces_the_shared_one_and_clearing_a_secret_falls_back(accounts):
    base = {"ANTHROPIC_API_KEY": "shared"}
    accounts.set_secret("akhil", "ANTHROPIC_API_KEY", KEY)
    assert accounts.billing("akhil", base).env["ANTHROPIC_API_KEY"] == KEY
    assert accounts.clear_secret("akhil", "ANTHROPIC_API_KEY") is True
    assert accounts.clear_secret("akhil", "ANTHROPIC_API_KEY") is False
    assert accounts.billing("akhil", base).source == "shared API key"
    assert accounts.status("akhil")["secrets"]["ANTHROPIC_API_KEY"]["set"] is False


def test_unknown_or_missing_orderer_gets_the_shared_key(accounts):
    base = {"ANTHROPIC_API_KEY": "shared"}
    assert accounts.billing(None, base).mode == "api-key"
    assert accounts.billing("", base).mode == "api-key"
    assert accounts.billing("../etc", base).mode == "api-key"
