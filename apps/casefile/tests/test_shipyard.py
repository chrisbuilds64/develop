"""A software change through the way of CONTRIBUTING.md (REQ-002): task confirmed by the product owner, built and
checked by a developer, merged by the product owner (never by the author of the pull request), then ENTW, TEST and
PROD, each accepted by the product owner. The developer here is an agent; every gate is a person."""

import json
from pathlib import Path

from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import step as stepping
from casefile.domain.turn import turn as whose
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config" / "shipyard"
STAGES = ("10-task", "20-build", "30-checks", "40-approval", "50-release", "60-entw", "70-test", "80-prod", "90-closed")
CID = "SW-2026-001-split-the-api"


def world(tmp_path: Path):
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    case = root / "10-task" / CID
    case.mkdir()
    (case / "meta.json").write_text(json.dumps({"label": "SW", "number": "2026-001", "title": "Split the API", "configVersion": "1"}), encoding="utf-8")
    (case / "review.md").write_text("", encoding="utf-8")
    store = FsStore(root)
    return root, store, DomainConfig.load(CFG, root)


TASK_MD = """# Task: split the API

## Acceptance criteria

- AC-1 · ENTW · yes/no — The API answers on its new path.
- AC-2 · TEST · evidence — A case opened through the new path.
"""
GATES = {"merge": "merge", "approve_test": "entw", "approve_prod": "test"}   # PROD: the TEST acceptance was the last check; prod.md is the proof


def pass_protocol(store, config, tid, by="chris"):
    """The gate's protocol, every item answered as passed by the person, sealed — for tests about what comes after a gate."""
    from casefile.domain import protocol as P
    P.start(store, config, CID, tid, by)
    case = reading.load(store, config, CID)
    doc = case.data[f"protocol-{tid}.json"]
    for it in P.live(doc):
        if it["id"] in doc["answers"]:
            continue
        value = {"yesno": True, "number": 0, "choice": (it.get("criterion") or {}).get("allowed", [""])[0], "evidence": "seen"}[it["type"]]
        P.answer(store, config, CID, tid, by, it["id"], f"pp-{tid}-{it['id']}", value=value)
    P.seal(store, config, CID, tid, by, f"pp-{tid}-seal")


class Steps:
    def __init__(self, store, config, protocols=True):
        self.store, self.config, self.n, self.protocols = store, config, 0, protocols

    def __call__(self, action, by, **payload):
        self.n += 1
        if self.protocols and action in GATES:
            case = reading.load(self.store, self.config, CID)
            if not (case.data or {}).get(f"protocol-{GATES[action]}.json", {}).get("sealed"):
                pass_protocol(self.store, self.config, GATES[action], "chris")      # a person seals; the move may be an agent's
        return stepping.step(self.store, self.config, CID, StepRequest(action=action, step_id=f"s{self.n}", payload=payload), by)

    def deliver(self, root, name, by, text="x"):
        if name == "task.md" and text == "x":
            text = TASK_MD
        (root / reading.load(self.store, self.config, CID).stage / CID / name).write_text(text, encoding="utf-8")
        r = self("deliver", by, files=[name])
        assert r.ok, r.reason
        return r


def stage(store, config):
    return reading.load(store, config, CID).stage


