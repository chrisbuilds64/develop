"""Workspaces: the registry, creating and cloning, who may open what — and casefile mounted under /w/<id> with the cockpit's login."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cockpit.app import create_app
from cockpit.config import load
from cockpit.workspaces import WorkspaceError, Workspaces

FIX = Path(__file__).resolve().parents[1] / "fixtures"
CASEFILE_CONFIG = Path(__file__).resolve().parents[2] / "casefile" / "config"


def build_template(where: Path) -> Path:
    from casefile.demo.worlds import build_pressroom
    return build_pressroom(where)


@pytest.fixture
def world(tmp_path):
    for d in ("flow", "worklist", "audits", "context-loop", "canon", "home", "plugins", "gatehouse-instance", "tools"):
        if (FIX / d).exists():
            shutil.copytree(FIX / d, tmp_path / d)
    shutil.copy(FIX / "users.json", tmp_path / "users.json")
    (tmp_path / "cockpit.toml").write_text((FIX / "cockpit.demo.toml").read_text(encoding="utf-8"), encoding="utf-8")
    template = build_template(tmp_path / "worlds" / "pressroom")
    reg = {"applications": {"pressroom": {"label": "PressRoom", "config_dir": str(CASEFILE_CONFIG / "pressroom"), "template": str(template)}},
           "workspaces": [{"id": "shared", "application": "pressroom", "label": "PressRoom shared", "shared": True, "root": str(template / "flow") if (template / "flow").is_dir() else str(template)}]}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    return tmp_path


def sign_in(client, name="alex", password="cockpit-demo"):
    client.get("/login")
    return client.post("/login", data={"name": name, "password": password, "_csrf": client.cookies["csrf"]})


# ------------------------------------------------------------------- the registry

def test_create_clones_the_source_and_starts_with_an_empty_queue(world):
    ws = Workspaces(world / "workspaces.json", world)
    assert [w.id for w in ws.for_user(None)] == ["shared"]
    w = ws.create("mine", "pressroom", "alex", label="Alex' PressRoom", source="shared")
    assert w.owner == "alex" and not w.shared and w.cloned_from == "shared"
    assert (w.root / "_runs").is_dir() and not any((w.root / "_runs").iterdir())
    assert (w.root / "workspace.json").is_file() and (w.root / "10-ideas").is_dir()
    assert ws.may_open("alex", "mine") and not ws.may_open("sam", "mine") and ws.may_open("sam", "shared")
    again = Workspaces(world / "workspaces.json", world)                 # saved, and relative to the registry
    assert again.get("mine").root == w.root


def test_bad_ids_unknown_applications_and_foreign_sources_are_refused(world):
    ws = Workspaces(world / "workspaces.json", world)
    for bad in ("Mine", "a b", "../x", "x"):
        with pytest.raises(WorkspaceError):
            ws.create(bad, "pressroom", "alex")
    with pytest.raises(WorkspaceError):
        ws.create("ok-id", "claims", "alex")
    ws.create("private", "pressroom", "sam")
    with pytest.raises(WorkspaceError):
        ws.create("copy", "pressroom", "alex", source="private")          # sam's, not alex's to copy
    with pytest.raises(WorkspaceError):
        ws.create("shared", "pressroom", "alex")                          # exists


def test_an_empty_workspace_comes_from_the_configuration(world):
    ws = Workspaces(world / "workspaces.json", world)
    ws.applications["pressroom"] = type(ws.applications["pressroom"])(id="pressroom", label="PressRoom", config_dir=CASEFILE_CONFIG / "pressroom", template=None)
    w = ws.create("fresh", "pressroom", "alex")
    assert (w.root / "30-review-human").is_dir() and (w.root / "people.json").is_file() and (w.root / "_runs").is_dir()


# ------------------------------------------------------------------- mounted behind the login

def test_workspaces_are_served_behind_the_cockpit_login_with_its_identity(world):
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    assert client.get("/w/shared/").status_code == 303                                  # a page: to the login
    assert client.get("/w/shared/api/me").status_code == 401                            # the API: a plain 401
    sign_in(client)
    html = client.get("/w/shared/").text
    assert '<meta name="cf-base" content="/w/shared" />' in html and 'src="/w/shared/assets/' in html
    me = client.get("/w/shared/api/me").json()
    assert me["identity"] == "alex" and me["open_identity"] is False                    # alex is signed in, but no person of this tree
    assert client.get("/w/nothing/api/me").status_code == 404
    home = client.get("/").text
    assert 'href="/w/shared/"' in home and "PressRoom shared" in home


def test_a_person_of_the_tree_works_in_it_and_a_clone_is_one_form_away(world):
    users = json.loads((world / "users.json").read_text())
    users["users"]["chris"] = dict(users["users"]["alex"], display="Chris", context="home/chris/context")
    (world / "users.json").write_text(json.dumps(users))
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(client, "chris")
    me = client.get("/w/shared/api/me").json()
    assert me["person"] == "chris" and me["name"] == "Chris"
    assert client.get("/w/shared/api/cases").status_code == 200
    r = client.post("/workspaces/new", data={"id": "chris-sandbox", "application": "pressroom", "label": "Sandbox", "source": "shared", "_csrf": client.cookies["csrf"]})
    assert r.status_code == 303 and r.headers["location"] == "/w/chris-sandbox/"
    assert client.get("/w/chris-sandbox/api/me").json()["person"] == "chris"           # mounted at once, same identity
    groups = client.get("/w/chris-sandbox/api/cases").json()
    assert sum(len(g["cases"]) for g in groups) == sum(len(g["cases"]) for g in client.get("/w/shared/api/cases").json())
    assert "chris-sandbox" in client.get("/").text
    acct = client.get("/account").text
    assert "CLAUDE_CODE_OAUTH_TOKEN" in acct and "sk-ant" not in acct.replace("sk-ant-…", "")
