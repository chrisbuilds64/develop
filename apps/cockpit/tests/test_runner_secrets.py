"""A skill's session gets the secrets its policy names and no others (Shipyard: the code host's token reaches the
build, never a content run); an agent's runs are billed to the person it belongs to."""

import stat
from argparse import Namespace
from pathlib import Path

from cockpit.account import Accounts
from cockpit.plugins.pipeline import runner


def secrets(tmp_path: Path) -> Path:
    d = tmp_path / "secrets"
    d.mkdir()
    (d / "GH_TOKEN").write_text("ghs_plain\n", encoding="utf-8")
    minted = d / "MINTED"
    minted.write_text("#!/bin/sh\necho ghs_minted\n", encoding="utf-8")
    minted.chmod(minted.stat().st_mode | stat.S_IXUSR)
    return d


def test_a_secret_reaches_only_the_skill_that_names_it(tmp_path):
    args = Namespace(secrets_dir=secrets(tmp_path))
    base = {"PATH": "/usr/bin", "GH_TOKEN": "inherited"}
    build = runner.policy_env({"secrets": ["GH_TOKEN", "MINTED"], "env": {"GIT_AUTHOR_NAME": "Axel"}}, args, base)
    assert build["GH_TOKEN"] == "ghs_plain" and build["MINTED"] == "ghs_minted" and build["GIT_AUTHOR_NAME"] == "Axel"
    content = runner.policy_env({}, args, base)
    assert "GH_TOKEN" not in content and content["PATH"] == "/usr/bin"


def test_a_missing_secret_is_left_out_not_invented(tmp_path):
    out = runner.policy_env({"secrets": ["NOPE"]}, Namespace(secrets_dir=tmp_path), {})
    assert "NOPE" not in out


def test_an_agents_runs_go_on_the_account_of_the_person_it_belongs_to(tmp_path):
    acc = Accounts(tmp_path / "accounts")
    token = "sk-ant-oat01-" + "x" * 48
    acc.dir("chris").mkdir(parents=True)
    acc.set_secret("chris", "CLAUDE_CODE_OAUTH_TOKEN", token)
    acc.dir("axel").mkdir(parents=True)
    acc._settings_path("axel").write_text('{"bill_to": "chris"}', encoding="utf-8")
    b = acc.billing("axel", {"ANTHROPIC_API_KEY": "shared"})
    assert b.mode == "subscription" and b.env["CLAUDE_CODE_OAUTH_TOKEN"] == token and "for axel" in b.source
    assert "ANTHROPIC_API_KEY" not in b.env
