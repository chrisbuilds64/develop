"""The registry in format 2 (ADR-032): connectors, workspaces with data points, application instances bound to them —
and the migration from format 1 that changes no instance's data, mode or template."""

import json
from pathlib import Path

import pytest

from cockpit import workspace_registry as registry
from cockpit.workspaces import Workspaces, peers_of

CONFIG = Path(__file__).resolve().parents[2] / "casefile" / "config"


def format1(tmp: Path) -> dict:
    """A stage like ours, in invented paths: a live application on a team folder, a sample filed as an application of
    its own over the same configuration, a mailbox for one person, and a worklist over three data points."""
    cloud = tmp / "cloud"
    return {
        "applications": {
            "pressroom": {"label": "PressRoom", "config_dir": str(CONFIG / "pressroom"), "mode": "live"},
            "pressroom-muster": {"label": "PressRoom · Muster", "config_dir": str(CONFIG / "pressroom"), "template": str(tmp / "worlds" / "pm"), "mode": "replay"},
            "posteingang": {"label": "Posteingang", "config_dir": str(CONFIG / "posteingang"), "template": str(tmp / "worlds" / "pe-live"), "mode": "live"},
            "worklist": {"label": "Worklist", "config_dir": str(CONFIG / "worklist"), "mode": "live"},
        },
        "workspaces": [
            {"id": "pressroom", "application": "pressroom", "label": "PressRoom", "shared": True, "members": ["ana", "ben"],
             "root": str(cloud / "data" / "1" / "files" / "flow"), "write_root": str(cloud / "mnt" / "pressroom" / "flow"), "mode": "live"},
            {"id": "posteingang", "application": "posteingang", "label": "Posteingang", "shared": True, "members": ["ana"],
             "root": "workspaces/shared/posteingang/flow", "mode": "live"},
            {"id": "worklist", "application": "worklist", "label": "Worklist", "shared": True, "members": ["ana", "ben"],
             "root": "workspaces/worklist/home", "mode": "live",
             "data_points": [{"name": "ana", "root": "workspaces/worklist/ana", "readers": ["ana"], "writers": ["ana"], "label": "Private"},
                             {"name": "team", "root": "workspaces/worklist/team", "readers": ["ana", "ben"], "writers": ["ana", "ben"], "label": "Team"}]},
            {"id": "pressroom-muster", "application": "pressroom-muster", "label": "PressRoom · Muster", "shared": True, "members": [],
             "root": "workspaces/shared/pressroom-muster/flow", "mode": "replay", "open_identity": True},
        ],
    }


def plan(tmp: Path) -> dict:
    cloud = tmp / "cloud"
    return {"connectors": {"nextcloud": {"kind": "nextcloud", "label": "Nextcloud", "root": str(cloud / "data"), "write_root": str(cloud / "mnt")},
                           "server": {"kind": "directory", "label": "Server directory", "root": ""}},
            "workspaces": [{"id": "operations", "label": "Operations", "open": False, "members": ["ana", "ben"],
                            "instances": ["pressroom", "posteingang", "worklist"]},
                           {"id": "samples", "label": "Samples", "open": True, "members": [], "instances": ["pressroom-muster"]}]}


@pytest.fixture
def stage(tmp_path):
    doc1 = format1(tmp_path)
    (tmp_path / "workspaces.json").write_text(json.dumps(doc1))
    return tmp_path, doc1


def test_the_migration_keeps_every_instance_where_it_was(stage):
    tmp, doc1 = stage
    doc2 = registry.migrate(doc1, plan(tmp))
    assert registry.check(doc1, doc2, tmp) == []
    before, after = Workspaces(tmp / "workspaces.json", tmp), None
    (tmp / "workspaces.json").write_text(json.dumps(doc2))
    after = Workspaces(tmp / "workspaces.json", tmp)
    for w in before.items:
        n = after.get(w.id)
        assert (n.root, n.write_root, n.mode, n.data_points, n.open_identity) == (w.root, w.write_root, w.mode, w.data_points, w.open_identity)
    assert after.get("pressroom").write_root == tmp / "cloud" / "mnt" / "pressroom" / "flow"


def test_a_sample_filed_as_an_application_becomes_a_seed_on_its_data_point(stage):
    tmp, doc1 = stage
    doc2 = registry.migrate(doc1, plan(tmp))
    assert "pressroom-muster" not in doc2["applications"]
    (tmp / "workspaces.json").write_text(json.dumps(doc2))
    w = Workspaces(tmp / "workspaces.json", tmp).get("pressroom-muster")
    assert w.application == "pressroom" and w.template == tmp / "worlds" / "pm"
    assert w.workspace == "samples" and w.workspace_label == "Samples"


def test_the_plan_must_name_every_entry_once(stage):
    tmp, doc1 = stage
    p = plan(tmp)
    p["workspaces"][0]["instances"].remove("worklist")
    with pytest.raises(registry.RegistryError, match="missing: worklist"):
        registry.migrate(doc1, p)
    p["workspaces"][0]["instances"] += ["worklist", "pressroom"]
    with pytest.raises(registry.RegistryError, match="twice: pressroom"):
        registry.migrate(doc1, p)