def test_the_whole_way_from_task_to_prod(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    assert go("accept_task", "chris").ok
    go.deliver(root, "pr.md", "axel", "https://example.org/pull/4")
    assert go("open_pr", "axel").ok
    go.deliver(root, "checks.md", "axel")
    assert go("checks_green", "axel").ok
    assert go("merge", "chris").ok
    go.deliver(root, "release.md", "axel")
    assert go("deploy_entw", "axel").ok
    assert go("approve_test", "chris").ok
    go.deliver(root, "test.md", "axel")
    assert go("approve_prod", "chris").ok
    go.deliver(root, "prod.md", "axel")
    assert go("close", "axel").ok
    assert stage(store, config) == "90-closed"


def test_a_task_moves_only_when_the_product_owner_confirms_it(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    assert not go("accept_task", "chris").ok                       # no task written yet
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "axel")                                  # the developer cannot confirm their own task
    assert not r.ok and "product_owner" in r.reason
    assert go("accept_task", "chris").ok


def test_the_author_of_the_pull_request_cannot_merge_it(tmp_path):
    root, store, config = world(tmp_path)
    data = json.loads((CFG / "people.json").read_text(encoding="utf-8"))
    for p in data["people"]:
        if p["id"] == "chris":
            p["roles"] = ["product_owner", "developer"]               # a product owner who also writes code
    (root / "people.json").write_text(json.dumps(data), encoding="utf-8")
    config = DomainConfig.load(CFG, root)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    assert go("accept_task", "chris").ok
    go.deliver(root, "pr.md", "chris")
    assert go("open_pr", "chris").ok
    go.deliver(root, "checks.md", "axel")
    assert go("checks_green", "axel").ok
    r = go("merge", "chris")
    assert not r.ok and "four eyes" in r.reason
    assert stage(store, config) == "40-approval"


def test_the_merge_waits_for_the_recorded_checks_and_can_send_the_change_back(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    go("accept_task", "chris")
    go.deliver(root, "pr.md", "axel")
    go("open_pr", "axel")
    assert not go("checks_green", "axel").ok                       # no check run recorded
    go.deliver(root, "checks.md", "axel")
    go("checks_green", "axel")
    assert not go("send_back", "chris").ok                         # a send-back says why
    assert go("send_back", "chris", note="The tests describe the code, not the requirement.").ok
    assert stage(store, config) == "20-build"


def test_whose_move_names_the_agent_while_it_builds_and_the_owner_at_each_gate(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    moves = whose(reading.load(store, config, CID), config)
    assert moves and moves[0].actor == "role:product_owner"
    go("accept_task", "chris")
    moves = whose(reading.load(store, config, CID), config)
    assert moves and moves[0].actor == "claude"                    # the confirmed task is the build's order: the helper works
    assert [p.id for p in config.persons_for("role:developer")] == ["akhil", "axel"]


def runs(root):
    return sorted(json.loads(f.read_text(encoding="utf-8"))["skill"] for f in (root / "_runs").glob("*.json"))


def test_each_gate_orders_the_helper_for_the_next_stretch(tmp_path):
    """ADR-028: the person confirms, merges and accepts; each of those orders the helper's next stretch, so a change
    that an agent builds needs no terminal between the task and PROD."""
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "chris")
    go("accept_task", "chris")
    assert runs(root) == ["shipyard-build"]
    go.deliver(root, "pr.md", "axel")
    go("open_pr", "axel")
    assert runs(root) == ["shipyard-build", "shipyard-checks"]
    go.deliver(root, "checks.md", "axel")
    assert go("checks_green", "axel").ok
    go("merge", "chris")
    assert runs(root) == ["shipyard-build", "shipyard-checks", "shipyard-release"]
    go.deliver(root, "release.md", "axel")
    go("deploy_entw", "axel")
    go("approve_test", "chris")
    go.deliver(root, "test.md", "axel")
    go("approve_prod", "chris")
    assert runs(root) == ["shipyard-build", "shipyard-checks", "shipyard-release", "shipyard-release", "shipyard-release"]


def test_red_checks_send_the_change_back_to_the_build_with_what_failed(tmp_path):
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "chris")
    go("accept_task", "chris")
    go.deliver(root, "pr.md", "axel")
    go("open_pr", "axel")
    go.deliver(root, "checks.md", "axel")
    assert not go("checks_red", "axel").ok                         # red says what failed
    assert go("checks_red", "axel", note="flows: the desk does not open").ok
    assert stage(store, config) == "20-build" and runs(root).count("shipyard-build") == 2


def test_both_languages_name_every_stage_action_and_file(tmp_path):
    vocab = json.loads((CFG / "vocabulary.json").read_text(encoding="utf-8"))
    stages = json.loads((CFG / "stages.json").read_text(encoding="utf-8"))["stages"]
    files = [a["file"] for a in json.loads((CFG / "artifacts.json").read_text(encoding="utf-8"))["formats"]["SW"]["artifacts"]]
    for lang in ("de", "en"):
        v = vocab[lang]
        for s in stages:
            assert s["key"] in v["stations"] and s["folder"] in v["stages"]
            for a in s.get("actions", []):
                assert a["id"] in v["actions"]
        for f in files:
            assert f in v["files"]


def test_a_release_the_code_host_did_not_confirm_can_be_ordered_again_by_the_product_owner():
    """The merge in the case comes after the merge on the code host. If it came first, the release run finds no merge,
    writes a note and stops; once the product owner has merged on the code host, they order the release again."""
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "shipyard" / "stages.json").read_text())
    release = next(s for s in cfg["stages"] if s["folder"] == "50-release")
    again = next(a for a in release["actions"] if a["id"] == "retry_release")
    assert again["actor"] == "role:product_owner" and again["run"] == "shipyard-release" and not again.get("to")


