"""Free notes (REQ-001 S-17): every case may hold Markdown notes under `notes/`, created, edited and versioned in the
editor; they count for no gate. An application switches them off with `"notes": false` in theme.json; the default is on."""

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.domain import cases as reading
from casefile.domain import notes
from casefile.domain.turn import turn as whose
from casefile.store import FsStore

from .test_shipyard import CID, world

SHIPYARD = Path(__file__).resolve().parents[1] / "config" / "shipyard"
PRESSROOM = Path(__file__).resolve().parents[1] / "config" / "pressroom"


def client_for(tmp_path, config_dir=SHIPYARD):
    root, _, _ = world(tmp_path)
    client = TestClient(create_app(Settings(root=root, config_dir=config_dir, lang="en", secret="test")))
    assert client.post("/api/session", json={"person": "chris"}).status_code == 200
    return client, root / "10-task" / CID


def notes_off(tmp_path) -> Path:
    d = tmp_path / "shipyard-cfg"
    shutil.copytree(SHIPYARD, d)
    theme = json.loads((d / "theme.json").read_text(encoding="utf-8"))
    (d / "theme.json").write_text(json.dumps({**theme, "notes": False}), encoding="utf-8")
    return d


def test_a_new_note_is_named_by_its_title_and_its_saves_are_versions_delivered_in_the_thread(tmp_path):
    client, case = client_for(tmp_path)
    r = client.post(f"/api/cases/{CID}/notes", json={"title": "Gespräch mit Peter"})
    assert r.status_code == 200, r.text
    file = r.json()["file"]
    assert file == "notes/gespraech-mit-peter.md" and not (case / "notes").exists()          # naming writes nothing
    first = client.post(f"/api/cases/{CID}/edit", json={"file": file, "text": "# Gespräch mit Peter\n\nErste Fassung.", "step_id": "note-1"})
    assert first.status_code == 200, first.text
    assert first.json()["name"] == file
    second = client.post(f"/api/cases/{CID}/edit", json={"file": file, "text": "# Gespräch mit Peter\n\nZweite Fassung.", "step_id": "note-2"})
    assert second.json()["name"] == "notes/gespraech-mit-peter.v2.md"
    assert (case / "notes" / "gespraech-mit-peter.md").read_text(encoding="utf-8").endswith("Erste Fassung.")
    v = client.get(f"/api/cases/{CID}").json()
    assert [(n["file"], n["word"], [x["name"] for x in n["versions"]]) for n in v["notes"]] == [
        (file, "Gespräch mit Peter", [file, "notes/gespraech-mit-peter.v2.md"])]
    assert not any(s["file"].startswith("notes") for s in v["slots"])                         # beside the slots, never among them
    assert v["entries"][-1]["files"] == ["notes/gespraech-mit-peter.v2.md"]                   # every save is a delivery
    read = client.get(f"/api/cases/{CID}/read/notes/gespraech-mit-peter.v2.md")
    assert read.status_code == 200 and "Zweite Fassung." in read.json()["html"]
    assert client.get(f"/api/cases/{CID}/files/notes/gespraech-mit-peter.md").status_code == 200
    again = client.post(f"/api/cases/{CID}/notes", json={"title": "gespräch mit peter"})
    assert again.status_code == 409                                                           # a title never overwrites another note


def test_a_note_changes_no_action_and_no_blocked_reason(tmp_path):
    root, store, config = world(tmp_path)                                                    # a task case in 10-task without task.md
    before = whose(reading.load(store, config, CID), config, "en")
    notes.save(store, CID, "notes/task.md", "# Task: written as a note\n\n## Acceptance criteria\n\n- AC-1 · ENTW · yes/no — x\n")
    after_case = reading.load(store, config, CID)
    assert [n.file for n in after_case.notes] == ["notes/task.md"]
    assert after_case.files == reading.load(store, config, CID).files and "task.md" not in after_case.files
    after = whose(after_case, config, "en")
    assert [(t.action, t.actor, t.blocked_by) for t in after] == [(t.action, t.actor, t.blocked_by) for t in before]
    assert "_criteria" not in after_case.data


def test_names_outside_the_notes_folder_are_refused(tmp_path):
    client, case = client_for(tmp_path)
    for f in ("notes/../review.md", "notes/x.txt", "notes/X.md", "notes/a/b.md", "notes/x.v2.md", "notes/.x.md", "notes/x.html"):
        r = client.post(f"/api/cases/{CID}/edit", json={"file": f, "text": "x", "step_id": "bad-" + str(abs(hash(f)))})
        assert r.status_code == 403, (f, r.status_code)
    assert not (case / "notes").exists()
    assert client.post(f"/api/cases/{CID}/notes", json={"title": "  ?!  "}).status_code == 422
    assert client.get(f"/api/cases/{CID}/read/meta%2Fx.md").status_code == 404
    assert client.get(f"/api/cases/{CID}/files/sub/meta.json").status_code == 404


def test_an_application_that_switches_notes_off_offers_none_and_refuses_them(tmp_path):
    client, case = client_for(tmp_path, notes_off(tmp_path))
    assert client.post(f"/api/cases/{CID}/notes", json={"title": "x"}).status_code == 403
    assert client.post(f"/api/cases/{CID}/edit", json={"file": "notes/x.md", "text": "x", "step_id": "off-1"}).status_code == 403
    assert client.post(f"/api/cases/{CID}/edit/preview", json={"file": "notes/x.md", "text": "x"}).status_code == 403
    assert not (case / "notes").exists()
    assert client.get("/api/config").json()["theme"]["notes"] is False                       # the surface reads the same switch


def test_notes_are_on_by_default_in_every_application():
    for d in (SHIPYARD, PRESSROOM):
        assert notes.enabled(DomainConfig.load(d))
    assert notes.slug("Gespräch mit Peter – 2. Runde") == "gespraech-mit-peter-2-runde"


def test_the_store_lists_the_notes_folder_and_top_level_files_stay_as_they_were(tmp_path):
    root, store, _ = world(tmp_path)
    top = store.files(CID)
    store.put_bytes(CID, "notes/a.md", b"a")
    assert store.files(CID) == top and store.sub_files(CID, "notes") == ["notes/a.md"]
    assert FsStore(root).sub_files(CID, "nothing") == []
