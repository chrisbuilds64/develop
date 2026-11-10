"""One worklist over several data points (REQ-005 PV-01 to PV-05, ADR-032): private ones and a shared one; each person
sees what they may read, starts where they write, shares and delegates between them."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import DataPoint, FsStore, MultiStore, StoreError

CFG = Path(__file__).resolve().parents[1] / "config" / "worklist"
STAGES = [s["folder"] for s in json.loads((CFG / "stages.json").read_text())["stages"]]


def tree(path: Path) -> Path:
    for s in STAGES:
        (path / s).mkdir(parents=True)
    return path


def points(tmp_path: Path) -> list[dict]:
    return [{"name": "chris", "root": str(tree(tmp_path / "dp-chris")), "readers": ["chris"], "writers": ["chris"], "label": "Private"},
            {"name": "akhil", "root": str(tree(tmp_path / "dp-akhil")), "readers": ["akhil"], "writers": ["akhil"], "label": "Private"},
            {"name": "team", "root": str(tree(tmp_path / "dp-team")), "readers": ["chris", "akhil"], "writers": ["chris", "akhil"], "label": "Team"}]


def app(tmp_path: Path, who: dict) -> TestClient:
    home = tree(tmp_path / "home")
    return TestClient(create_app(Settings(root=home, config_dir=CFG, lang="en", secret="t", identity=lambda r: who["name"],
                                          web_dist=None, data_points=points(tmp_path))))


def scoped(tmp_path: Path, viewer: str) -> tuple[MultiStore, DomainConfig]:
    pts = [DataPoint(name=d["name"], store=FsStore(Path(d["root"])), readers=set(d["readers"]), writers=set(d["writers"]), label=d["label"])
           for d in points_spec(tmp_path)]
    own = next(p.name for p in pts if p.readers == {viewer})
    return MultiStore(FsStore(tmp_path / "home"), pts, viewer=viewer, create_in=own), DomainConfig.load(CFG, tmp_path / "home")


def points_spec(tmp_path):
    return [{"name": n, "root": str(tmp_path / f"dp-{n}"), "readers": r, "writers": r, "label": l}
            for n, r, l in (("chris", ["chris"], "Private"), ("akhil", ["akhil"], "Private"), ("team", ["chris", "akhil"], "Team"))]


def new(client, title, n, **values):
    r = client.post("/api/cases", json={"title": title, "step_id": f"c{n}", "values": values})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def ids(client) -> set[str]:
    return {c["id"] for g in client.get("/api/stages").json() for c in g["cases"]}


def test_every_person_starts_in_their_private_data_point_and_sees_only_what_they_may_read(tmp_path):
    who = {"name": "chris"}
    client = app(tmp_path, who)
    mine = new(client, "Chris's own", 1, label="SYS", assignee="chris")
    assert (tmp_path / "dp-chris" / "10-backlog" / mine).is_dir()                   # PV-01: in the private data point
    who["name"] = "akhil"
    his = new(client, "Akhil's own", 2, label="SYS", assignee="akhil")
    assert (tmp_path / "dp-akhil" / "10-backlog" / his).is_dir()
    assert mine == "SYS-1" and his == "SYS-2"                                       # numbers count over every data point
    assert ids(client) == {his}                                                     # Akhil does not see Chris's item
    assert client.get(f"/api/cases/{mine}").status_code == 404
    who["name"] = "chris"
    assert ids(client) == {mine}


def test_a_case_of_an_unreadable_data_point_cannot_be_written(tmp_path):
    client = app(tmp_path, {"name": "chris"})
    mine = new(client, "Private", 1, label="SYS", assignee="chris")
    store, config = scoped(tmp_path, "akhil")
    r = stepping.step(store, config, mine, StepRequest(action="to_done", step_id="x1"), "akhil")
    assert not r.ok and "not found" in r.reason
    try:
        store.write_json(f"10-backlog/{mine}/meta.json", {})
        raise AssertionError("wrote into somebody else's private data point")
    except StoreError:
        pass


def test_share_moves_the_item_and_keeps_its_id(tmp_path):
    client = app(tmp_path, {"name": "chris"})
    cid = new(client, "For both of us", 1, label="MKT", assignee="chris")
    store, config = scoped(tmp_path, "chris")
    r = stepping.step(store, config, cid, StepRequest(action="share", step_id="s1", payload={"to": "team"}), "chris")
    assert r.ok, r.reason
    assert (tmp_path / "dp-team" / "10-backlog" / cid).is_dir() and not (tmp_path / "dp-chris" / "10-backlog" / cid).exists()
    akhil, _ = scoped(tmp_path, "akhil")
    assert akhil.find(cid) == "10-backlog"                                         # now Akhil sees it too
    assert "Team" in akhil.case_text(cid, "review.md")


def test_delegate_creates_there_and_closes_here(tmp_path):
    client = app(tmp_path, {"name": "chris"})
    cid = new(client, "Call the printer", 1, label="MKT", assignee="chris", priority="high")
    store, config = scoped(tmp_path, "chris")
    r = stepping.step(store, config, cid, StepRequest(action="delegate", step_id="d1", payload={"to": "akhil"}), "chris")
    assert r.ok, r.reason
    assert store.find(cid) == "90-done"                                             # mine closes …
    assert "MKT-2" in store.case_text(cid, "review.md")                              # … with the reference
    akhil, _ = scoped(tmp_path, "akhil")
    meta = akhil.case_json("MKT-2", "meta.json")                                    # … and it opens in his private data point
    assert (meta["assignee"], meta["created_by"], meta["priority"]) == ("akhil", "chris", "high")
    assert cid in meta["origin_ref"]
    assert store.find("MKT-2") is None                                              # Chris cannot read it there


def test_the_instance_shows_every_readable_item_marked_with_its_data_point(tmp_path):
    who = {"name": "chris"}
    client = app(tmp_path, who)
    a = new(client, "Mine", 1, label="SYS", assignee="chris")
    b = new(client, "Ours", 2, label="SYS", assignee="chris")
    store, config = scoped(tmp_path, "chris")
    assert stepping.step(store, config, b, StepRequest(action="share", step_id="s1", payload={"to": "team"}), "chris").ok
    assert ids(client) == {a, b}
    assert {store.point_of(a).label, store.point_of(b).label} == {"Private", "Team"}


def test_the_surface_marks_each_card_with_its_data_point(tmp_path):
    who = {"name": "chris"}
    client = app(tmp_path, who)
    a = new(client, "Mine", 1, label="SYS", assignee="chris")
    store, config = scoped(tmp_path, "chris")
    b = new(client, "Ours", 2, label="SYS", assignee="chris")
    assert stepping.step(store, config, b, StepRequest(action="share", step_id="s1", payload={"to": "team"}), "chris").ok
    marks = {c["id"]: c["data_point"] for g in client.get("/api/stages").json() for c in g["cases"]}
    assert marks == {a: "Private", b: "Team"}


def test_export_gives_every_readable_case_as_data(tmp_path):
    who = {"name": "chris"}
    client = app(tmp_path, who)
    a = new(client, "Mine", 1, label="INF", assignee="chris", due="2026-11-14")
    store, config = scoped(tmp_path, "chris")
    assert stepping.step(store, config, a, StepRequest(action="to_done", step_id="d1"), "chris").ok
    who["name"] = "akhil"
    new(client, "His", 2, label="SYS", assignee="akhil")
    who["name"] = "chris"
    rows = client.get("/api/export").json()
    assert [(r["id"], r["stage"], r["meta"]["due"], r["data_point"], bool(r["closed"])) for r in rows] == [(a, "90-done", "2026-11-14", "chris", True)]


def test_one_store_lists_every_stage_once_and_follows_its_own_moves(tmp_path):
    """Where each case lies is read once per store (a page asked thousands of times, 2026-11-10) and stays true when a
    case opens, moves or changes data point through that same store."""
    points(tmp_path)                                   # the data point trees
    tree(tmp_path / "home")
    first, _ = scoped(tmp_path, "chris")
    first.mkcase("10-backlog", "SYS-1")
    (first.case_dir("SYS-1") / "meta.json").write_text("{}", encoding="utf-8")
    store, _ = scoped(tmp_path, "chris")
    listed = []
    for p in store.points:
        orig = p.store.stages
        p.store.stages = lambda orig=orig: listed.append(1) or orig()
    for _ in range(50):
        assert store.find("SYS-1") == "10-backlog" and store.point_of("SYS-1").name == "chris"
    assert len(listed) == len(store.points)
    store.move("SYS-1", "20-next")
    assert store.find("SYS-1") == "20-next" and store.cases("20-next") == ["SYS-1"] and store.cases("10-backlog") == []
    store.transfer("SYS-1", "team")
    assert store.point_of("SYS-1").name == "team" and store.case_json("SYS-1", "meta.json") == {}