def test_a_closed_workspace_lets_in_its_members_and_an_instance_may_narrow_them(stage):
    tmp, doc1 = stage
    (tmp / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan(tmp))))
    ws = Workspaces(tmp / "workspaces.json", tmp)
    assert ws.may_open("ben", "pressroom") and not ws.may_open("cleo", "pressroom")
    assert ws.may_open("ana", "posteingang") and not ws.may_open("ben", "posteingang")
    assert ws.may_open("cleo", "pressroom-muster")                       # the samples are open to everybody signed in


def test_format_2_saves_back_in_format_2_and_a_new_instance_joins_its_workspace(stage):
    tmp, doc1 = stage
    (tmp / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan(tmp))))
    ws = Workspaces(tmp / "workspaces.json", tmp)
    w = ws.create("ben-notes", "worklist", "ben", label="Ben's notes", workspace="operations")
    doc = json.loads((tmp / "workspaces.json").read_text())
    assert doc["format"] == 2 and "applications" in doc and "connectors" in doc
    ops = next(x for x in doc["workspaces"] if x["id"] == "operations")
    assert any(i["id"] == "ben-notes" for i in ops["instances"]) and any(p["name"] == "ben-notes" for p in ops["data_points"])
    again = Workspaces(tmp / "workspaces.json", tmp)
    assert again.get("ben-notes").root == w.root and again.get("ben-notes").workspace == "operations"
    assert again.remove("ben-notes")
    doc = json.loads((tmp / "workspaces.json").read_text())
    ops = next(x for x in doc["workspaces"] if x["id"] == "operations")
    assert not any(p["name"] == "ben-notes" for p in ops["data_points"])     # its data point leaves with it
    assert any(p["name"] == "worklist-team" for p in ops["data_points"])     # the others stay


def test_an_unknown_data_point_or_connector_is_a_sentence(stage):
    tmp, doc1 = stage
    doc2 = registry.migrate(doc1, plan(tmp))
    doc2["workspaces"][0]["instances"][0]["bind"] = {"cases": "nowhere"}
    with pytest.raises(registry.RegistryError, match="data point 'nowhere' is not in workspace 'operations'"):
        registry.instances(doc2)
    doc2 = registry.migrate(doc1, plan(tmp))
    doc2["connectors"].pop("nextcloud")
    with pytest.raises(registry.RegistryError, match="connector 'nextcloud' is not defined"):
        registry.instances(doc2)


def test_the_rail_knows_each_instance_s_workspace(stage):
    tmp, doc1 = stage
    (tmp / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan(tmp))))
    ws = Workspaces(tmp / "workspaces.json", tmp)
    places = peers_of(ws, ws.get("pressroom"), None, "/")(None)
    by = {p["id"]: p["workspace"] for p in places}
    assert by["pressroom"] == "operations" and by["pressroom-muster"] == "samples"
    assert ws.spaces() == [{"id": "operations", "label": "Operations"}, {"id": "samples", "label": "Samples"}]


def test_the_runner_serves_the_live_instances_of_format_2(stage):
    import argparse
    from cockpit.plugins.pipeline import runner
    tmp, doc1 = stage
    (tmp / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan(tmp))))
    got = dict(runner.queues(argparse.Namespace(workspaces=tmp / "workspaces.json", data=None)))
    assert got["pressroom"] == tmp / "cloud" / "mnt" / "pressroom" / "flow"     # writes go through the mount, as before
    assert got["posteingang"] == tmp / "workspaces" / "shared" / "posteingang" / "flow"
    assert "pressroom-muster" not in got                                       # replay is never served by Claude


def test_an_instance_moves_with_its_data_points_and_keeps_its_address(stage):
    tmp, doc1 = stage
    (tmp / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan(tmp))))
    ws = Workspaces(tmp / "workspaces.json", tmp)
    root = ws.get("worklist").root
    ws.move("worklist", "samples")
    w = Workspaces(tmp / "workspaces.json", tmp).get("worklist")
    assert w.workspace == "samples" and w.root == root and [d["name"] for d in w.data_points] == ["ana", "team"]
    doc = json.loads((tmp / "workspaces.json").read_text())
    ops, samples = doc["workspaces"]
    assert not any(p["name"].startswith("worklist") for p in ops["data_points"])
    assert {p["name"] for p in samples["data_points"]} >= {"worklist-home", "worklist-ana", "worklist-team"}


def test_members_are_kept_per_workspace_and_decide_who_enters(stage):
    tmp, doc1 = stage
    (tmp / "workspaces.json").write_text(json.dumps(registry.migrate(doc1, plan(tmp))))
    ws = Workspaces(tmp / "workspaces.json", tmp)
    assert not ws.may_open("cleo", "pressroom")
    ws.set_members("operations", ["ana", "ben", "cleo", "cleo", ""])
    assert ws.may_open("cleo", "pressroom")
    assert [g["id"] for g in ws.grouped("cleo")] == ["operations", "samples"]
    assert [w.id for w in ws.grouped("cleo")[0]["items"]] == ["pressroom", "worklist"]     # the inbox stays narrowed to ana
