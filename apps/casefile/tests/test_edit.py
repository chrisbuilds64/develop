"""The editor (REQ-001 S-14 – S-16): a file the application marks editable gets its next version from the surface; the
older versions stay (C-06); the thread and meta.json are refused by the core whatever a configuration says (C-07); the
preview is the reader's renderer (S-03); in the criteria file the lines the gate could not read are named with their line."""

from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import criteria
from casefile.models import Deliverable

from .test_shipyard import CID, TASK_MD, world

SHIPYARD = Path(__file__).resolve().parents[1] / "config" / "shipyard"


def client_for(tmp_path):
    root, _, _ = world(tmp_path)
    (root / "10-task" / CID / "task.md").write_text(TASK_MD, encoding="utf-8")
    client = TestClient(create_app(Settings(root=root, config_dir=SHIPYARD, lang="en", secret="test")))
    assert client.post("/api/session", json={"person": "chris"}).status_code == 200
    return client, root / "10-task" / CID


def test_saving_writes_the_next_version_and_leaves_the_first_as_it_was(tmp_path):
    client, case = client_for(tmp_path)
    edited = TASK_MD.replace("on its new path", "on its new path and the old one")
    r = client.post(f"/api/cases/{CID}/edit", json={"file": "task.md", "text": edited, "step_id": "ed-1"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "task.v2.md" and r.json()["step"]["ok"]
    assert (case / "task.md").read_text(encoding="utf-8") == TASK_MD
    assert (case / "task.v2.md").read_text(encoding="utf-8") == edited
    again = client.post(f"/api/cases/{CID}/edit", json={"file": "task.md", "text": edited, "step_id": "ed-1"})
    assert again.json()["step"]["replayed"] and not (case / "task.v3.md").exists()       # the same save twice is one version
    v = client.get(f"/api/cases/{CID}").json()
    assert v["entries"][-1]["files"] == ["task.v2.md"]                                       # the save is a delivery in the thread
    slot = next(s for s in v["slots"] if s["file"] == "task.md")
    assert slot["editable"] and [x["name"] for x in slot["versions"]] == ["task.md", "task.v2.md"]


def test_the_thread_meta_and_unmarked_files_are_refused_and_offered_no_edit(tmp_path):
    client, case = client_for(tmp_path)
    before = {p.name: p.read_bytes() for p in case.iterdir()}
    for f in ("review.md", "meta.json", "pr.md", "nothing.md"):
        r = client.post(f"/api/cases/{CID}/edit", json={"file": f, "text": "x", "step_id": f"ed-{f.replace('.', '-')}"})
        assert r.status_code == 403, (f, r.status_code)
        assert client.post(f"/api/cases/{CID}/edit/preview", json={"file": f, "text": "x"}).status_code == 403
    assert {p.name: p.read_bytes() for p in case.iterdir()} == before
    slots = {s["file"]: s["editable"] for s in client.get(f"/api/cases/{CID}").json()["slots"]}
    assert slots["review.md"] is False and slots["meta.json"] is False and slots["pr.md"] is False


def test_the_core_refuses_the_thread_even_when_a_configuration_marks_it():
    assert not reading.editable(Deliverable(file="review.md", editable=True))
    assert not reading.editable(Deliverable(file="meta.json", editable=True))
    assert not reading.editable(Deliverable(file="substack.html", editable=True))
    assert reading.editable(Deliverable(file="teleprompter.txt", editable=True))
    assert not reading.editable(Deliverable(file="teleprompter.txt"))


def test_the_preview_is_the_readers_rendering_with_raw_html_shown(tmp_path):
    client, _ = client_for(tmp_path)
    r = client.post(f"/api/cases/{CID}/edit/preview", json={"file": "task.md", "text": "# T\n\n**b** <script>alert(1)</script> [x](javascript:alert(1))"})
    assert r.status_code == 200
    html = r.json()["html"]
    assert "<strong>b</strong>" in html and "<script>" not in html and "&lt;script&gt;" in html and "javascript:" not in html


def test_the_criteria_file_comes_with_its_unreadable_lines_where_they_stand(tmp_path):
    client, _ = client_for(tmp_path)
    broken = TASK_MD + "- AC-9 · ENTW · maybe — x\n- just a line\n"
    r = client.post(f"/api/cases/{CID}/edit/preview", json={"file": "task.md", "text": broken}).json()
    lines = broken.split("\n")
    assert [u["line"] for u in r["unreadable"]] == [lines.index("- AC-9 · ENTW · maybe — x") + 1, lines.index("- just a line") + 1]
    assert "AC-9" in r["unreadable"][0]["reason"] and "maybe" in r["unreadable"][0]["reason"]
    assert client.post(f"/api/cases/{CID}/edit/preview", json={"file": "task.md", "text": TASK_MD}).json()["unreadable"] == []


def test_the_line_marks_and_the_gate_name_the_same_lines():
    text = "# T\n\n## Acceptance criteria\n\n- AC-1 · ENTW · yes/no — ok\n- AC-2 · TEST · number about zero — n\n- loose\n\n## Next\n- not a criterion\n"
    marks = criteria.unreadable(text)
    assert [m["line"] for m in marks] == [6, 7]
    assert len(criteria.parse(text)[1]) == 2 and criteria.parse(text)[1][0].startswith("AC-2:")


def test_pressroom_marks_its_drafts_editable_and_never_its_html_or_thread():
    cfg = DomainConfig.load(Path(__file__).resolve().parents[1] / "config" / "pressroom")
    fn = {d.file: reading.editable(d) for d in cfg.deliverables("FN")}
    assert fn["substack.md"] and fn["linkedin-post.txt"] and fn["source.md"] and fn["interpretation.md"]
    assert not fn["substack.html"] and not fn["review.md"] and not fn["meta.json"]
    shipyard = {d.file: reading.editable(d) for d in DomainConfig.load(SHIPYARD).deliverables("SW")}
    assert shipyard["task.md"] and not any(v for f, v in shipyard.items() if f != "task.md")
