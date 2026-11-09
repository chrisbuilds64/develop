"""The worklist (REQ-005 WL-01 to WL-05, EX-03): an open item is a case; its number is its name; any member moves it."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import step as stepping
from casefile.domain.turn import turn as whose
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config" / "worklist"


def tree(tmp_path: Path) -> Path:
    root = tmp_path / "flow"
    for s in json.loads((CFG / "stages.json").read_text())["stages"]:
        (root / s["folder"]).mkdir(parents=True)
    return root


def api(root: Path, who: dict) -> TestClient:
    return TestClient(create_app(Settings(root=root, config_dir=CFG, lang="en", secret="t", identity=lambda request: who["name"], web_dist=None)))


def new(client, title, n, **values):
    r = client.post("/api/cases", json={"title": title, "step_id": f"c{n}", "values": values})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def step(store, config, cid, action, by, n, **payload):
    return stepping.step(store, config, cid, StepRequest(action=action, step_id=f"s{n}", payload=payload), by)


def test_an_item_carries_the_fields_of_todo_json(tmp_path):
    root, who = tree(tmp_path), {"name": "axel"}
    cid = new(api(root, who), "Audit the server", 1, label="INF", assignee="chris", due="2026-11-14", priority="high",
              origin_kind="decision", origin_ref="Chris 2026-11-09")
    meta = FsStore(root).case_json(cid, "meta.json")
    assert {k: meta[k] for k in ("label", "title", "assignee", "due", "priority", "origin_kind", "origin_ref", "created_by")} == {
        "label": "INF", "title": "Audit the server", "assignee": "chris", "due": "2026-11-14", "priority": "high",
        "origin_kind": "decision", "origin_ref": "Chris 2026-11-09", "created_by": "axel"}           # creator ≠ assignee
    assert meta["created"]


def test_a_value_outside_its_list_is_refused(tmp_path):
    root, who = tree(tmp_path), {"name": "chris"}
    client = api(root, who)
    for bad in ({"label": "NOPE"}, {"priority": "urgent"}, {"assignee": "nobody"}, {"due": "14.11.2026"}, {"colour": "red"}):
        r = client.post("/api/cases", json={"title": "x", "step_id": f"b{len(bad)}{list(bad)[0]}", "values": bad})
        assert r.status_code == 409, bad
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    cid = new(client, "A thing", 1)
    r = step(store, config, cid, "set_fields", "chris", 1, fields={"priority": "urgent"})
    assert not r.ok and "list 'priority'" in r.reason


def test_ids_survive_and_continue_per_cluster(tmp_path):
    root, who = tree(tmp_path), {"name": "chris"}
    (root / "90-done" / "SYS-147").mkdir()                                       # a moved item keeps its number
    (root / "90-done" / "SYS-147" / "meta.json").write_text(json.dumps({"label": "SYS", "number": "147", "title": "old"}))
    client = api(root, who)
    assert new(client, "Next system item", 1, label="SYS") == "SYS-148"
    assert new(client, "First infra item", 2, label="INF") == "INF-1"
    assert new(client, "Another", 3, label="SYS") == "SYS-149"


def test_any_file_may_be_added_none_is_required(tmp_path):
    root, who = tree(tmp_path), {"name": "chris"}
    cid = new(api(root, who), "With a sketch", 1, assignee="chris")
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    assert step(store, config, cid, "to_done", "chris", 1).ok                    # nothing required
    assert step(store, config, cid, "reopen", "chris", 2).ok
    (root / store.find(cid) / cid / "sketch.png").write_bytes(b"\x89PNG")
    assert step(store, config, cid, "deliver", "chris", 3, files=["sketch.png"]).ok
    assert any(s.file == "sketch.png" and s.present for s in reading.load(store, config, cid).slots)


def test_any_member_moves_and_done_sets_the_date(tmp_path):
    root, who = tree(tmp_path), {"name": "chris"}
    cid = new(api(root, who), "Rotate passwords", 1, label="INF", assignee="chris")
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    case = reading.load(store, config, cid)
    assert whose(case, config)[0].actor == "person:chris"                         # whose move: the assignee
    assert step(store, config, cid, "to_waiting", "akhil", 1).ok                  # somebody else may move it too
    assert step(store, config, cid, "to_doing", "axel", 2).ok                     # an agent member as well
    assert step(store, config, cid, "set_fields", "akhil", 3, fields={"assignee": "akhil", "due": "2026-12-01"}).ok
    case = reading.load(store, config, cid)
    assert whose(case, config)[0].actor == "person:akhil" and case.meta["due"] == "2026-12-01"
    assert "Assignee: chris → akhil" in case.entries[-1].text
    assert step(store, config, cid, "to_done", "chris", 4).ok
    case = reading.load(store, config, cid)
    assert case.stage == "90-done" and whose(case, config) == []                  # done: nobody's move
    closed = next(e for e in reversed(case.entries) if e.to == "90-done")
    assert closed.date[:10] == case.since[:10]                                    # the closing date is the move's
    assert step(store, config, cid, "reopen", "chris", 5).ok and store.find(cid) == "30-doing"
    assert step(store, config, cid, "set_fields", "chris", 6, fields={"due": ""}).ok
    assert "due" not in store.case_json(cid, "meta.json")                         # an empty value clears


def test_both_languages_name_every_stage_action_and_field():
    config = DomainConfig.load(CFG)
    theme = json.loads((CFG / "theme.json").read_text())
    fields = [k for k in theme["fields"] if not k.startswith("$")]
    for lang in ("de", "en"):
        v = config.vocabulary[lang]
        for s in config.stages:
            assert s.folder in v["stages"] and s.key in v["stations"], (lang, s.folder)
            for a in s.actions:
                assert a.label in v["actions"], (lang, a.label)
        for f in fields:
            assert f in v["fields"], (lang, f)
        for builtin in ("wait_for", "set_fields", "reopen"):
            assert builtin in v["actions"], (lang, builtin)
    for lst in config.lists.values():
        for e in lst["entries"]:
            assert e["word"].get("de") and e["word"].get("en"), e["key"]


def test_the_demo_world_shows_every_concept(tmp_path):
    """REQ-005 EX-01: case, stage, whose move, value list, document, gate, hand-off, dependency — on invented items."""
    from casefile.api import views
    from casefile.demo.worlds import build_worklist
    from casefile.domain import depends
    root = build_worklist(tmp_path / "worklist")
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    all_cases = {c.id: c for c in reading.load_all(store, config)}
    assert all(c.meta.get("fictional") is True for c in all_cases.values())
    assert {c.stage for c in all_cases.values()} == {s.folder for s in config.stages}                  # every stage holds one
    assert whose(all_cases["INF-7"], config)[0].actor == "person:du"                                     # whose move
    assert all_cases["INF-7"].meta["created_by"] == "helfer" != all_cases["INF-7"].meta["assignee"]      # creator ≠ assignee
    assert {c.meta["label"] for c in all_cases.values()} <= {e["key"] for e in config.lists["label"]["entries"]}   # value list
    assert any(s.file == "entwurf.md" and s.present for s in all_cases["CNT-21"].slots)                  # a document
    assert "Kim" in all_cases["MKT-3"].meta["origin_ref"]                                                # a hand-off
    resolve = depends.resolver_for(store, config)
    evt = views.view(config, all_cases["EVT-4"], "du", "en", lambda c, n: n, None, store)
    assert [(d.case, d.closed) for d in evt.waits] == [("INF-6", True), ("CNT-21", False)] and not evt.released
    assert depends.released(depends.waits(all_cases["SYS-11"].meta, resolve, "en"))                    # released, not moved
    assert all_cases["SYS-11"].stage == "20-next"
    r = step(store, config, "INF-7", "to_doing", "kim", 1)                                               # the gate is open:
    assert r.ok                                                                                          # any member moves
