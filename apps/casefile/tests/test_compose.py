"""Composing: the core assembles the report from approved modules, chosen by rules over the result — the result decides which
modules stand, a missing value or an unapproved module refuses and nothing is written."""

import json
from pathlib import Path

import pytest

from casefile.config import DomainConfig
from casefile.demo.worlds import MODULES
from casefile.domain import compose
from casefile.domain import step as stepping
from casefile.models import StepRequest
from casefile.store import FsStore

CFG = Path(__file__).resolve().parents[1] / "config"
SPEC = json.loads((CFG / "egutachten" / "aufbau.json").read_text(encoding="utf-8"))
STAGES = ("10-auftrag", "20-besichtigung", "30-vorpruefung", "40-fachpruefung", "50-versand", "60-versendet", "70-abgeschlossen")


@pytest.fixture
def mods(tmp_path):
    d = tmp_path / "_bausteine"
    d.mkdir()
    for name, text in MODULES.items():
        (d / name).write_text(text, encoding="utf-8")
    return compose.modules(FsStore(tmp_path))


def result(**over) -> dict:
    base = dict(order="GA-1", sparte="Kasko", fahrzeug="Kompaktwagen", fin="WXX1", besichtigung="2026-10-27", ort="Tiefgarage", gutachter="Kaya",
                vorschaeden="nein", hergang="Pfeiler.", befund="Tür verkratzt.", reparaturweg="Tür lackieren.", fotos=3, kalk_system="DAT",
                rk_netto=1640, rk_brutto=1951.6, dauer="2 Tage", wbw=22400, wm=0, wm_grund="Bagatellgrenze", sparte_typ="kasko", nu_gruppe="D", nu_tage=2)
    return {"fields": {k: {"value": v, "word": k} for k, v in {**base, **over}.items()}}


def test_a_repair_takes_the_repair_modules(mods):
    text, used = compose.compose(result(), SPEC, mods)
    ids = [u["module"] for u in used]
    assert ids == ["B-16", "B-11", "B-18", "B-12", "B-05", "B-15", "B-01"]
    assert "8,7 %" in text and "22.400,00 €" in text and "[B-12 · Kein Totalschaden, Fassung 2]" in text and "Ergebnis: **0 €** (Bagatellgrenze)" in text


def test_the_result_changes_the_report(mods):
    text, used = compose.compose(result(rk_brutto=8234.8, wbw=7800, restwert=1450, sparte_typ="haftpflicht", vorschaeden="ja",
                                        vorschaeden_text="Front 2023, repariert.", wm=250), SPEC, mods)
    ids = [u["module"] for u in used]
    assert "B-13" in ids and "B-11" not in ids and "B-17" in ids and "B-10" in ids      # total loss: no repair route, prior damage named
    assert "105,6 %" in text and "6.350,00 €" in text and "Ergebnis: **250,00 €**" in text


def test_a_missing_value_or_an_unapproved_module_refuses(mods):
    r = result()
    del r["fields"]["wbw"]
    with pytest.raises(compose.ComposeError, match="wbw"):
        compose.compose(r, SPEC, mods)
    mods["B-12"]["status"] = "Entwurf"
    with pytest.raises(compose.ComposeError, match="B-12"):
        compose.compose(result(), SPEC, mods)


def test_compose_step_writes_the_next_version_and_stays(tmp_path):
    root = tmp_path / "flow"
    for st in STAGES:
        (root / st).mkdir(parents=True)
    (root / "_runs").mkdir()
    (root / "_bausteine").mkdir()
    for name, text in MODULES.items():
        (root / "_bausteine" / name).write_text(text, encoding="utf-8")
    store = FsStore(root)
    cid = "KK-2026-0001-test"
    store.mkcase("20-besichtigung", cid)
    store.write_json(f"20-besichtigung/{cid}/meta.json", {"label": "KK", "number": "2026-0001", "title": "Test"})
    config = DomainConfig.load(CFG / "egutachten", root)
    r = stepping.step(store, config, cid, StepRequest(action="compose_report", step_id="c0"), "du")
    assert not r.ok and "ergebnis.json" in r.reason
    store.write_json(f"20-besichtigung/{cid}/ergebnis.json", result())
    store.write_atomic(f"20-besichtigung/{cid}/gutachten.md", "# alt\n")
    r = stepping.step(store, config, cid, StepRequest(action="compose_report", step_id="c1"), "du")
    assert r.ok and store.find(cid) == "20-besichtigung"
    assert store.case_text(cid, "gutachten.md") == "# alt\n" and "Bausteinen" in store.case_text(cid, "gutachten.v2.md")
