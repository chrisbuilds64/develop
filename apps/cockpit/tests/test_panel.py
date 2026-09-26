"""The panel contract: a card shows numbers only when shape and freshness both hold."""

import datetime as dt

from cockpit.panel import evaluate, is_stale, now_iso, shape_errors


def good():
    return {
        "panel": "worklist", "title": "worklist.title", "maturity": "running",
        "as_of": now_iso(), "state": "ok",
        "headline": {"value": 3, "unit": "worklist.open"},
        "lines": [{"label": "worklist.blocked", "value": 0, "tone": "muted"}],
        "source": "todo.json",
    }


def test_a_good_panel_is_shown():
    assert evaluate("worklist", good(), 24).shown


def test_an_unknown_field_is_refused_define_it_first():
    p = good(); p["extra"] = 1
    errs = shape_errors(p)
    assert any("unknown field 'extra'" in e for e in errs)
    assert evaluate("worklist", p, 24).verdict == "invalid"


def test_more_than_five_lines_is_refused():
    p = good(); p["lines"] = [p["lines"][0]] * 6
    assert evaluate("worklist", p, 24).verdict == "invalid"


def test_a_fourth_state_is_refused():
    p = good(); p["state"] = "fine"
    assert evaluate("worklist", p, 24).verdict == "invalid"


def test_missing_source_is_refused():
    p = good(); del p["source"]
    assert evaluate("worklist", p, 24).verdict == "invalid"


def test_an_old_reading_is_stale_not_shown():
    p = good()
    p["as_of"] = (dt.datetime.now().astimezone() - dt.timedelta(hours=30)).isoformat(timespec="seconds")
    card = evaluate("worklist", p, 24)
    assert card.verdict == "stale" and not card.shown


def test_staleness_respects_the_limit():
    old = (dt.datetime.now().astimezone() - dt.timedelta(hours=30)).isoformat(timespec="seconds")
    assert is_stale(old, 24) and not is_stale(old, 48)