def test_a_refused_or_failed_deploy_takes_the_case_back_so_the_stage_never_claims_what_is_not_installed():
    """The acceptance moves the case before the deploy runs. If the server refuses or the deploy fails, the case must not
    stand in a stage whose system it never reached: the developer takes it back, with the server's reason."""
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "shipyard" / "stages.json").read_text())
    by = {s["folder"]: s for s in cfg["stages"]}
    for here, before in (("70-test", "60-entw"), ("80-prod", "70-test")):
        a = next(x for x in by[here]["actions"] if x["id"] == "deploy_refused")
        assert a["to"] == before and a["actor"] == "role:developer" and a["payload"] == ["note"]


def test_a_run_ordered_by_a_move_works_in_the_stage_the_case_moves_to(tmp_path):
    """Found on PROD 2026-11-09: the checks helper was given the build stage as its folder, the case already stood in
    the checks stage, and the helper could not write its record there. A run ordered with a move works where the case
    will stand."""
    import json
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "chris")
    go("accept_task", "chris")
    go.deliver(root, "pr.md", "axel")
    go("open_pr", "axel")
    orders = sorted((root / "_runs").glob("*.json"))
    containers = {json.loads(f.read_text())["skill"]: json.loads(f.read_text())["container"] for f in orders}
    assert containers["shipyard-build"].startswith("20-build/")
    assert containers["shipyard-checks"].startswith("30-checks/")


def test_the_product_owner_can_order_the_checks_again_when_the_helper_could_not_finish():
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "shipyard" / "stages.json").read_text())
    checks = next(s for s in cfg["stages"] if s["folder"] == "30-checks")
    again = next(a for a in checks["actions"] if a["id"] == "retry_checks")
    assert again["actor"] == "role:product_owner" and again["run"] == "shipyard-checks" and not again.get("to")


def test_a_failed_run_is_run_again_by_whoever_may_order_its_skill(tmp_path):
    """A helper's run cut off (a deploy restarted the runner): the move goes to whoever may order that skill — here the
    product owner, not an operator nobody is — and "run again" orders the same skill with its own fields, once."""
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "chris")
    assert r.ok and r.run
    run_file = root / "_runs" / f"{r.run}.json"
    doc = json.loads(run_file.read_text())
    doc.update(status="failed", exit=75, finished="2026-11-10T18:52:18+01:00",
               result="Interrupted: the runner stopped while this run was going.", target="x")
    run_file.write_text(json.dumps(doc))
    moves = whose(reading.load(store, config, CID), config, "de")
    assert moves[0].action == "retry" and moves[0].actor == "role:product_owner" and moves[0].label == "Erneut starten"
    assert "Interrupted" in moves[0].reason
    again = stepping.step(store, config, CID, StepRequest(action="retry", step_id="again-1"), "chris")
    assert again.ok and again.run and again.run != r.run
    new = json.loads((root / "_runs" / f"{again.run}.json").read_text())
    assert (new["skill"], new["status"], new["retry_of"], new["target"]) == ("shipyard-build", "queued", r.run, "x")
    assert "exit" not in new and "result" not in new
    replay = stepping.step(store, config, CID, StepRequest(action="retry", step_id="again-1"), "chris")
    assert replay.run == again.run                                           # the same click twice orders once
    twice = stepping.step(store, config, CID, StepRequest(action="retry", step_id="again-2"), "chris")
    assert not twice.ok and "did not fail" in twice.reason                  # the new run is queued: nothing to run again
    case = reading.load(store, config, CID)
    assert any("started again" in e.title for e in case.entries)


