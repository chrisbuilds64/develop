"""An inventory end to end: the core's steps leave their files and sign as the core, the helper's draft is decided line by line,
the valid state is compiled from the decisions, and the case reaches proven only through every gate."""

import json
from pathlib import Path

from casefile.config import DomainConfig
from casefile.demo.replay import play
from casefile.domain import interview as talk
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config" / "bestandsakte"
STAGES = ("10-bestand", "20-baseline", "30-abgleich", "40-entscheid", "50-gueltig", "60-neuaufbau", "70-bewiesen")
CID = "BA-2026-0001-auftragsverwaltung"
LINES = {"lines": [{"id": "A-1", "block": "Code", "text": "Der Hotfix gilt.", "sources": []},
                   {"id": "A-2", "block": "Eigentum", "text": "Bitte benennen.", "sources": []}]}


def world(tmp_path: Path) -> Path:
    root = tmp_path / "flow"
    for s in STAGES:
        (root / s).mkdir(parents=True)
    case = root / "10-bestand" / CID
    case.mkdir()
    (case / "meta.json").write_text(json.dumps({"label": "BA", "title": "Auftragsverwaltung", "configVersion": "1", "fictional": True}), encoding="utf-8")
    (case / "review.md").write_text("", encoding="utf-8")
    (root / "_replies").mkdir()
    replies = {"ernte": {"baseline.md": "# Baseline"}, "skripte": {"skripte-test.md": "# TEST"},
               "abgleich": {"abweichungen.json": json.dumps(LINES), "befund.json": json.dumps({"summary": "Drei Ursachen."})},
               "neuaufbau": {"neuaufbau.md": "# Neuaufbau"}, "nachweis": {"nachweis.md": "# Leer"}}
    for skill, files in replies.items():
        author = {} if skill == "abgleich" else {"author": "Kern · SQLcl"}
        (root / "_replies" / f"{skill}.{CID}.json").write_text(json.dumps(
            {"delay_s": 0, "files": {n: f"inline:{c}" for n, c in files.items()}, "entry": {"title": skill, "text": ".", **author}}), encoding="utf-8")
    return root


def press(store: FsStore, config: DomainConfig, action: str, n: int) -> None:
    r = stepping.step(store, config, CID, StepRequest(action=action, step_id=f"s{n}"), "chris")
    assert r.ok, r.reason
    if r.run:
        assert play(store, config, r.run + ".json", None, wait=False)


def test_an_inventory_reaches_proven_only_through_every_gate(tmp_path):
    root = world(tmp_path)
    store, config = FsStore(root), DomainConfig.load(CFG, root)
    for n, action in enumerate(("harvest", "replay_scripts", "explain"), 1):
        press(store, config, action, n)
    assert store.find(CID) == "40-entscheid"
    thread = (root / "40-entscheid" / CID / "review.md").read_text(encoding="utf-8")
    assert "Kern · SQLcl" in thread                                     # the core's steps are not the AI's

    refused = stepping.step(store, config, CID, StepRequest(action="approve_canon", step_id="early"), "chris")
    assert not refused.ok and store.find(CID) == "40-entscheid"         # an undecided line holds the gate
    talk.decide(store, config, CID, "chris", "A-1", "accept", "", "d1", "abweichungen.json", "entscheide.json")
    talk.decide(store, config, CID, "chris", "A-2", "edit", "Eigentümer ist Chris.", "d2", "abweichungen.json", "entscheide.json")
    press(store, config, "approve_canon", 10)
    valid = (root / "50-gueltig" / CID / "canon.md").read_text(encoding="utf-8")
    assert "Gültiger Stand" in valid and "Eigentümer ist Chris." in valid and "Bitte benennen." not in valid

    press(store, config, "rebuild", 11)
    press(store, config, "prove", 12)
    assert store.find(CID) == "70-bewiesen"
    assert (root / "70-bewiesen" / CID / "nachweis.md").is_file()
