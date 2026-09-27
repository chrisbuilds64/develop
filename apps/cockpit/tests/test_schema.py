"""One checker for every document: same rules, same words, nested too."""

from cockpit.schema import check

SCHEMA = {
    "type": "object", "required": ["label", "title"], "additionalProperties": False,
    "properties": {
        "label": {"enum": ["FN", "POD"]}, "title": {"type": "string", "minLength": 1},
        "created": {"type": ["string", "null"], "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "guests": {"type": "array", "items": {"$ref": "#/$defs/guest"}},
    },
    "$defs": {"guest": {"type": "object", "required": ["name"], "additionalProperties": False,
                        "properties": {"name": {"type": "string"}, "consent": {"type": "boolean"}}}},
}


def test_the_three_checks_that_matter_and_their_words():
    out = check({"label": "EP", "mood": "x"}, SCHEMA)
    assert "required field 'title' is missing" in out
    assert "label = 'EP' is not one of ['FN', 'POD']" in out
    assert "unknown field 'mood' — define it in the schema first" in out


def test_types_patterns_and_lengths_hold_in_nested_documents():
    doc = {"label": "FN", "title": "", "created": "27.09.2026",
           "guests": [{"name": "Ray", "consent": "yes"}, {"place": "Sydney"}]}
    out = check(doc, SCHEMA)
    assert "title: empty" in out
    assert any(x.startswith("created = '27.09.2026' does not match") for x in out)
    assert "guests[0].consent: expected boolean, got str" in out
    assert "guests[1]: required field 'name' is missing" in out
    assert "guests[1]: unknown field 'place' — define it in the schema first" in out
    assert check({"label": "FN", "title": "ok", "created": None, "guests": []}, SCHEMA) == []


def test_no_schema_means_nothing_to_say():
    assert check({"anything": 1}, None) == []


def test_a_deprecated_field_that_is_still_there_is_named():
    schema = {"type": "object", "properties": {"old": {"type": "string", "deprecated": True, "description": "use new"}, "new": {"type": "string"}}}
    assert check({"old": "x"}, schema) == ["field 'old' is deprecated — use new"]
    assert check({"new": "x"}, schema) == []
