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
    assert me["shell"] == "/"                                                            # and the menu knows the way back to the cockpit
    assert client.get("/w/nothing/api/me").status_code == 404
    home = client.get("/").text
    assert home.count('class="nav-row ws-row casefile-link') == 1 and 'href="/w/' in home   # the rail: Casefile once, not each workspace
    assert "PressRoom shared" not in home                                               # the workspaces are switched inside Casefile
    places = {p["id"]: p for p in me["places"]}
    assert places["shared"]["current"] and places["shared"]["name"] == "PressRoom shared"   # …whose rail lists them, this one current
    assert all(p["url"] == f"/w/{i}/" for i, p in places.items() if i != "shared")        # the others by their address in the cockpit


def test_under_a_prefix_the_mounted_surface_is_prefixed_once(world):
    toml = (world / "cockpit.toml").read_text(encoding="utf-8")
    (world / "cockpit.toml").write_text(toml.replace('bind = "127.0.0.1:8200"', 'bind = "127.0.0.1:8200"\nbase_path = "/test"\nenvironment = "test"'), encoding="utf-8")
    client = TestClient(create_app(load(world / "cockpit.toml")), root_path="/test", follow_redirects=False)
    client.get("/test/login")
    client.post("/test/login", data={"name": "alex", "password": "cockpit-demo", "_csrf": client.cookies["csrf"]})
    html = client.get("/test/w/shared/").text
    assert '<meta name="cf-base" content="/test/w/shared" />' in html
    assert 'src="/test/w/shared/assets/' in html and "/test/test/" not in html
    assert '<meta name="cf-stage" content="test" />' in html and 'class="cf-stage-badge">TEST<' in html   # the stage shows inside the surface too
    assert client.get("/test/w/shared/api/me").json()["shell"] == "/test/"
    assert 'data-env="test"' in client.get("/test/").text                                      # and on the shell's own pages
    assert client.get("/test/").status_code == 200 and 'href="/test/w/shared/"' in client.get("/test/").text


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


def test_an_application_marks_itself_through_its_theme_not_its_id(world, tmp_path):
    ws = Workspaces(world / "workspaces.json", world)
    app = ws.applications["pressroom"]
    assert (app.icon, app.color) == ("mic", "#F07A5C")                   # config/pressroom/theme.json → app
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "theme.json").write_text(json.dumps({"name": "Plain", "app": {"icon": "<script>", "color": "red"}}))
    reg = json.loads((world / "workspaces.json").read_text())
    reg["applications"]["plain"] = {"label": "Plain", "config_dir": str(plain)}
    (world / "workspaces.json").write_text(json.dumps(reg))
    again = Workspaces(world / "workspaces.json", world)
    assert (again.applications["plain"].icon, again.applications["plain"].color) == (None, None)   # nothing unsafe gets through
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(client)
    me = client.get("/w/shared/api/me").json()
    assert {p["color"] for p in me["places"]} >= {"#F07A5C"}             # Casefile's rail shows each workspace in its application's colour


def test_a_workspace_carries_its_data_points_and_writes_them_back(tmp_path):
    """ADR-032: an application instance over several data points; the registry reads them, makes the paths absolute,
    refuses a nameless or doubled one, and writes them back relative to itself."""
    reg = {"applications": {"wl": {"label": "Worklist", "config_dir": "cfg"}},
           "workspaces": [{"id": "team", "application": "wl", "root": "home", "members": ["chris"],
                           "data_points": [{"name": "chris", "root": "dp/chris", "readers": ["chris"], "writers": ["chris"], "label": "Private"},
                                           {"name": "team", "root": "dp/team", "readers": ["chris", "akhil"], "writers": ["chris", "akhil"]}]}]}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    ws = Workspaces(tmp_path / "workspaces.json", tmp_path)
    dps = ws.get("team").data_points
    assert [d["name"] for d in dps] == ["chris", "team"] and dps[0]["root"] == str(tmp_path / "dp" / "chris")
    ws.save()
    again = json.loads((tmp_path / "workspaces.json").read_text())["workspaces"][0]["data_points"]
    assert again[0] == {"name": "chris", "root": "dp/chris", "readers": ["chris"], "writers": ["chris"], "label": "Private"}
    reg["workspaces"][0]["data_points"].append({"name": "team", "root": "x"})
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    with pytest.raises(WorkspaceError):
        Workspaces(tmp_path / "workspaces.json", tmp_path)


