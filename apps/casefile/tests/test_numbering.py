"""A new case is numbered by its domain's rule: within a year, within a series, or as a placeholder until it is numbered."""

import datetime as dt

from casefile.domain import numbering
from casefile.store import FsStore


def tree(tmp_path, *ids):
    for i in ids:
        (tmp_path / "10-ideas" / i).mkdir(parents=True)
    return FsStore(tmp_path)


def test_a_claim_counts_within_its_year(tmp_path):
    y = dt.date.today().year
    store = tree(tmp_path, f"HR-{y}-0417-wasser", f"HR-{y}-0002-x", "HR-2019-0999-alt")
    assert numbering.next_number(store, "HR", ["{year}-{seq:04}"], {}) == f"{y}-0418"


def test_a_piece_of_a_series_counts_within_the_series(tmp_path):
    store = tree(tmp_path, "FN-SIM-01-a", "FN-SIM-02-b", "FN-RT-07-c")
    rule = ["{series}-{seq:02}", "xxx"]
    assert numbering.next_number(store, "FN", rule, {"series": "SIM"}) == "SIM-03"
    assert numbering.next_number(store, "FN", rule, {"series": "GH"}) == "GH-01"
    assert numbering.next_number(store, "FN", rule, {}) == "xxx"               # no series: the placeholder until it is numbered


def test_without_a_rule_the_old_numbering_holds(tmp_path):
    y = dt.date.today().year
    assert numbering.next_number(tree(tmp_path, f"ERH-{y}-03-x"), "ERH", None, {}) == f"{y}-04"
