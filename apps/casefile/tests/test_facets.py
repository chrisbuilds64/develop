"""Facets (domain/facets.py): filter, sort and card chips from every application's own configuration."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import facets

CONFIGS = Path(__file__).resolve().parents[1] / "config"


def by_key(fs):
    return {f["key"]: f for f in fs}


@pytest.mark.parametrize("domain", sorted(p.name for p in CONFIGS.iterdir() if (p / "stages.json").exists()))
def test_every_application_gets_facets_from_its_configuration(domain):
    cfg = DomainConfig.load(CONFIGS / domain, None)
    fs = by_key(facets.facets(cfg, "en"))
    assert fs["stage"]["filter"] and [v["key"] for v in fs["stage"]["values"]] == [s.folder for s in cfg.stages]
    for lst in cfg.lists.values():
        assert lst["field"] in fs, f"{domain}: list {lst['id']} has no facet"


def test_defaults_by_kind_and_a_view_overrides_them():
    cfg = DomainConfig.load(CONFIGS / "worklist", None)
    fs = by_key(facets.facets(cfg, "de"))
    assert (fs["priority"]["filter"], fs["priority"]["sort"], fs["priority"]["card"]) == (True, True, True)
    assert fs["assignee"]["kind"] == "person" and {v["key"] for v in fs["assignee"]["values"]} >= {"chris", "akhil"}
    assert fs["due"]["kind"] == "date" and not fs["due"]["filter"] and fs["due"]["sort"]
    assert fs["origin_kind"]["filter"] and not fs["origin_kind"]["card"]        # theme.fields.origin_kind.view
    assert "origin_ref" not in fs and "title" not in fs                         # text: no filter, no sort, no card
    assert fs["priority"]["word"] == "Wichtigkeit"


def test_a_card_carries_its_values_and_the_config_its_facets(tmp_path):
    root = tmp_path / "tree"
    for s in ("10-backlog", "20-next", "30-doing", "40-waiting", "90-done"):
        (root / s).mkdir(parents=True)
    c = TestClient(create_app(Settings(root=root, config_dir=CONFIGS / "worklist", lang="en", secret="t", identity=lambda r: "chris", web_dist=None)))
    r = c.post("/api/cases", json={"title": "Try facets", "step_id": "f-1", "values": {"label": "SYS", "priority": "high", "assignee": "akhil", "due": "2026-11-30"}})
    assert r.status_code == 200, r.text
    card = next(x for s in c.get("/api/stages").json() for x in s["cases"])
    assert card["values"] == {"label": "SYS", "priority": "high", "assignee": "akhil", "due": "2026-11-30", "stage": "10-backlog"}
    keys = [f["key"] for f in c.get("/api/config").json()["facets"]]
    assert keys[:3] == ["label", "priority", "origin_kind"] and "stage" in keys and "data_point" not in keys
