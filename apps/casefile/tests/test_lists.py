"""Value lists (SYS-105): loading and merging, the older labels/covers, covers by any list, changing as an operator only,
the log line, a retired entry staying readable — and a list no configuration knows, started from the surface and offered
to a new case."""

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from casefile.api import views
from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import lists as value_lists
from casefile.store import FsStore

from .world import CONFIG, build


def _world(tmp_path, with_lists=True, theme_extra=None):
    root = build(tmp_path / "flow")
    cfg = root.parent / "config"
    if with_lists:
        shutil.copy(CONFIG / "lists.json", cfg / "lists.json")
    if theme_extra:
        theme = json.loads((cfg / "theme.json").read_text())
        (cfg / "theme.json").write_text(json.dumps({**theme, **theme_extra}))
    return root, cfg


def _client(root, cfg):
    client = TestClient(create_app(Settings(root=root, config_dir=cfg, lang="en", secret="test")))
    return client


def sign_in(client, person="chris"):
    assert client.post("/api/session", json={"person": person}).status_code == 200


# ----------------------------------------------------------------------------- loading
def test_the_domain_lists_load_and_the_tree_adds_to_them(tmp_path):
    root, cfg = _world(tmp_path)
    (root / "lists.json").write_text(json.dumps({"lists": {
        "series": {"entries": [{"key": "NEW", "word": {"en": "A new one"}, "status": "planned"}, {"key": "GH", "word": {"de": "Torhaus"}}]},
        "label": {"word": {"de": "Formatart"}}}}))
    c = DomainConfig.load(cfg, root)
    assert set(c.lists) >= {"label", "series", "track"}
    series = c.lists["series"]
    assert series["field"] == "series" and series["on_create"] is True
    keys = [e["key"] for e in series["entries"]]
    assert keys[:5] == ["ARC", "SIM", "RT", "GH", "STP"] and keys[-1] == "NEW"
    gh = value_lists.entry(c.lists, "series", "GH")
    assert gh["word"] == {"de": "Torhaus", "en": "Gatehouse"}                    # the tree's word added, the domain's kept
    assert value_lists.entry(c.lists, "series", "NEW")["status"] == "planned"
    assert c.lists["label"]["word"] == {"de": "Formatart", "en": "Format"}
    assert value_lists.entry(c.lists, "label", "FN")["color"] == "#2f6fed"
    assert [e["key"] for e in c.lists["track"]["entries"]] == ["deep-tech", "provocative", "business", "weekend-notes"]


def test_without_lists_json_the_labels_and_covers_become_a_list(tmp_path):
    root, cfg = _world(tmp_path, with_lists=False)
    c = DomainConfig.load(cfg, root)
    assert list(c.lists) == ["label"]                                            # translated on load: vocabulary.labels + covers.colors
    fn = value_lists.entry(c.lists, "label", "FN")
    assert fn["word"]["en"] == "Essay" and fn["word"]["de"] == "Essay" and fn["color"] == "#2f6fed"
    assert c.word("labels", "POD", "en") == "Podcast episode"                    # the old word lookup still answers
    store = FsStore(root)
    card = views.card(c, reading.load(store, c, "POD-110-the-silent-failure"), "chris", "en")
    assert card.tint == "#e0a52a" and card.label_word == "Podcast episode"
    assert views.config_view(c, "en").lists[0].entries[0].word


def test_covers_by_another_list_take_the_entry_colour_then_colors_then_fallback(tmp_path):
    root, cfg = _world(tmp_path, theme_extra={"covers": {"by": "series", "colors": {"RT": "#111111"}, "fallback": "#5a6270"}})
    (root / "lists.json").write_text(json.dumps({"lists": {"series": {"entries": [{"key": "GH", "color": "#123456"}]}}}))
    c = DomainConfig.load(cfg, root)
    assert value_lists.tint(c.lists, c.theme, {"series": "GH"}) == "#123456"
    assert value_lists.tint(c.lists, c.theme, {"series": "RT"}) == "#111111"
    assert value_lists.tint(c.lists, c.theme, {"label": "FN"}) == "#5a6270"
    store = FsStore(root)
    case = reading.load(store, c, "POD-110-the-silent-failure")
    case.meta["series"] = "GH"
    assert views.card(c, case, "chris", "en").tint == "#123456"


