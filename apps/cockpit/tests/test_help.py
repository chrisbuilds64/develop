"""Help for the page: anchors in the markup and topics in the catalogs stay in step — the check is the guarantee."""

import json

from cockpit import help as page_help


def test_the_shipped_help_matches_the_screen():
    assert page_help.check() == []                       # this is the gate the deploy runs too


def test_an_anchor_without_a_topic_and_a_topic_without_an_anchor_are_both_findings(tmp_path, monkeypatch):
    (tmp_path / "page.html").write_text('<nav data-help="x.menu"></nav><div data-help="x.desk"></div>')
    (tmp_path / "app.tsx").write_text('<b {...(on ? { "data-help": "x.flag" } : {})} />')
    cat = tmp_path / "x.json"
    cat.write_text(json.dumps({"surface": "x", "topics": [
        {"key": "x.menu", "since": "1.0.0", "title": {"de": "Menü", "en": "Menu"}, "text": {"de": "…", "en": "…"}},
        {"key": "x.flag", "since": "1.0.0", "title": {"de": "Flagge", "en": "Flag"}, "text": {"de": "…"}},
        {"key": "x.gone", "title": {"de": "Weg", "en": "Gone"}, "text": {"de": "…", "en": "…"}}]}))
    monkeypatch.setattr(page_help, "sources", lambda: [tmp_path / "page.html", tmp_path / "app.tsx"])
    monkeypatch.setattr(page_help, "catalogs", lambda: [cat])
    found = page_help.check()
    assert "anchor 'x.desk' (page.html) has no help topic" in found
    assert "help topic 'x.gone' (x) has no anchor on any page" in found
    assert "help topic 'x.gone' has no 'since' version" in found
    assert "help topic 'x.flag' has no en title or text" in found
    assert len(found) == 4


def test_the_panel_gets_the_help_in_the_persons_language():
    from tests.test_workspaces import FIX  # noqa: F401 — the fixtures exist
    de, en = page_help.view("de"), page_help.view("en")
    assert {t["key"] for t in de["topics"]} == {t["key"] for t in en["topics"]} and "cf.desk" in {t["key"] for t in de["topics"]}
    assert "Schreibtisch" in page_help.as_text("de", ["cf.desk"]) and "Muster" not in page_help.as_text("de", ["cf.desk"])


def test_a_menu_row_or_action_without_an_anchor_is_a_finding_unless_it_says_why(tmp_path, monkeypatch):
    (tmp_path / "base.html").write_text(
        '<a href="/" class="nav-row{% if on %} on{% endif %}" title="x">Home</a>\n'
        '<a class="nav-row" data-help="x.ok">Ok</a>\n'
        '<a class="nav-row ws-row" data-help-skip="explained by x.ok">Row</a>\n'
        '<div class="card">no rule for this</div>\n')
    (tmp_path / "Menu.tsx").write_text(
        '<button type="button" className={`nav-row${a ? " on" : ""}`} onClick={() => go("/")}>Go</button>\n'
        '<div className="views" role="tablist">\n')
    monkeypatch.setattr(page_help, "sources", lambda: [tmp_path / "base.html", tmp_path / "Menu.tsx"])
    assert page_help.unanchored() == [
        "base.html:1: a 'nav-row' without data-help (or data-help-skip=\"why\")",
        "Menu.tsx:1: a 'nav-row' without data-help (or data-help-skip=\"why\")",
        "Menu.tsx:2: a 'views' without data-help (or data-help-skip=\"why\")"]
