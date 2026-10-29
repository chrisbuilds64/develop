"""The stack (ADR-024): every move has a kind, a headline and, when blocked, a lock sentence; the list of what waits for a person
follows the stack's rule — a date first, then gates with a seal, gates without, moves that wait for something, then nudges."""

from casefile.domain import cases, turn as whose


def main(store, config, cid, lang=None):
    case = cases.load(store, config, cid)
    return whose.enrich(case, whose.turn(case, config, lang), config, lang)[0]


def test_every_move_has_a_kind(store, config):
    assert main(store, config, "FN-105-the-review-that-reads-itself").kind == "seal"     # approve_to_visual carries a seal
    assert main(store, config, "FN-108-missing-draft").kind == "gap"                     # the same gate, but the draft is missing
    assert main(store, config, "FN-111-the-boring-win").kind == "gate"                   # schedule moves the stage, no seal
    assert main(store, config, "FN-106-two-models-agreeing").kind == "gate"              # a question addressed to Chris
    assert main(store, config, "FN-101-the-quiet-audit").kind == "nudge"                 # work_out starts a helper, moves nothing
    assert main(store, config, "FN-103-what-the-pilot-taught").kind == "nudge"           # waiting for a helper is nobody's gate


def test_headline_and_lock_come_from_the_vocabulary(store, config):
    t = main(store, config, "FN-108-missing-draft", "de")
    assert t.headline.startswith("Text freigeben: ")
    assert "öffnet sich, sobald" in t.lock and "Entwurf" in t.lock                       # 'substack.md' is the primary → its word
    free = main(store, config, "FN-105-the-review-that-reads-itself", "de")
    assert free.lock == ""                                                               # nothing blocks: no lock sentence
    assert main(store, config, "FN-101-the-quiet-audit", "en").headline.startswith("Work it out: ")


def test_the_stack_follows_the_rule(store, config):
    kinds = [t.kind for _, t in whose.turns_for("chris", cases.load_all(store, config), config)]
    order = {k: i for i, k in enumerate(whose.ORDER)}
    assert kinds == sorted(kinds, key=order.__getitem__)                                 # never a nudge before a gate
    assert kinds[0] in ("date", "seal", "gate")


def test_a_date_puts_a_case_first(store, config):
    case = cases.load(store, config, "FN-111-the-boring-win")
    case.meta["publishDate"] = "2026-11-03"
    t = whose.enrich(case, whose.turn(case, config), config)[0]
    assert t.kind == "date" and t.date == "2026-11-03"


def test_the_order_can_be_configured(store, config):
    config.order = ["nudge", "gate", "seal", "gap", "date"]
    kinds = [t.kind for _, t in whose.turns_for("chris", cases.load_all(store, config), config)]
    assert kinds and kinds[0] == "nudge"
    config.order = []
