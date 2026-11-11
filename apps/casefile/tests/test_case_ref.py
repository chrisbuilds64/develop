"""A case's reference (REQ-001 S-20, SW-2026-023): one spelling, built by the core, shown where the theme says.

The reference is what people say on the phone: the external number, else label and number, else the id without its slug.
The theme's `case_ref.show` names the places (list, board, head); without it, all three."""

import json

from fastapi.testclient import TestClient

from casefile.api import views
from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.store import FsStore

from .world import CONFIG, build


def _world(tmp_path, theme_extra=None):
    root = build(tmp_path / "flow")
    cfg = root.parent / "config"
    if theme_extra is not None:
        theme = json.loads((cfg / "theme.json").read_text())
        (cfg / "theme.json").write_text(json.dumps({**theme, **theme_extra}))
    return root, cfg


def _card(root, cfg, cid):
    c = DomainConfig.load(cfg, root)
    return views.card(c, reading.load(FsStore(root), c, cid), "chris", "en")


def test_the_reference_is_label_and_number(tmp_path):
    root, cfg = _world(tmp_path)
    assert _card(root, cfg, "POD-110-the-silent-failure").ref == "POD-110"


def test_an_external_number_wins(tmp_path):
    root, cfg = _world(tmp_path)
    meta = root / "40-asset-generation" / "POD-110-the-silent-failure" / "meta.json"
    m = json.loads(meta.read_text())
    meta.write_text(json.dumps({**m, "external_id": "KS-4711"}))
    assert _card(root, cfg, "POD-110-the-silent-failure").ref == "KS-4711"


def test_without_a_number_the_id_loses_its_slug(tmp_path):
    root, cfg = _world(tmp_path)
    meta = root / "10-ideas" / "FN-101-the-quiet-audit" / "meta.json"
    m = json.loads(meta.read_text())
    m.pop("number", None)
    meta.write_text(json.dumps(m))
    assert _card(root, cfg, "FN-101-the-quiet-audit").ref == "FN-101"


def test_a_year_number_keeps_its_year():
    assert views.reference("SW-2026-023-kennung-der-akte", "SW", "2026-023", "") == "SW-2026-023"
    assert views.reference("SW-2026-023-kennung-der-akte", "SW", "", "") == "SW-2026-023"
    assert views.reference("plain", "", "", "") == "plain"


def test_the_theme_places_the_reference_and_defaults_to_everywhere(tmp_path):
    root, cfg = _world(tmp_path)
    assert views.config_view(DomainConfig.load(cfg, root), "en").case_ref == ["list", "board", "head"]
    root2, cfg2 = _world(tmp_path / "b", {"case_ref": {"show": ["head", "nowhere"]}})
    assert views.config_view(DomainConfig.load(cfg2, root2), "en").case_ref == ["head"]
    root3, cfg3 = _world(tmp_path / "c", {"case_ref": {"show": []}})
    assert views.config_view(DomainConfig.load(cfg3, root3), "en").case_ref == []


def test_the_api_carries_the_reference_on_every_card_and_the_places_in_the_config(tmp_path):
    root, cfg = _world(tmp_path, {"case_ref": {"show": ["head"]}})
    client = TestClient(create_app(Settings(root=root, config_dir=cfg, lang="en", secret="test")))
    assert client.post("/api/session", json={"person": "chris"}).status_code == 200
    assert client.get("/api/config").json()["case_ref"] == ["head"]
    cards = [c for g in client.get("/api/cases").json() for c in g["cases"]]
    assert cards and all(c["ref"] for c in cards)
    assert {c["id"]: c["ref"] for c in cards}["POD-110-the-silent-failure"] == "POD-110"
