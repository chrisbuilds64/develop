"""A move that exists only when a finding calls for it (`when`), and a follow-up order in the same workspace (target `self`):
the change file's deviation decision after PROD (DISC-044)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain.turn import turn
from casefile.store import FsStore

CONFIG = Path(__file__).resolve().parents[1] / "config" / "aenderungsakte"
STAGES = ["10-entw", "20-erfasst", "30-analysiert", "40-bereit", "50-test", "60-prod", "70-abgeschlossen"]
CASE = "AE-2026-0011-liefertermin"


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "flow"
    for st in STAGES:
        (root / st).mkdir(parents=True)
    shutil.copy(CONFIG / "people.json", root / "people.json")
    d = root / "60-prod" / CASE
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"label": "AE", "number": "2026-0011", "title": "Liefertermin zusagen"}), encoding="utf-8")
    (d / "prod.md").write_text("# PROD\n", encoding="utf-8")
    return root


def moves(root):
    store, config = FsStore(root), DomainConfig.load(CONFIG, root)
    return [t.action for t in turn(reading.load(store, config, CASE), config, "de")]


def test_without_a_finding_there_is_no_move_at_all(tree):
    assert moves(tree) == []


def test_a_finding_offers_both_decisions(tree):
    (tree / "60-prod" / CASE / "abweichung.md").write_text("# Abweichung\n", encoding="utf-8")
    assert moves(tree) == ["record_exception", "order_rework"]


def test_a_move_that_is_not_offered_is_refused(tree):
    client = TestClient(create_app(Settings(root=tree, config_dir=CONFIG, secret="x", recover_on_start=False)))
    client.post("/api/session", json={"person": "chris"})
    r = client.post(f"/api/cases/{CASE}/steps", json={"action": "record_exception", "step_id": "s1", "payload": {"note": "x"}})
    assert not r.json().get("ok") and "not offered" in r.text


def test_an_order_opens_a_new_change_in_the_same_workspace(tree):
    (tree / "60-prod" / CASE / "abweichung.md").write_text("# Abweichung\n\nApp 106 liest direkt.\n", encoding="utf-8")
    client = TestClient(create_app(Settings(root=tree, config_dir=CONFIG, secret="x", recover_on_start=False)))
    client.post("/api/session", json={"person": "chris"})
    r = client.post(f"/api/cases/{CASE}/steps", json={"action": "order_rework", "step_id": "s2", "payload": {"note": "umstellen"}})
    assert r.json()["ok"] and r.json()["to"] == "70-abgeschlossen"
    new = [p for p in (tree / "10-entw").iterdir() if p.is_dir()]
    assert len(new) == 1
    meta = json.loads((new[0] / "meta.json").read_text(encoding="utf-8"))
    assert meta["title"] == "Abweichung aus 2026-0011 beheben"
    assert "App 106" in (new[0] / "aenderung.md").read_text(encoding="utf-8")


def test_an_exception_is_sealed_with_its_reason(tree):
    (tree / "60-prod" / CASE / "abweichung.md").write_text("# Abweichung\n", encoding="utf-8")
    client = TestClient(create_app(Settings(root=tree, config_dir=CONFIG, secret="x", recover_on_start=False)))
    client.post("/api/session", json={"person": "chris"})
    r = client.post(f"/api/cases/{CASE}/steps", json={"action": "record_exception", "step_id": "s3", "payload": {"note": "App 106 liest nur."}})
    assert r.json()["ok"] and r.json()["to"] == "70-abgeschlossen"
    thread = (tree / "70-abgeschlossen" / CASE / "review.md").read_text(encoding="utf-8")
    assert "App 106 liest nur." in thread and "approved" in thread
    assert (tree / "70-abgeschlossen" / CASE / "abweichung.md").is_file()
