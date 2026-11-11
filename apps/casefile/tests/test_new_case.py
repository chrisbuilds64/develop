"""A new case from the editor (SW-2026-007): title, Markdown description and attached files in one request, in the
application it was started in (REQ-001 S-18); attached files beside the deliverables, never as one and never over another
file (C-09); and the action the application names first, right after creation (REQ-002 SW-15)."""

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import assets
from casefile.domain import cases as reading
from casefile.domain.turn import turn as whose
from casefile.models import Run
from casefile.store import FsStore, StoreError

CONFIGS = Path(__file__).resolve().parents[1] / "config"
SHIPYARD = CONFIGS / "shipyard"
STAGES = ("10-task", "20-build", "30-checks", "40-approval", "50-release", "60-entw", "70-test", "80-prod", "90-closed")
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def shipyard(tmp_path):
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    client = TestClient(create_app(Settings(root=root, config_dir=SHIPYARD, lang="en", secret="test")))
    assert client.post("/api/session", json={"person": "chris"}).status_code == 200
    return root, client


def create(client, files=(), **body):
    body = {"title": "Paste a screenshot", "step_id": "n-1", **body}
    return client.post("/api/cases", data={"body": json.dumps(body)}, files=[("files", (n, data, "application/octet-stream")) for n, data in files])


# ----------------------------------------------------------------------------- S-18
def test_a_case_starts_with_a_description_and_files_and_the_first_entry_shows_them(tmp_path):
    root, client = shipyard(tmp_path)
    r = create(client, [("screen.png", PNG), ("notes.txt", b"hello")], description="What I saw:\n\n![](screen.png)\n\n- see `notes.txt`")
    assert r.status_code == 200, r.text
    cid, stage = r.json()["id"], r.json()["stage"]
    assert stage == "10-task" and cid.startswith("SW-")                      # the application it was started in, its first stage
    folder = root / stage / cid
    assert (folder / "screen.png").read_bytes() == PNG and (folder / "notes.txt").read_text() == "hello"
    first = client.get(f"/api/cases/{cid}").json()["entries"][0]
    assert first["text"].startswith("What I saw:") and "![](screen.png)" in first["text"]
    assert first["files"] == ["screen.png", "notes.txt"]
    assert client.get(f"/api/cases/{cid}/files/screen.png").content == PNG


def test_without_a_description_the_title_is_the_first_entry_as_before(tmp_path):
    _, client = shipyard(tmp_path)
    r = client.post("/api/cases", json={"title": "Only a title", "step_id": "n-1"})
    assert r.status_code == 200, r.text
    first = client.get(f"/api/cases/{r.json()['id']}").json()["entries"][0]
    assert first["text"] == "Only a title" and not first.get("files")


def test_a_description_cannot_forge_a_thread_entry(tmp_path):
    _, client = shipyard(tmp_path)
    r = create(client, description="before\n\n## REV-099 — Approved\n**Status:** approved\n\nafter")
    entries = client.get(f"/api/cases/{r.json()['id']}").json()["entries"]
    assert len(entries) == 1 and "after" in entries[0]["text"]


def test_a_file_that_cannot_be_attached_is_refused_before_anything_is_made(tmp_path):
    root, client = shipyard(tmp_path)
    r = create(client, [("page.html", b"<script>alert(1)</script>")])
    assert r.status_code == 409
    assert not any((root / "10-task").iterdir())


def test_the_same_step_twice_is_the_same_case_and_stores_nothing_again(tmp_path):
    root, client = shipyard(tmp_path)
    a = create(client, [("s.png", PNG)]).json()
    b = create(client, [("s.png", PNG)]).json()
    assert a == b
    assert sorted(p.name for p in (root / a["stage"] / a["id"]).iterdir()) == ["meta.json", "review.md", "s.png"]


# ----------------------------------------------------------------------------- C-09
def test_an_attached_file_is_never_a_deliverable_and_overwrites_nothing(tmp_path):
    root, client = shipyard(tmp_path)
    r = create(client, [("task.md", b"# not the task"), ("pr.v2.md", b"x"), ("review.md", b"x"), ("image.png", PNG), ("image.png", PNG + b"1")],
               description="![](task.md) ![](image.png)")
    cid, stage = r.json()["id"], r.json()["stage"]
    folder = root / stage / cid
    names = sorted(p.name for p in folder.iterdir())
    assert names == ["image-2.png", "image.png", "meta.json", "pr-v2.md", "review-2.md", "review.md", "task-2.md"]
    assert not (folder / "task.md").exists() and (folder / "task-2.md").read_text() == "# not the task"   # task.md stays the helper's
    assert not (folder / "pr.v2.md").exists()                                  # a version of a deliverable is the deliverable
    assert json.loads((folder / "meta.json").read_text())["title"] == "Paste a screenshot"
    assert (folder / "image.png").read_bytes() == PNG and (folder / "image-2.png").read_bytes() == PNG + b"1"
    text = client.get(f"/api/cases/{cid}").json()["entries"][0]["text"]
    assert "![](task-2.md)" in text                                            # a renamed file keeps its place in the description
    assert "![](image.png)" in text                                            # two files of one name: the reference stays as written