def test_in_format_2_a_workspace_is_created_without_an_application_and_takes_one_after(world):
    """ADR-032: the form makes a workspace (name, members) first; an application instance joins it after, in its group."""
    from cockpit import workspace_registry as registry
    doc1 = json.loads((world / "workspaces.json").read_text())
    plan = {"connectors": {"server": {"kind": "directory", "label": "Server", "root": ""}},
            "workspaces": [{"id": "samples", "label": "Samples", "open": True, "members": [], "instances": ["shared"]}]}
    (world / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan)))
    users = json.loads((world / "users.json").read_text())
    users["users"]["chris"] = dict(users["users"]["alex"], display="Chris", context="home/chris/context")
    (world / "users.json").write_text(json.dumps(users))
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(client, "chris")
    page = client.get("/workspaces/new").text
    assert 'action="/workspaces/space"' in page and 'name="workspace"' in page
    r = client.post("/workspaces/space", data={"id": "party", "label": "Party", "_csrf": client.cookies["csrf"]})
    assert r.status_code == 303 and r.headers["location"] == "/workspaces/new?space=party"
    assert 'value="party" selected' in client.get("/workspaces/new?space=party").text
    r = client.post("/workspaces/new", data={"id": "party-list", "application": "pressroom", "label": "Party list", "workspace": "party",
                                             "_csrf": client.cookies["csrf"]})
    assert r.status_code == 303 and r.headers["location"] == "/w/party-list/"
    places = {p["id"]: p for p in client.get("/w/party-list/api/me").json()["places"]}
    assert places["party-list"]["workspace_label"] == "Party" and places["shared"]["workspace_label"] == "Samples"
    doc = json.loads((world / "workspaces.json").read_text())
    party = next(w for w in doc["workspaces"] if w["id"] == "party")
    assert party["members"] == ["chris"] and [i["id"] for i in party["instances"]] == ["party-list"]
    sign_in(client, "alex")                                              # not a member of the party
    assert client.get("/w/party-list/api/me").status_code in (302, 303, 403, 404)


def test_the_cockpit_shows_the_workspaces_above_the_tools_and_lets_them_be_managed(world):
    """ADR-032 made visible: rail and dashboard name the workspaces; /workspaces shows members, data points, instances."""
    from cockpit import workspace_registry as registry
    doc1 = json.loads((world / "workspaces.json").read_text())
    plan = {"connectors": {"server": {"kind": "directory", "label": "Server", "root": ""}},
            "workspaces": [{"id": "samples", "label": "Samples", "open": True, "members": [], "instances": ["shared"]},
                           {"id": "operations", "label": "Operations", "open": False, "members": ["alex"], "instances": []}]}
    (world / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan)))
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(client, "alex")
    home = client.get("/").text
    assert 'class="ws-card sp-card"' in home and "Samples" in home and "Operations" in home
    assert home.index('data-key="spaces"') < home.index('data-key="tools"')          # workspaces above the tools
    page = client.get("/workspaces").text
    assert 'id="ws-samples"' in page and "/w/shared/" in page and 'id="connectors"' in page
    r = client.post("/workspaces/move", data={"instance": "shared", "to": "operations", "_csrf": client.cookies["csrf"]})
    assert r.status_code == 303
    moved = Workspaces(world / "workspaces.json", world).get("shared")
    assert moved.workspace == "operations" and not moved.shared                    # alex administers the demo; closed now


