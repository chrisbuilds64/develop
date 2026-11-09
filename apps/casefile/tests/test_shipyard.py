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


class Steps:
    def __init__(self, store, config):
        self.store, self.config, self.n = store, config, 0

    def __call__(self, action, by, **payload):
        self.n += 1
        return stepping.step(self.store, self.config, CID, StepRequest(action=action, step_id=f"s{self.n}", payload=payload), by)

    def deliver(self, root, name, by, text="x"):
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