# ----------------------------------------------------------------------------- changing
def test_only_an_operator_changes_a_list_and_each_change_leaves_a_line(tmp_path):
    root, cfg = _world(tmp_path)
    before = (cfg / "lists.json").read_text()
    client = _client(root, cfg)
    sign_in(client, "akhil")
    r = client.post("/api/lists/series/entries", json={"key": "OPS", "word": {"de": "Betrieb", "en": "Operations"}, "step_id": "l-1"})
    assert r.status_code == 403 and r.json()["reason"].endswith(".")
    assert client.get("/api/lists").json()["may_edit"] is False
    sign_in(client, "chris")
    assert client.get("/api/lists").json()["may_edit"] is True
    r = client.post("/api/lists/series/entries", json={"key": "OPS", "word": {"de": "Betrieb", "en": "Operations"}, "color": "#336699", "status": "planned", "step_id": "l-2"})
    assert r.status_code == 200, r.text
    assert r.json()["list"]["entries"][-1] == {"key": "OPS", "word": "Operations", "words": {"de": "Betrieb", "en": "Operations"}, "color": "#336699",
                                               "description": "", "status": "planned", "cases": 0}
    again = client.post("/api/lists/series/entries", json={"key": "OPS", "word": {"en": "Other"}, "step_id": "l-2"})
    assert again.status_code == 200 and again.json()["line"]["what"] == "entry"   # the same step id twice is the same change
    tree = json.loads((root / "lists.json").read_text())
    assert tree["lists"]["series"]["entries"] == [{"key": "OPS", "word": {"de": "Betrieb", "en": "Operations"}, "color": "#336699", "status": "planned"}]
    assert (cfg / "lists.json").read_text() == before                            # the domain's configuration is never written
    lines = [json.loads(l) for l in (root / "_lists" / "log.jsonl").read_text().splitlines()]
    assert len(lines) == 1 and lines[0]["by"] == "chris" and lines[0]["list"] == "series" and lines[0]["key"] == "OPS" and lines[0]["at"]
    for bad, why in (({"key": "ops"}, "capital"), ({"key": "GH"}, "Nothing"), ({"key": "NEW2"}, "name"), ({"key": "GH2", "word": {"en": "x"}, "status": "gone"}, "status")):
        r = client.post("/api/lists/series/entries", json={**bad, "step_id": f"bad-{why}"})
        assert r.status_code == 409 and why in r.json()["reason"], (bad, r.json())
    assert client.post("/api/lists/nothing/entries", json={"key": "A", "word": {"en": "A"}, "step_id": "l-x"}).status_code == 409


def test_a_retired_entry_stays_readable_but_is_no_longer_offered(tmp_path):
    root, cfg = _world(tmp_path)
    client = _client(root, cfg)
    sign_in(client)
    assert client.post("/api/lists/label/entries", json={"key": "POD", "status": "retired", "step_id": "r-1"}).status_code == 200
    lst = next(l for l in client.get("/api/lists").json()["lists"] if l["id"] == "label")
    pod = next(e for e in lst["entries"] if e["key"] == "POD")
    assert pod["status"] == "retired" and pod["word"] == "Podcast episode" and pod["cases"] >= 1
    v = client.get("/api/cases/POD-110-the-silent-failure").json()
    assert v["label_word"] == "Podcast episode" and v["tint"] == "#e0a52a"
    c = DomainConfig.load(cfg, root)
    with pytest.raises(value_lists.ListError):
        value_lists.validate_choice(c.lists, {"label": "POD"})
    assert value_lists.validate_choice(c.lists, {"label": "FN", "series": "GH"}) == {"label": "FN", "series": "GH"}


# ----------------------------------------------------------------------------- a list nobody configured
def test_a_list_no_configuration_knows_is_started_filled_and_offered_to_a_new_case(tmp_path):
    root, cfg = _world(tmp_path, theme_extra={"create": {"label": "FN", "roles": ["author"]}})
    client = _client(root, cfg)
    sign_in(client, "akhil")
    assert client.post("/api/lists", json={"id": "channel", "word": {"en": "Channel"}, "field": "channel", "on_create": True, "step_id": "c-0"}).status_code == 403
    sign_in(client, "chris")
    for bad in ({"id": "Bad Id", "field": "x"}, {"id": "dup", "field": "series"}, {"id": "core", "field": "title"}, {"id": "noname", "field": "noname", "word": {}}):
        r = client.post("/api/lists", json={"word": {"en": "x"}, **bad, "step_id": f"c-bad-{bad['id'].replace(' ', '')}"})
        assert r.status_code == 409, bad
    r = client.post("/api/lists", json={"id": "channel", "word": {"de": "Kanal", "en": "Channel"}, "field": "channel", "on_create": True, "step_id": "c-1"})
    assert r.status_code == 200, r.text and r.json()["list"]["entries"] == []
    for i, (key, de, en, status) in enumerate([("LI", "LinkedIn", "LinkedIn", "active"), ("SUB", "Substack", "Substack", "planned"), ("FAX", "Fax", "Fax", "retired")]):
        assert client.post("/api/lists/channel/entries", json={"key": key, "word": {"de": de, "en": en}, "status": status, "step_id": f"c-e{i}"}).status_code == 200
    conf = client.get("/api/config").json()
    channel = next(l for l in conf["lists"] if l["id"] == "channel")
    assert channel["on_create"] and channel["field"] == "channel" and [e["key"] for e in channel["entries"]] == ["LI", "SUB", "FAX"]
    r = client.post("/api/cases", json={"title": "A post on gates", "values": {"channel": "SUB", "series": "GH"}, "step_id": "n-1"})
    assert r.status_code == 200, r.text
    meta = json.loads((root / r.json()["stage"] / r.json()["id"] / "meta.json").read_text())
    assert meta["channel"] == "SUB" and meta["series"] == "GH" and meta["label"] == "FN"
    assert client.post("/api/cases", json={"title": "Old way", "values": {"channel": "FAX"}, "step_id": "n-2"}).status_code == 409
    assert client.post("/api/cases", json={"title": "Unknown", "values": {"colour": "X"}, "step_id": "n-3"}).status_code == 409
    r = client.post("/api/cases", json={"title": "A podcast", "values": {"label": "POD"}, "step_id": "n-4"})
    assert r.json()["id"].startswith("POD-")
    # the list lives on in a fresh load of the same tree, and counts its case
    c = DomainConfig.load(cfg, root)
    assert value_lists.entry(c.lists, "channel", "LI")["word"]["de"] == "LinkedIn"
    assert value_lists.counts(FsStore(root), c.lists)["channel"] == {"SUB": 1}