def test_an_own_application_runs_as_an_instance_in_a_workspace_for_its_members_only(world):
    """ADR-032 (amended 2026-11-10): a plugin is an own application; its instance binds the plugin's needs to data points
    of its workspace, opens under /m/<id> for the workspace's members, and sits in that workspace — not under Tools."""
    from cockpit import workspace_registry as registry
    doc1 = json.loads((world / "workspaces.json").read_text())
    plan = {"connectors": {"server": {"kind": "directory", "label": "Server", "root": ""}},
            "workspaces": [{"id": "ops", "label": "Operations", "open": False, "members": ["alex"], "instances": ["shared"]}]}
    doc = registry.migrate(doc1, plan)
    doc["applications"]["audit-log"] = {"label": "Audits", "kind": "plugin", "plugin": "audits"}
    ops = doc["workspaces"][0]
    ops["data_points"].append({"name": "audits", "connector": "server", "place": "audits", "mode": "read"})
    ops["instances"].append({"id": "ops-audits", "application": "audit-log", "label": "Audits", "bind": {"audits": "audits"}})
    (world / "workspaces.json").write_text(json.dumps(doc))
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(client, "alex")
    assert client.get("/m/ops-audits").status_code == 200
    home = client.get("/").text
    assert 'href="/m/ops-audits"' not in home.split('data-key="tools"')[1].split("</details>")[0]   # not under Tools
    places = {p["id"]: p for p in client.get("/w/shared/api/me").json()["places"]}
    assert places["ops-audits"]["url"].endswith("/m/ops-audits") and places["ops-audits"]["workspace"] == "ops"
    sign_in(client, "sam")                                               # not a member of ops
    assert client.get("/m/ops-audits").status_code in (302, 303)


def test_a_retired_plugin_cannot_be_placed_in_a_workspace(world):
    from cockpit import workspace_registry as registry
    from cockpit.config import ConfigError, add_own_instances
    doc1 = json.loads((world / "workspaces.json").read_text())
    doc = registry.migrate(doc1, {"connectors": {"server": {"kind": "directory", "label": "S", "root": ""}},
                                  "workspaces": [{"id": "ops", "members": ["alex"], "instances": ["shared"]}]})
    doc["applications"]["old"] = {"label": "Work list", "kind": "plugin", "plugin": "worklist"}
    doc["workspaces"][0]["data_points"].append({"name": "wl", "connector": "server", "place": "worklist"})
    doc["workspaces"][0]["instances"].append({"id": "old-list", "application": "old", "bind": {"worklist": "wl", "tools": "wl"}})
    with pytest.raises(ConfigError, match="retired"):
        add_own_instances(load(world / "cockpit.toml"), registry.own_instances(doc))


def test_an_own_instance_reads_its_bound_data_point_not_a_source_named_like_the_need(world):
    """The module's sources are the bound source ids (`<instance>.<need>`); a reader passes them to Access as they are."""
    from cockpit import workspace_registry as registry
    from cockpit.access import Access
    from cockpit.audit import AuditLog
    from cockpit.config import add_own_instances
    from cockpit.registry import card_for
    doc = registry.migrate(json.loads((world / "workspaces.json").read_text()),
                           {"connectors": {"server": {"kind": "directory", "label": "S", "root": ""}},
                            "workspaces": [{"id": "ops", "members": ["alex"], "instances": ["shared"]}]})
    doc["applications"]["a"] = {"label": "Audits", "kind": "plugin", "plugin": "audits"}
    doc["workspaces"][0]["data_points"].append({"name": "au", "connector": "server", "place": str(world / "audits")})
    doc["workspaces"][0]["instances"].append({"id": "ops-audits", "application": "a", "bind": {"audits": "au"}})
    config = load(world / "cockpit.toml")
    config.sources.pop("audits", None)                                    # nothing named like the need may help it
    config.modules[:] = [m for m in config.modules if m.id != "audits"]
    add_own_instances(config, registry.own_instances(doc))
    card = card_for(config, Access(config, AuditLog(world / "a.jsonl"), {}), config.roles["operator"], "ops-audits")
    assert card.verdict != "denied" and card.panel, card.reason
