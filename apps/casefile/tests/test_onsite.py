"""At the car: photos go into the next place of the series (a sample under its own name too), the on-site state says what each
photo shows and what is settled, and a helper asked again answers with the next round's prepared reply."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.config import DomainConfig
from casefile.demo.replay import play
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config" / "egutachten"
STAGES = ("10-auftrag", "20-besichtigung", "30-vorpruefung", "40-fachpruefung", "50-versand", "60-versendet", "70-abgeschlossen")
CID = "KK-2026-0001-streifschaden"


def world(tmp_path: Path) -> Path:
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    case = root / "20-besichtigung" / CID
    case.mkdir()
    (case / "meta.json").write_text(json.dumps({"label": "KK", "title": "Streifschaden", "configVersion": "1", "fictional": True}), encoding="utf-8")
    (case / "review.md").write_text("", encoding="utf-8")
    (root / "_samples").mkdir()
    (root / "_samples" / "vorort-hinten.jpg").write_bytes(b"\xff\xd8\xff fictional jpeg")
    (root / "_replies").mkdir()
    for n, title in ((1, "Runde eins"), (2, "Runde zwei")):
        (root / "_replies" / f"fotohinweis.{CID}.{n}.json").write_text(json.dumps(
            {"delay_s": 0, "files": {"fotohinweise.json": f"inline:{json.dumps({'round': n})}"}, "entry": {"title": title, "text": "."}}), encoding="utf-8")
    return root


def client(root: Path) -> TestClient:
    c = TestClient(create_app(Settings(root=root, config_dir=CFG, secret="t", demo=True, samples_dir=None, replies_dir=None)))
    assert c.post("/api/session", json={"person": "kaya"}).status_code == 200
    return c


def test_a_sample_goes_into_the_series_and_the_state_says_what_it_shows(tmp_path):
    root = world(tmp_path)
    c = client(root)
    assert c.get("/api/config").json()["theme"]["onsite"]["series"] == "fotos-{n}.jpg"
    r = c.post(f"/api/cases/{CID}/samples", json={"slot": "fotos-1.jpg", "source": "vorort-hinten.jpg", "step_id": "s1"})
    assert r.status_code == 200 and r.json()["name"] == "fotos-1.jpg"
    assert c.post(f"/api/cases/{CID}/samples", json={"slot": "fotos-2.jpg", "source": "nothing.jpg", "step_id": "s2"}).status_code == 404
    r = c.put(f"/api/cases/{CID}/vorort", json={"photos": {"fotos-1.jpg": "hinten"}, "hints": {"lack": {"done": True, "text": "110 µm, Erstlack"}}})
    assert r.status_code == 200
    r = c.put(f"/api/cases/{CID}/vorort", json={"photos": {"fotos-2.jpg": "fin"}})
    state = c.get(f"/api/cases/{CID}").json()["data"]["vorort.json"]
    assert state["photos"] == {"fotos-1.jpg": "hinten", "fotos-2.jpg": "fin"} and state["hints"]["lack"]["text"] == "110 µm, Erstlack"
    assert state["hints"]["lack"]["by"] == "kaya"
    assert c.put(f"/api/cases/{CID}/vorort", json={"photos": {"../x": "a"}}).status_code == 422


def test_asked_again_the_helper_answers_the_next_round(tmp_path):
    root = world(tmp_path)
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    for n in (1, 2):
        r = stepping.step(store, config, CID, StepRequest(action="ask", step_id=f"a{n}", payload={"skill": "fotohinweis", "text": f"Runde {n}"}), "kaya")
        assert r.ok and r.run
        assert play(store, config, r.run + ".json", None, wait=False)
        assert json.loads((root / "20-besichtigung" / CID / ("fotohinweise.json" if n == 1 else "fotohinweise.v2.json")).read_text())["round"] == n
