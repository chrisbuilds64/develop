"""turn(): a table over the sample world. Every row: case → (actor, action, blocked) of the main turn, plus the others."""

import pytest

from casefile.domain import cases, turn as whose

TABLE = [
    # case id                              main actor        main action          blocked contains        other actors
    ("FN-101-the-quiet-audit",             "role:author",    "work_out",          [],                     []),
    ("POD-102-the-handoff",                "role:author",    "work_out",          [],                     []),
    ("FN-103-what-the-pilot-taught",       "claude",         "wait",              [],                     []),
    ("WN-104-notes-on-friction",           "role:operator",  "see_failure",       [],                     ["role:author"]),
    ("FN-105-the-review-that-reads-itself","role:approver",  "approve_to_visual", [],                     ["role:approver"]),
    ("FN-106-two-models-agreeing",         "chris",          "answer",            [],                     ["akhil", "role:approver", "role:approver"]),
    ("SP-107-written-by-chris",            "role:approver",  "approve_to_visual", [],                     ["role:approver"]),   # Sam may still approve; Chris may not (per person); the second turn is "rework"
    ("FN-108-missing-draft",               "role:approver",  "approve_to_visual", ["substack.md"],        ["role:approver"]),
    ("SP-109-the-intern",                  "role:visual",    "deliver",           ["shape:image"],        []),
    ("POD-110-the-silent-failure",         "role:approver",  "approve_visual",    [],                     []),
    ("FN-111-the-boring-win",              "role:approver",  "schedule",          [],                     []),
    ("SP-112-the-handover-note",           "role:approver",  "published",         [],                     []),
    ("FN-113-the-first-arc",               None,             None,                [],                     []),
    ("SP-114-one-file-per-decision",       None,             None,                [],                     []),
    ("SP-115-the-fourth-reviewer",         "claude",         "wait",              [],                     []),
    ("OBS-117-a-signal",                   "role:author",    "work_out",          [],                     []),
    ("FN-118-old",                         None,             None,                [],                     []),
    ("WN-119-weekend",                     "role:approver",  "approve_to_visual", [],                     ["role:approver"]),
]


@pytest.mark.parametrize("cid,actor,action,blocked,others", TABLE, ids=[r[0] for r in TABLE])
def test_whose_move(store, config, cid, actor, action, blocked, others):
    case = cases.load(store, config, cid)
    turns = whose.turn(case, config)
    if actor is None:
        assert turns == [], turns
        return
    main = turns[0]
    assert (main.actor, main.action) == (actor, action), turns
    for b in blocked:
        assert any(b in x for x in main.blocked_by), main.blocked_by
    assert [t.actor for t in turns[1:]] == others, turns


def test_labels_come_from_the_vocabulary_in_both_languages(store, config):
    case = cases.load(store, config, "FN-105-the-review-that-reads-itself")
    assert whose.turn(case, config, "de")[0].label == "Freigeben und an Akhil schicken"
    assert whose.turn(case, config, "en")[0].label == "Approve and send to Akhil"


def test_four_eyes_is_decided_per_person(store, config):
    """The primary of SP-107 was written by Chris. The role may approve (Sam), Chris may not."""
    case = cases.load(store, config, "SP-107-written-by-chris")
    main = whose.turn(case, config)[0]
    assert main.blocked_by == []                                   # Sam is an approver too
    assert whose.primary_author(config, case) == "chris"
    # with Sam gone, the role collapses to Chris and the block appears in the turn
    config.people = [p for p in config.people if p.id != "sam"]
    main = whose.turn(case, config)[0]
    assert any("four eyes" in b for b in main.blocked_by)


def test_my_move_list_resolves_roles_to_persons(store, config):
    all_cases = cases.load_all(store, config)
    mine = whose.turns_for("akhil", all_cases, config)
    ids = {(c.id, t.action) for c, t in mine}
    assert ("SP-109-the-intern", "deliver") in ids
    assert ("FN-106-two-models-agreeing", "answer") in ids
    assert ("FN-105-the-review-that-reads-itself", "approve_to_visual") not in ids
    chris = {(c.id, t.action) for c, t in whose.turns_for("chris", all_cases, config)}
    assert ("FN-105-the-review-that-reads-itself", "approve_to_visual") in chris
    assert ("WN-104-notes-on-friction", "see_failure") in chris
    assert ("FN-101-the-quiet-audit", "work_out") in chris


def test_an_unknown_stage_is_nobodys_move(store, config):
    (store.root / "25-x").mkdir()
    (store.root / "25-x" / "FN-120-odd").mkdir()
    case = cases.load(store, config, "FN-120-odd")
    assert whose.turn(case, config) == []


def test_a_case_without_meta_still_loads(store, config):
    (store.root / "30-review-human" / "nameless").mkdir()
    case = cases.load(store, config, "nameless")
    assert case.label == "nameless" and all(not s.present for s in case.slots)
    assert whose.turn(case, config)[0].action == "approve_to_visual"
