"""A tree's own vocabulary adds to its domain's: the words it names win, the ones it leaves out still come from the domain."""

import json
from pathlib import Path

from casefile.config import DomainConfig

CFG = Path(__file__).resolve().parents[1] / "config"


def test_a_tree_vocabulary_overrides_without_erasing(tmp_path):
    (tmp_path / "vocabulary.json").write_text(json.dumps({"de": {"product": "Mein PressRoom", "groups": {"you": "Dran"}}}))
    v = DomainConfig.load(CFG / "pressroom", tmp_path).vocabulary["de"]
    assert v["product"] == "Mein PressRoom" and v["groups"]["you"] == "Dran"
    assert v["groups"]["others"] == "Bei anderen" and v["meta"]["publishDate"] == "Veröffentlicht am"
