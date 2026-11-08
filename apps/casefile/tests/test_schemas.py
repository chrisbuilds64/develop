"""A new kind of case from Setup must not cost the workspace the kinds it already has (review of the design hand-back,
2026-11-08, B1): a tree without its own artifacts.json reads the domain's, and the first kind added there used to start
the tree's file from nothing — after the next load every other format and `common` were gone."""

import json
import shutil

import pytest

from casefile.config import DomainConfig
from casefile.domain import schemas
from casefile.store import FsStore

from .world import CONFIG, build


def _empty_tree(tmp_path):
    """A workspace started from configuration: the domain carries artifacts.json, the tree has none of its own."""
    root = build(tmp_path / "flow")
    cfg = root.parent / "config"
    for name in ("artifacts.json", "lists.json"):
        shutil.copy(CONFIG / name, cfg / name)
    (root / "artifacts.json").unlink()
    return root, cfg


def test_a_new_kind_in_a_tree_without_its_own_file_keeps_every_kind_after_the_next_load(tmp_path):
    root, cfg = _empty_tree(tmp_path)
    config = DomainConfig.load(cfg, root)
    before = json.loads((cfg / "artifacts.json").read_text())
    schemas.add(FsStore(root), config, "chris", "XX", {"de": "Neu", "en": "New"}, "FN", "s-1")
    again = DomainConfig.load(cfg, root)
    assert set(again.artifacts["formats"]) == set(before["formats"]) | {"XX"}
    assert again.artifacts.get("common") == before.get("common")
    assert again.artifacts["formats"]["XX"] == before["formats"]["FN"]


def test_a_tree_file_that_cannot_be_read_is_not_written_over(tmp_path):
    root, cfg = _empty_tree(tmp_path)
    config = DomainConfig.load(cfg, root)
    (root / "artifacts.json").write_text("{ not json")
    with pytest.raises(schemas.SchemaError):
        schemas.add(FsStore(root), config, "chris", "XX", {"de": "Neu", "en": "New"}, "FN", "s-1")
    assert (root / "artifacts.json").read_text() == "{ not json"
