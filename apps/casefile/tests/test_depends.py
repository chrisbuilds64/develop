"""Dependencies between cases (REQ-005 DP-01 to DP-05): a case may wait for others, here and in a connected instance."""

import json

from casefile.config import DomainConfig
from casefile.domain import cases, depends, step as stepping
from casefile.domain import entries as thread
from casefile.models import StepRequest
from casefile.store import FsStore

from .world import build

A = "FN-105-the-review-that-reads-itself"
B = "FN-106-two-models-agreeing"
C = "FN-101-the-quiet-audit"
OLD = "FN-118-old"                      # stands in 00-archive: closed


def wait(store, config, case, refs, sid, resolve=None):
    return stepping.step(store, config, case, StepRequest(action="wait_for", step_id=sid, payload={"refs": refs}), "chris", resolve)


def other(tmp_path, store):
    """A second instance, connected to the first under 'other' (today through targets.json, ADR-022)."""
    root2 = build(tmp_path / "other" / "flow")
    store.write_json("targets.json", {"other": {"root": str(root2), "config": str(root2.parent / "config")}})
    return FsStore(root2), DomainConfig.load(root2.parent / "config", root2)


def test_a_case_waits_for_cases_in_other_instances(tmp_path, store, config):
    st2, cfg2 = other(tmp_path, store)
    r = wait(store, config, A, [B, f"other:{OLD}"], "w1")
    assert r.ok and r.to is None and store.find(A) == "30-review-human"                 # nothing moved
    assert store.case_json(A, "meta.json")["waitsFor"] == [B, f"other:{OLD}"]
    e = thread.parse(store.case_text(A, "review.md"))[-1]
    assert e.step == "w1" and B in e.text and "other:" in e.text
    deps = depends.waits(store.case_json(A, "meta.json"), depends.resolver_for(store, config), "en")
    assert [(d.instance, d.case, d.found, d.closed) for d in deps] == [("", B, True, False), ("other", OLD, True, True)]
    assert deps[0].title == "Two models agreeing" and deps[0].stage_word


def test_closing_the_last_dependency_releases_but_does_not_move(store, config):
    assert wait(store, config, A, [OLD, B], "w1").ok
    resolve = depends.resolver_for(store, config)
    assert not depends.released(depends.waits(store.case_json(A, "meta.json"), resolve, "en"))
    store.move(B, "00-archive")                                                         # B closes
    deps = depends.waits(store.case_json(A, "meta.json"), resolve, "en")
    assert depends.released(deps)
    assert store.find(A) == "30-review-human"                                           # released, not moved
    assert not depends.released([])                                                     # waiting for nothing is not "released"


def test_a_dependency_must_exist_and_be_visible(store, config):
    r = wait(store, config, A, ["FN-999-nothing"], "w1")
    assert not r.ok and "does not exist" in r.reason
    r = wait(store, config, A, ["elsewhere:FN-101-the-quiet-audit"], "w2")
    assert not r.ok and "not connected" in r.reason                                     # an instance we cannot reach: may not see it
    r = wait(store, config, A, [A], "w3")
    assert not r.ok and "itself" in r.reason
    assert "waitsFor" not in store.case_json(A, "meta.json")


def test_a_circle_is_refused(store, config):
    assert wait(store, config, A, [B], "w1").ok
    assert wait(store, config, B, [C], "w2").ok
    r = wait(store, config, C, [A], "w3")                                               # C → A → B → C
    assert not r.ok and "circle" in r.reason
    assert "waitsFor" not in store.case_json(C, "meta.json")


def test_an_empty_list_ends_the_waiting_and_the_view_shows_it(store, config):
    from casefile.api import views
    assert wait(store, config, A, [B], "w1").ok
    v = views.view(config, cases.load(store, config, A), "chris", "en", lambda c, n: n, None, store)
    assert [d.case for d in v.waits] == [B] and not v.released
    assert wait(store, config, A, [], "w2").ok
    assert "waitsFor" not in store.case_json(A, "meta.json")
    assert not wait(store, config, A, [], "w3").ok                                      # nothing changed: refused
    v = views.view(config, cases.load(store, config, A), "chris", "en", lambda c, n: n, None, store)
    assert v.waits == [] and not v.released


def test_the_same_wait_for_twice_is_a_no_op(store, config):
    assert wait(store, config, A, [B], "w1").ok
    again = wait(store, config, A, [B, C], "w1")                                        # same step id
    assert again.ok and store.case_json(A, "meta.json")["waitsFor"] == [B]
    assert json.loads(store.read_text("_steps/w1.json"))["status"] == "done"