def test_a_running_build_shows_its_phases_what_it_does_now_and_how_long_it_usually_takes(tmp_path):
    """REQ-001 W-08: the case knows the helper's phases from the skill's policy, the one reached and the tool call going on
    (the runner's `<id>.progress`), and the median of this skill's finished runs as the expected duration."""
    from casefile.api import views
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "chris")
    for i, secs in enumerate((300, 420, 360)):                               # three earlier builds, done
        (root / "_runs" / f"20261101-10000{i}_shipyard-build_SW-2026-000-old.json").write_text(json.dumps(
            {"id": f"20261101-10000{i}_shipyard-build_SW-2026-000-old", "skill": "shipyard-build", "container": "90-closed/SW-2026-000-old",
             "requested_by": "chris", "status": "done", "created": "2026-11-01T10:00:00+01:00", "duration_s": secs}))
    f = root / "_runs" / f"{r.run}.json"
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": "running", "started": "2026-11-10T19:47:34+01:00"}))
    (root / "_runs" / f"{r.run}.progress").write_text(json.dumps(
        {"steps": 9, "phase": 2, "now": "Bash python -m pytest -q", "recent": ["Edit web/look.css", "Bash python -m pytest -q"]}))
    h = views.helper(config, reading.load(store, config, CID), "de", store)
    assert [p.word for p in h.phases] == ["Lesen", "Ändern", "Testen", "Hochladen", "Übergabe"]
    assert (h.status, h.phase, h.steps, h.now) == ("running", 2, 9, "Bash python -m pytest -q")
    assert h.expected_s == 360
    assert h.skill == "shipyard-build" and h.started.startswith("2026-11-10")
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": "done"}))
    assert views.helper(config, reading.load(store, config, CID), "de", store) is None    # nothing at work, nothing shown


def test_after_a_hand_back_the_product_owner_sends_the_helper_again_with_a_note(tmp_path):
    """SYS-161: the build helper finished but left the case in the build (it handed a decision back). Whoever may order the
    build sends it again with a note; the offer is on the case, never a move in anybody's stack."""
    from casefile.api import views
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "chris")
    f = root / "_runs" / f"{r.run}.json"
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": "done", "finished": "2026-11-10T20:09:20+01:00", "duration_s": 1300}))
    case = reading.load(store, config, CID)
    assert views.again(config, case, "chris", "de").skill == "shipyard-build"
    assert all(t.action != "order_again" for t in whose(case, config))          # not a move: it never counts in a stack
    sent = stepping.step(store, config, CID, StepRequest(action="order_again", step_id="ag-1", payload={"note": "CI is green now, go on to the checks"}), "chris")
    assert sent.ok and sent.run
    new = json.loads((root / "_runs" / f"{sent.run}.json").read_text())
    assert (new["skill"], new["status"], new["again_after"]) == ("shipyard-build", "queued", r.run)
    assert new["note"].endswith("Chris: CI is green now, go on to the checks")
    case = reading.load(store, config, CID)
    assert views.again(config, case, "chris", "de") is None                  # at work again: nothing to offer
    twice = stepping.step(store, config, CID, StepRequest(action="order_again", step_id="ag-2", payload={"note": "x"}), "chris")
    assert not twice.ok


def test_a_person_s_move_waits_while_a_helper_is_at_work_and_the_helper_s_own_steps_go_on(tmp_path):
    """While the build helper runs, the product owner cannot move the case (even with the button in an old page); the
    helper itself still files and moves; once its run is done, the person's moves are theirs again."""
    root, store, config = world(tmp_path)
    go = Steps(store, config)
    go.deliver(root, "task.md", "axel")
    r = go("accept_task", "chris")
    f = root / "_runs" / f"{r.run}.json"
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": "running"}))
    held = go("send_back", "chris")
    assert not held.ok and "helper is at work" in held.reason
    go.deliver(root, "pr.md", "axel", "https://example.org/pull/4")
    assert go("open_pr", "axel").ok                                         # the helper's own step
    f.write_text(json.dumps({**json.loads(f.read_text()), "status": "done"}))


def test_every_gate_waits_for_its_protocol_and_the_task_for_its_criteria(tmp_path):
    """ADR-029 in Shipyard: the task is confirmed only with readable acceptance criteria; merge, ENTW, TEST and the close
    each wait for their sealed protocol; a failed must-item on ENTW offers the way back to the build."""
    from casefile.domain import protocol as P
    root, store, config = world(tmp_path)
    go = Steps(store, config, protocols=False)
    go.deliver(root, "task.md", "axel", "# Task\n\nno criteria yet\n")
    assert not go("accept_task", "chris").ok
    go.deliver(root, "task.v2.md", "axel", TASK_MD)
    assert go("accept_task", "chris").ok
    go.deliver(root, "pr.md", "axel", "https://example.org/pull/4")
    assert go("open_pr", "axel").ok
    go.deliver(root, "checks.md", "axel")
    assert go("checks_green", "axel").ok
    held = go("merge", "chris")
    assert not held.ok and "protocol:merge" in held.reason
    pass_protocol(store, config, "merge")
    assert go("merge", "chris").ok
    go.deliver(root, "release.md", "axel")
    assert go("deploy_entw", "axel").ok
    name = P.start(store, config, CID, "entw", "chris")
    doc = reading.load(store, config, CID).data["protocol-entw.json"]
    assert any(i["origin"] == "task:AC-1" for i in doc["items"])                     # the task's ENTW criterion is an item
    P.answer(store, config, CID, "entw", "chris", "errors", "e1", value=4, note="four 500s after the deploy")
    for it in P.live(doc):
        if it["id"] != "errors":
            P.answer(store, config, CID, "entw", "chris", it["id"], f"e-{it['id']}", value={"yesno": True, "evidence": "tried it"}.get(it["type"], True))
    P.seal(store, config, CID, "entw", "chris", "e-seal")
    assert not go("approve_test", "chris").ok
    back = go("entw_failed", "chris")
    assert back.ok and stage(store, config) == "20-build"