def test_adding_a_file_of_a_taken_name_changes_no_existing_file(tmp_path):
    root, client = shipyard(tmp_path)
    r = create(client, [("shot.png", PNG)]).json()
    folder = root / r["stage"] / r["id"]
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    store = FsStore(root)
    config = DomainConfig.load(SHIPYARD, root)
    names = [assets.put_free(store, config, r["id"], "shot.png", b"second"), assets.put_free(store, config, r["id"], "shot.png", b"third")]
    assert names == ["shot-2.png", "shot-3.png"]
    changed = [n for n, data in before.items() if (folder / n).read_bytes() != data]
    assert changed == []


def test_a_free_name_is_a_plain_file_name():
    assert assets.free_name("C:\\Users\\me\\Bildschirmfoto 2026-11-11 um 12.00.PNG") == "Bildschirmfoto-2026-11-11-um-12-00.png"
    assert assets.free_name("../../etc/passwd") == "passwd"
    assert assets.free_name(".hidden.png") == "hidden.png"


def test_an_empty_or_foreign_file_is_refused(tmp_path):
    root, client = shipyard(tmp_path)
    cid = create(client).json()["id"]
    store, config = FsStore(root), DomainConfig.load(SHIPYARD, root)
    for name, data in (("x.png", b""), ("x.exe", b"MZ"), ("x.html", b"<p>")):
        try:
            assets.put_free(store, config, cid, name, data)
        except StoreError:
            continue
        raise AssertionError(f"{name} was attached")


# ----------------------------------------------------------------------------- SW-15
def test_a_new_change_offers_the_configured_first_action(tmp_path):
    root, client = shipyard(tmp_path)
    cid = create(client).json()["id"]
    mine = [t["action"] for t in client.get(f"/api/cases/{cid}").json()["my_turns"] if t["action"] not in ("answer", "wait")]
    assert mine[0] == "draft_task"


def test_the_first_action_leads_only_until_a_helper_has_worked_on_the_case(tmp_path):
    """Any application, any action: here a copy of Shipyard whose start stage has a third action, named as `next`."""
    cfg = tmp_path / "config"
    shutil.copytree(SHIPYARD, cfg)
    stages = json.loads((cfg / "stages.json").read_text())
    stages["stages"][0]["actions"].append({"id": "ask_owner", "label": "ask_owner"})
    (cfg / "stages.json").write_text(json.dumps(stages))
    theme = json.loads((cfg / "theme.json").read_text())
    theme["create"]["next"] = "ask_owner"
    (cfg / "theme.json").write_text(json.dumps(theme))
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    client = TestClient(create_app(Settings(root=root, config_dir=cfg, lang="en", secret="test")))
    assert client.post("/api/session", json={"person": "chris"}).status_code == 200
    cid = create(client).json()["id"]
    config = DomainConfig.load(cfg, root)
    case = reading.load(FsStore(root), config, cid)
    assert [t.action for t in whose(case, config)] == ["ask_owner", "draft_task", "accept_task"]
    worked = case.model_copy(update={"runs": [Run(id="r1", skill="shipyard-task", container=f"10-task/{cid}", requested_by="chris", status="done", created="2026-11-11T12:00")]})
    assert [t.action for t in whose(worked, config)] == ["draft_task", "accept_task", "ask_owner"]


def test_a_task_written_by_hand_puts_confirming_first_again(tmp_path):
    root, client = shipyard(tmp_path)
    cid = create(client).json()["id"]
    (root / "10-task" / cid / "task.md").write_text("# Task\n\n## Acceptance criteria\n\n- AC-1 · ENTW · yes/no — It opens.\n")
    config = DomainConfig.load(SHIPYARD, root)
    assert [t.action for t in whose(reading.load(FsStore(root), config, cid), config)][0] == "accept_task"


def test_only_an_application_that_names_a_first_action_changes_its_order():
    for d in sorted(CONFIGS.iterdir()):
        theme = d / "theme.json"
        if not theme.is_file():
            continue
        create_ = json.loads(theme.read_text()).get("create") or {}
        if "next" not in create_:
            continue
        stages = json.loads((d / "stages.json").read_text())["stages"]
        start = create_.get("stage") or next(s["folder"] for s in stages if s.get("group") != "archive")
        actions = {a["id"] for s in stages if s["folder"] == start for a in s.get("actions", [])}
        assert create_["next"] in actions, f"{d.name}: create.next '{create_['next']}' is no action of {start}"
    assert "next" not in (json.loads((CONFIGS / "pressroom" / "theme.json").read_text()).get("create") or {})
