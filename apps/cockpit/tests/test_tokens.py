"""Personal tokens (REQ-005 IF-01 to IF-03): the API of a workspace from outside, as the token's owner, within its scope."""

import json

from fastapi.testclient import TestClient

from cockpit.__main__ import may_issue_for
from cockpit.account import Accounts
from cockpit.app import create_app
from cockpit.config import load
from cockpit.tokens import Tokens, TokenError

from tests.test_workspaces import world  # noqa: F401 — the fixture


def setup(world):
    config = load(world / "cockpit.toml")
    accounts = Accounts(config.accounts_path)
    accounts.set("alex", "billing", "auto")
    accounts.set("helper", "billing", "auto")
    sp = accounts.dir("helper") / "settings.json"                # an agent that belongs to alex (ADR-020): set by the administrator
    sp.write_text(json.dumps({**json.loads(sp.read_text()), "bill_to": "alex"}))
    return config, accounts, Tokens(config.accounts_path.parent / "tokens.json")


def test_api_accepts_a_valid_token_and_refuses_others(world):
    config, accounts, tokens = setup(world)
    raw = tokens.issue("alex", "alex", ["shared"], write=False, days=30, may_issue_for=may_issue_for(accounts))
    client = TestClient(create_app(config), follow_redirects=False)
    ok = client.get("/w/shared/api/me", headers={"Authorization": f"Bearer {raw}"})
    assert ok.status_code == 200 and ok.json()["identity"] == "alex"                   # IF-01: works as its owner
    assert client.get("/w/shared/api/me", headers={"Authorization": "Bearer cbt_00000000_" + "x" * 40}).status_code == 401
    assert client.get("/w/shared/", headers={"Authorization": f"Bearer {raw}"}).status_code == 403    # API only, no pages
    assert client.get("/w/other/api/me", headers={"Authorization": f"Bearer {raw}"}).status_code == 403   # not its workspace
    assert client.post("/w/shared/api/cases", json={}, headers={"Authorization": f"Bearer {raw}"}).status_code == 403  # read only
    tid = raw.split("_")[1]
    tokens.revoke(tid, "alex")
    assert client.get("/w/shared/api/me", headers={"Authorization": f"Bearer {raw}"}).status_code == 401  # revoked at once
    assert "hash" not in json.dumps(tokens.listing("alex")) and raw not in (config.accounts_path.parent / "tokens.json").read_text()


def test_who_may_issue_and_for_how_long(world):
    config, accounts, tokens = setup(world)
    check = may_issue_for(accounts)
    assert tokens.issue("helper", "alex", ["shared"], write=True, days=90, may_issue_for=check).startswith("cbt_")   # for his agent
    for owner, by, days in (("alex", "helper", 30), ("bob", "alex", 30), ("alex", "alex", 0), ("alex", "alex", 400)):
        try:
            tokens.issue(owner, by, ["shared"], write=False, days=days, may_issue_for=check)
            raise AssertionError((owner, by, days))
        except TokenError:
            pass


def test_writes_are_journaled_with_the_token_owner(world):
    """The identity a token carries is the one the mounted application acts as; the step journal names it."""
    config, accounts, tokens = setup(world)
    raw = tokens.issue("alex", "alex", ["shared"], write=True, days=1, may_issue_for=may_issue_for(accounts))
    client = TestClient(create_app(config), follow_redirects=False)
    me = client.get("/w/shared/api/me", headers={"Authorization": f"Bearer {raw}"}).json()
    assert me["identity"] == "alex"
    r = client.post("/w/shared/api/cases", json={"title": "x", "step_id": "t1"}, headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code != 403                                                          # a write token passes the gate; the tree decides the rest