def test_the_move_that_delivers_what_the_gate_waits_for_comes_first(tmp_path):
    """An action that produces what another waits for (`produces`) is the first move, and names the move it opens;
    once the task and its criteria are there, confirming is first again. The core's own token reads as a word."""
    from casefile.domain.turn import enrich
    root, store, config = world(tmp_path)
    case = reading.load(store, config, CID)
    turns = enrich(case, whose(case, config, "de"), config, "de")
    acts = [t for t in turns if t.action in ("draft_task", "accept_task")]
    assert [t.action for t in acts] == ["draft_task", "accept_task"]
    assert acts[0].unblocks == "accept_task" and not acts[0].blocked_by
    assert "Akzeptanzkriterien" in acts[1].missing and "criteria" not in acts[1].missing
    Steps(store, config, protocols=False).deliver(root, "task.md", "axel", TASK_MD)
    case = reading.load(store, config, CID)
    first = [t for t in whose(case, config, "de") if t.action in ("draft_task", "accept_task")]
    assert first[0].action == "accept_task" and not first[0].blocked_by and first[1].unblocks == ""


# A helper writes in the case only what its action delivers (REQ-001 A-05): the order carries the action's `produces`,
# the free question carries none, and `produces` names files only — the same for every application.

def order_of(root: Path, run_id: str) -> dict:
    return json.loads((root / "_runs" / f"{run_id}.json").read_text(encoding="utf-8"))


def test_the_free_question_is_ordered_with_no_delivery(tmp_path):
    root, store, config = world(tmp_path)
    r = Steps(store, config)("ask", "chris", text="Create an HTML page that lists the stages")
    assert r.ok, r.reason
    assert order_of(root, r.run)["produces"] == []


def test_an_action_orders_its_helper_with_what_it_delivers(tmp_path):
    root, store, config = world(tmp_path)
    steps = Steps(store, config)
    r = steps("draft_task", "chris")
    assert r.ok, r.reason
    assert order_of(root, r.run)["produces"] == ["task.md"]
    steps.deliver(root, "task.md", "axel")
    r = steps("accept_task", "chris")
    assert r.ok, r.reason
    assert order_of(root, r.run)["produces"] == ["pr.md"]


def test_produces_names_files_not_checks():
    import pytest
    from pydantic import ValidationError
    from casefile.models import Action
    for bad in (["task.md", "criteria"], ["protocol:merge"], ["../other/x.md"]):
        with pytest.raises(ValidationError):
            Action(id="draft", label="draft", produces=bad)
    assert Action(id="draft", label="draft", produces=["task.md"]).produces == ["task.md"]


def test_every_application_loads_with_files_in_produces(tmp_path):
    """A token in `produces` refuses the configuration; every application's stages load."""
    from casefile.config import DomainConfig as DC
    root = tmp_path / "flow"
    root.mkdir()
    for cfg in sorted(p.parent for p in CFG.parent.glob("*/stages.json")):
        DC.load(cfg, root)


def test_the_task_writer_still_comes_first_when_only_the_criteria_are_missing(tmp_path):
    """`criteria` left `produces`; a gate waiting for criteria still puts the helper that writes the criteria file first."""
    from casefile.domain.turn import enrich
    root, store, config = world(tmp_path)
    Steps(store, config).deliver(root, "task.md", "axel", "# Task: split the API\n\nNo criteria yet.\n")
    case = reading.load(store, config, CID)
    acts = [t for t in enrich(case, whose(case, config, "en"), config, "en") if t.action in ("draft_task", "accept_task")]
    assert [t.action for t in acts] == ["draft_task", "accept_task"]
    assert acts[0].unblocks == "accept_task"
