"""REQ-001 A-06: a helper's question offers its numbered choices as buttons. A choice in the words of a move the case offers
the viewer right now makes that move; any other sends the same helper again with that choice; where no helper can be sent,
the choice is the answer. Each resolves the question. Matched by the button words in any language of the application, so
nothing in the thread carries an id. Played on Shipyard here; nothing in the core knows Shipyard."""

import json

from casefile.api import views
from casefile.domain import cases as reading
from casefile.domain import choices
from casefile.domain import entries as thread
from casefile.domain import step as stepping
from casefile.models import StepRequest

from .test_shipyard import CID, Steps, pass_protocol, world


def ask(store, config, text, by="axel", for_="Chris"):
    r = stepping.step(store, config, CID, StepRequest(action="note", step_id=f"q{abs(hash(text)) % 10**8}", payload={"text": text, "for": for_, "title": "A decision"}), by)
    assert r.ok, r.reason
    return r.entry


def built(tmp_path):
    """The build helper finished and left the case in the build: it hands a decision back."""
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "chris")
    f = root / "_runs" / f"{r.run}.json"
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": "done", "finished": "2026-11-11T20:00:00+01:00"}))
    return root, store, config, go, r.run


def in_approval(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    assert go("accept_task", "chris").ok
    go.deliver(root, "pr.md", "axel", "https://example.org/pull/4")
    assert go("open_pr", "axel").ok
    go.deliver(root, "checks.md", "axel")
    assert go("checks_green", "axel").ok
    for f in (root / "_runs").glob("*.json"):                                    # every helper done: the product owner's turn
        f.write_text(json.dumps({**json.loads(f.read_text()), "status": "done"}))
    return root, store, config, go


def test_numbered_lines_are_the_choices_and_one_line_is_none():
    text = "Two ways are open.\n\n- the walk is red\n\n1. Keep the words — nothing changes\n2) Use the **shorter** words\n3. Ask the team first\n"
    assert choices.parse(text) == ["Keep the words — nothing changes", "Use the **shorter** words", "Ask the team first"]
    assert choices.parse("Just a question.\n\n1. only one\n") == []
    assert choices.parse("No list at all.") == []
    assert choices.head("Keep the words — nothing changes") == "Keep the words"
    assert choices.head("Use the **shorter** words: they fit") == "Use the shorter words"


def test_a_choice_that_is_not_a_move_sends_the_same_helper_again_with_it(tmp_path):
    root, store, config, go, first = built(tmp_path)
    q = ask(store, config, "Which words should the button carry?\n\n1. Keep the words as they are\n2. Use the shorter words\n3. Leave the button out")
    case = reading.load(store, config, CID)
    opts = choices.options(config, case, next(e for e in case.entries if e.id == q), "chris")
    assert [o.label for o in opts] == ["Keep the words as they are", "Use the shorter words", "Leave the button out"]
    assert {o.kind for o in opts} == {"again"}                                # the developer's stage: Chris has no move here
    r = stepping.step(store, config, CID, StepRequest(action="choose", step_id="c1", payload={"resolves": q, "choice": 2}), "chris")
    assert r.ok, r.reason
    run = json.loads((root / "_runs" / f"{r.run}.json").read_text())
    assert (run["skill"], run["again_after"]) == ("shipyard-build", first)
    assert run["note"].endswith("Chris: Use the shorter words")
    case = reading.load(store, config, CID)
    assert q in thread.resolved_ids(case.entries) and not thread.open_for(case.entries, "Chris")


def test_a_choice_in_the_words_of_the_viewer_s_move_makes_that_move_in_any_language(tmp_path):
    root, store, config, go = in_approval(tmp_path)
    q = ask(store, config, "The walk is red on the phone width.\n\n1. Send it back to the build — the walk must pass first\n2. Look at it myself first")
    case = reading.load(store, config, CID)
    opts = choices.options(config, case, next(e for e in case.entries if e.id == q), "chris")
    assert [(o.kind, o.action) for o in opts] == [("move", "send_back"), ("answer", "")]   # no helper ran here: the second is an answer
    r = stepping.step(store, config, CID, StepRequest(action="choose", step_id="c2", payload={"resolves": q, "choice": 1}), "chris")
    assert r.ok, r.reason
    assert (r.action, r.to) == ("send_back", "20-build") and r.run
    case = reading.load(store, config, CID)
    moved = next(e for e in case.entries if e.id == r.entry)
    assert moved.resolves == q and "the walk must pass first" in moved.text
    assert not thread.open_for(case.entries, "Chris")
    note = json.loads((root / "_runs" / f"{r.run}.json").read_text())["note"]
    assert "Send it back to the build" in note                                   # the build helper learns why

    _, store2, config2, _ = in_approval(tmp_path / "de")
    q2 = ask(store2, config2, "Der Rundgang ist rot.\n\n1. Zurück in die Umsetzung schicken\n2. Erst selbst ansehen")
    case2 = reading.load(store2, config2, CID)
    assert choices.options(config2, case2, next(e for e in case2.entries if e.id == q2), "chris")[0].action == "send_back"


def test_the_answer_choice_answers_and_a_move_another_holds_is_not_offered(tmp_path):
    root, store, config, go = in_approval(tmp_path)
    q = ask(store, config, "Merge now?\n\n1. Merge\n2. Look at it myself first")
    case = reading.load(store, config, CID)
    entry = next(e for e in case.entries if e.id == q)
    assert choices.options(config, case, entry, "chris")[0].kind == "answer"   # merge waits for its protocol: blocked, not a button move
    assert choices.options(config, case, entry, "akhil")[0].kind == "answer"   # not Akhil's move at all
    r = stepping.step(store, config, CID, StepRequest(action="choose", step_id="c3", payload={"resolves": q, "choice": 2}), "chris")
    assert r.ok and r.action == "answer"
    case = reading.load(store, config, CID)
    assert next(e for e in case.entries if e.id == r.entry).text == "Look at it myself first"
    assert case.stage == "40-approval"


def test_a_question_without_choices_or_answered_already_refuses_a_choice(tmp_path):
    root, store, config, go, _ = built(tmp_path)
    q = ask(store, config, "Is the title right?")
    case = reading.load(store, config, CID)
    assert choices.options(config, case, next(e for e in case.entries if e.id == q), "chris") == []
    bad = stepping.step(store, config, CID, StepRequest(action="choose", step_id="c4", payload={"resolves": q, "choice": 1}), "chris")
    assert not bad.ok
    q2 = ask(store, config, "Which?\n\n1. Keep it\n2. Change it")
    assert stepping.step(store, config, CID, StepRequest(action="done", step_id="d1", payload={"resolves": q2}), "chris").ok
    late = stepping.step(store, config, CID, StepRequest(action="choose", step_id="c5", payload={"resolves": q2, "choice": 1}), "chris")
    assert not late.ok and "answered" in late.reason
    nine = stepping.step(store, config, CID, StepRequest(action="choose", step_id="c6", payload={"resolves": q2, "choice": 9}), "chris")
    assert not nine.ok


def test_the_case_view_carries_the_choices_and_no_second_send_again(tmp_path):
    root, store, config, go, _ = built(tmp_path)
    case = reading.load(store, config, CID)
    assert views.again(config, case, "chris", "en") is not None
    q = ask(store, config, "Which words?\n\n1. Keep the words\n2. Use the shorter words\n3. Leave it out")
    v = views.view(config, reading.load(store, config, CID), "chris", "en", lambda c, n: n, store=store)
    assert [o.label for o in v.choices[q]] == ["Keep the words", "Use the shorter words", "Leave it out"]
    assert v.again is None                                                     # the choices take its place
