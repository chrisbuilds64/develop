"""The demo worlds: invented, labelled fictional, built fresh into a folder. Nothing here is real.

Three stories (Bauplan §5): a claims file in German, a content piece with two people, and the e-report of an assessment
organisation (the report as an editorial file). All run on the same core; only the configuration differs. `build_claims(root)` and `build_pressroom(root)` write a pipeline root the
core can serve; the demo copies it once per visitor (ADR-016).
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE.parents[1] / "config"
SAMPLES = HERE / "samples"


def _entry(n: int, title: str, author: str, status: str = "info", for_: str | None = None, stage: str = "", text: str = "", when: str = "",
           files: list[str] | None = None, frm: str | None = None, to: str | None = None, step: str | None = None) -> str:
    head = [f"**Date:** {when}", f"**Author:** {author}", f"**For:** {for_ or '—'}", f"**Status:** {status}", f"**Stage:** {stage}"]
    if step:
        head.append(f"**Step:** {step}")
    if frm:
        head.append(f"**From:** {frm}")
    if to:
        head.append(f"**To:** {to}")
    if files:
        head.append(f"**Files:** {', '.join(files)}")
    return f"\n## REV-{n:03d} — {title}\n{' · '.join(head)}\n\n{text}\n"


def _stamp(days_ago: float, hour: int = 10) -> str:
    d = dt.datetime.now() - dt.timedelta(days=days_ago)
    return d.replace(hour=hour, minute=0).strftime("%Y-%m-%d %H:%M")


def _root(root: Path, config_dir: Path, stages: list[str]) -> Path:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for s in stages:
        (root / s).mkdir()
    for name in ("artifacts.json", "vocabulary.json", "people.json", "run-policy.json", "calendar.json", "connectors.json"):
        if (config_dir / name).is_file():
            shutil.copy(config_dir / name, root / name)
    (root / "_runs").mkdir()
    (root / "DEMO.md").write_text("Fiktive Demo-Daten. Jeder Name, jede Adresse, jede Zahl ist erfunden.\nFictional demo data. Every name, address and number is invented.\n", encoding="utf-8")
    return root


def _case(root: Path, stage: str, cid: str, meta: dict, files: dict[str, bytes | str | Path] | None = None, review: str = "") -> Path:
    d = root / stage / cid
    d.mkdir(parents=True)
    meta = {"configVersion": "1", "fictional": True, **meta}
    if meta.get("label") in ("HR", "WG", "KFZ", "HP") and "external_id" not in meta:
        meta["external_id"] = "SN-" + str(meta.get("number", "")).replace("2026-", "2026-0")     # the house's claim number (fictional)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, content in (files or {}).items():
        if isinstance(content, Path):
            shutil.copy(content, d / name)
        else:
            (d / name).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    if review:
        (d / "review.md").write_text(f"# Review — {cid}\n\nAppend only. Newest entry at the end, never edited afterwards.\n" + review, encoding="utf-8")
    return d


def _signal(root: Path, sid: str, kind: str, title: str, cases: list[str], text: str, days_ago: float = 0) -> None:
    """A hint from the pattern helper across files: never a finding, always with reasoning and the files it rests on."""
    (root / "_signale").mkdir(exist_ok=True)
    (root / "_signale" / f"{sid}.md").write_text(f"---\nid: {sid}\nkind: {kind}\ntitle: {title}\ncases: {', '.join(cases)}\nstatus: offen\ndate: {_stamp(days_ago)[:10]}\n---\n{text}\n", encoding="utf-8")


def _run(root: Path, cid: str, stage: str, skill: str, status: str, minutes_ago: float, by: str, **extra) -> None:
    when = dt.datetime.now().astimezone() - dt.timedelta(minutes=minutes_ago)
    doc = {"id": f"{when.strftime('%Y%m%d-%H%M%S')}_{skill}_{cid}", "skill": skill, "container": f"{stage}/{cid}", "requested_by": by,
           "runner": "claude-code", "status": status, "created": when.isoformat(timespec="seconds"), **extra}
    (root / "_runs" / f"{doc['id']}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- the claims file (German)

CLAIMS_STAGES = ["10-meldung", "20-besichtigung", "25-abgleich", "30-pruefung", "40-regulierung", "60-abgeschlossen"]


def build_claims(root: Path) -> Path:
    cfg = CONFIG / "claims-demo"
    root = _root(root, cfg, CLAIMS_STAGES)
    pdf = SAMPLES / "gutachten.pdf"
    photo = SAMPLES / "foto.jpg"
    kva = SAMPLES / "kostenvoranschlag.pdf"

    # the demo path: everything there but the invoice; drop it, the AI reconciles, you approve with an amount
    _case(root, "30-pruefung", "HR-2026-0417-wasserschaden-badezimmer",
          {"label": "HR", "number": "2026-0417", "title": "Wasserschaden Badezimmer", "created": _stamp(6)[:10], "reported_by": "Familie Beispiel, Musterstraße 12",
           "subtitle": "Rohrbruch hinter der Dusche, Wasser in Decke und Flur"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Am Dienstag kam Wasser aus der Decke im Flur unter dem Bad. Der Installateur hat den Rohrbruch hinter der Dusche gefunden und abgestellt.\n",
           "fotos-1.jpg": photo, "gutachten.pdf": pdf, "gutachten.v2.pdf": pdf, "feuchtemessung.pdf": pdf, "kostenvoranschlag.pdf": kva},
          _entry(1, "Besichtigung angesetzt", "Du", stage="10-meldung", when=_stamp(5, 9), text="Gutachter Berger am Donnerstag 10 Uhr.", step="demo-1", frm="10-meldung", to="20-besichtigung") +
          _entry(2, "Fotos und Gutachten übergeben", "Gutachter Berger", stage="20-besichtigung", when=_stamp(3, 16), files=["fotos-1.jpg", "gutachten.pdf", "feuchtemessung.pdf"],
                 text="Fünf Fotos, Feuchtemessung an drei Stellen, Gutachten als Fassung 1.") +
          _entry(3, "Gutachten Fassung 2", "Gutachter Berger", stage="30-pruefung", when=_stamp(1, 11), files=["gutachten.v2.pdf"],
                 text="Fotos der Decke nachgereicht, Gutachten in Fassung 2. Fassung 1 bleibt erhalten.") +
          _entry(4, "Kostenvoranschlag mit Gutachten abgeglichen", "KI", stage="30-pruefung", when=_stamp(1, 12),
                 text="Zwei Positionen weichen ab: Trocknung (KVA 1.840 €, Gutachten 1.420 €) und Malerarbeiten Flur (KVA 980 €, im Gutachten nicht enthalten). Die Rechnung fehlt noch; sobald sie da ist, gleiche ich alle drei ab.\n\nVorschlag mit Begründung · du entscheidest."))

    # a question from the assessor waits for you
    _case(root, "30-pruefung", "WG-2026-0402-hagelschaden-reihenhaus",
          {"label": "WG", "number": "2026-0402", "title": "Hagelschaden Reihenhaus", "created": _stamp(9)[:10], "subtitle": "Dachziegel und Dachfenster, Ostseite"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Hagel am Abend des 9., Ziegel gebrochen, ein Dachfenster undicht.\n", "fotos-1.jpg": photo, "gutachten.pdf": pdf, "kostenvoranschlag.pdf": kva, "rechnung.pdf": kva},
          _entry(1, "Gutachten übergeben", "Gutachter Berger", stage="20-besichtigung", when=_stamp(4, 15), files=["gutachten.pdf", "fotos-1.jpg"], text="Gutachten und Fotos liegen bei.") +
          _entry(2, "Rückfrage zum Dachfenster", "Gutachter Berger", status="open", for_="Du", stage="30-pruefung", when=_stamp(2, 9),
                 text="Das Dachfenster war laut Nachbar schon vor dem Hagel undicht. Soll ich es im Gutachten ausklammern oder als Vorschaden führen?"))

    # the AI is reconciling right now
    _case(root, "25-abgleich", "WG-2026-0421-sturmschaden-carport",
          {"label": "WG", "number": "2026-0421", "title": "Sturmschaden Carport", "created": _stamp(2)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Sturm, Carportdach abgedeckt.\n", "gutachten.pdf": pdf, "kostenvoranschlag.pdf": kva, "rechnung.pdf": kva},
          _entry(1, "Gutachten übergeben", "Gutachter Berger", stage="20-besichtigung", when=_stamp(1, 14), files=["gutachten.pdf"], text="Dach und Pfosten, siehe Gutachten.", step="demo-c21", frm="20-besichtigung", to="25-abgleich"))
    _run(root, "WG-2026-0421-sturmschaden-carport", "25-abgleich", "reconcile", "queued", 3, "du")   # the replay finishes it a few seconds after the sandbox opens

    # with the assessor
    _case(root, "20-besichtigung", "WG-2026-0425-glasbruch-wintergarten",
          {"label": "WG", "number": "2026-0425", "title": "Glasbruch Wintergarten", "created": _stamp(1)[:10], "publishDate": (dt.date.today() + dt.timedelta(days=2)).isoformat()},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Scheibe im Wintergarten gesprungen, Ursache unklar.\n"},
          _entry(1, "Besichtigung angesetzt", "Du", stage="10-meldung", when=_stamp(1, 10), text="Termin Freitag.", step="demo-2", frm="10-meldung", to="20-besichtigung"))
    _case(root, "20-besichtigung", "KFZ-2026-0811-auffahrunfall-a3",
          {"label": "KFZ", "number": "2026-0811", "title": "Auffahrunfall A3, Kleinwagen", "created": _stamp(3)[:10], "gutachten_auftrag": "GA-2026-01182", "subtitle": "wartet auf das eGutachten GA-2026-01182"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Auffahrunfall im Stau, Heck und Stoßfänger.\n", "fotos-1.jpg": photo})

    # newly reported: a motor claim that orders its assessment (the hand-over into the e-report world)
    _case(root, "10-meldung", "KFZ-2026-0815-parkschaden-tiefgarage",
          {"label": "KFZ", "number": "2026-0815", "title": "Parkschaden Tiefgarage, Kleinwagen", "created": _stamp(0)[:10], "subtitle": "Fahrertür und Schweller, Vollkasko"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Beim Ausparken in der Tiefgarage an einem Betonpfeiler entlanggeschrammt. Fahrertür und Schweller. Fahrzeug fahrbereit, Fotos liegen bei.\n", "fotos-1.jpg": photo},
          _entry(1, "Schaden aufgenommen", "Du", stage="10-meldung", when=_stamp(0, 9), files=["meldung.md", "fotos-1.jpg"], text="Vollkasko, Fahrzeug fahrbereit. Gutachten beauftragen."))
    _case(root, "10-meldung", "HR-2026-0430-einbruch-wohnung",
          {"label": "HR", "number": "2026-0430", "title": "Einbruch Wohnung 2. OG", "created": _stamp(0)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Balkontür aufgehebelt, Laptop und Schmuck fehlen. Polizeiliche Anzeige liegt vor.\n"})

    # in settlement and closed
    _case(root, "40-regulierung", "HP-2026-0309-sturz-glatteis",
          {"label": "HP", "number": "2026-0309", "title": "Sturz auf Glatteis, Hausmeisterdienst", "created": _stamp(20)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv.\n", "gutachten.pdf": pdf, "rechnung.pdf": kva, "abgleich.md": "# Abgleich\n\nKeine Abweichung.\n"},
          _entry(1, "Freigegeben und zur Regulierung", "Du", status="approved", stage="30-pruefung", when=_stamp(2, 9), text="Betrag wie im Gutachten.", step="demo-3", frm="30-pruefung", to="40-regulierung"))
    _signal(root, "M-001", "Wiederholung", "Gleiche Risikoanschrift in zwei Akten innerhalb von fünf Wochen",
            ["HR-2026-0417-wasserschaden-badezimmer", "HR-2026-0430-einbruch-wohnung"],
            "Musterstraße 12, 2. OG: Wasserschaden gemeldet am {a}, Einbruch gemeldet am {b}. Zwei verschiedene Schadenarten, derselbe Vertrag. Das ist kein Verdacht; es ist ein Hinweis, die zweite Akte mit Kenntnis der ersten zu lesen (Zustand der Wohnung nach der Trocknung, Zugänglichkeit).\n\n*Hinweis, keine Feststellung · ein Mensch entscheidet, ob daraus etwas folgt.*".format(a=_stamp(6)[:10], b=_stamp(0)[:10]), 0)
    for i, (cid, title, label, days) in enumerate([("HR-2026-0388-leitungswasser-kueche", "Leitungswasser Küche", "HR", 14), ("KFZ-2026-0790-parkrempler", "Parkrempler Tiefgarage", "KFZ", 21),
                                                  ("WG-2026-0371-blitzschlag-dachstuhl", "Blitzschlag Dachstuhl", "WG", 30)]):
        _case(root, "60-abgeschlossen", cid, {"label": label, "number": cid.split("-")[1] + "-" + cid.split("-")[2], "title": title, "created": _stamp(days + 10)[:10],
                                              "publishDate": (dt.date.today() - dt.timedelta(days=days)).isoformat()},
              {"meldung.md": "# Schadenmeldung\n\nFiktiv.\n", "gutachten.pdf": pdf, "rechnung.pdf": kva, "abgleich.md": "# Abgleich\n\nKeine Abweichung.\n"},
              _entry(1, "Freigegeben und zur Regulierung", "Du", status="approved", stage="30-pruefung", when=_stamp(days + 2, 9), step=f"demo-c{i}", frm="30-pruefung", to="40-regulierung") +
              _entry(2, "Als reguliert gemeldet", "Regulierung", stage="40-regulierung", when=_stamp(days, 15), step=f"demo-d{i}", frm="40-regulierung", to="60-abgeschlossen"))
    return root


# ----------------------------------------------------------------------------- the content piece (English, two people)

PRESSROOM_STAGES = ["00-archive", "05-operational-observations", "10-ideas", "15-interpretation", "20-produce", "30-review-human",
                    "40-asset-generation", "50-ready-to-publish", "55-scheduled", "60-published", "61-field-observation", "65-canonical-review", "66-reviewed", "70-reference-frames"]


def build_pressroom(root: Path) -> Path:
    cfg = CONFIG / "pressroom"
    root = _root(root, cfg, PRESSROOM_STAGES)
    png = SAMPLES / "thumbnail.png"
    script = (SAMPLES / "script.md").read_text(encoding="utf-8")
    draft = (SAMPLES / "draft.md").read_text(encoding="utf-8")

    # Chris approves, Akhil fills the frames
    _case(root, "30-review-human", "POD-ARC-02-the-arc-spoken",
          {"label": "POD", "number": "ARC-02", "series": "ARC", "title": "The Arc, Spoken", "created": _stamp(5)[:10], "subtitle": "A pipeline is a promise about order"},
          {"source.md": "# Idea\n\nWhat happens when the promise is broken and nobody notices.\n", "script.md": script, "teleprompter.txt": script.replace("#", "").strip(),
           "show-notes.txt": "Show notes (fictional).\n", "linkedin-post.txt": "The post (fictional).\n", "first-comment.txt": "Link in the first comment.\n",
           "reel-hooks.txt": "Hook 1. Hook 2. Hook 3.\n", "visual-brief.md": "# Visual brief\n\nA line that breaks where nobody looks.\n"},
          _entry(1, "Script delivered", "Chris", stage="10-ideas", when=_stamp(5, 9), files=["script.md"], text="Read it aloud twice. Good as it stands.") +
          _entry(2, "Teleprompter, show notes, post and hooks are ready", "Axel", stage="30-review-human", when=_stamp(4, 10),
                 files=["teleprompter.txt", "show-notes.txt", "linkedin-post.txt", "first-comment.txt", "reel-hooks.txt", "visual-brief.md"], text="I left your script as it is."))
    _run(root, "POD-ARC-02-the-arc-spoken", "30-review-human", "derive", "done", 4 * 24 * 60, "chris", cost_usd=1.9, model="claude-opus-5-5", turns=6, duration_s=410)

    # Claude asks you one question
    _case(root, "30-review-human", "FN-043-the-review-that-reads-itself",
          {"label": "FN", "number": "043", "title": "The review that reads itself", "created": _stamp(7)[:10]},
          {"source.md": "# Idea\n\nA review process that checks its own blind spots.\n", "substack.md": draft, "linkedin-post.txt": "Post (fictional).\n", "first-comment.txt": "First comment.\n", "visual-brief.md": "# Visual brief\n"},
          _entry(1, "Draft ready", "Axel", stage="30-review-human", when=_stamp(2, 10), files=["substack.md", "linkedin-post.txt"], text="Draft, post and first comment are in.") +
          _entry(2, "Which title?", "Axel", status="open", for_="Chris", stage="30-review-human", when=_stamp(2, 10),
                 text="Two titles fit: 'The review that reads itself' or 'Four eyes, one of them blind'. The second is sharper, the first is yours."))
    _run(root, "FN-043-the-review-that-reads-itself", "30-review-human", "interpret", "done", 2 * 24 * 60, "chris", cost_usd=2.4, model="claude-opus-5-5", turns=9, duration_s=640)

    # Claude is writing
    _case(root, "15-interpretation", "SP-032-the-fourth-reviewer", {"label": "SP", "number": "032", "title": "The fourth reviewer", "created": _stamp(1)[:10]},
          {"source.md": "# Idea\n\nThree reviewers agreed; the fourth was the log.\n"})
    _run(root, "SP-032-the-fourth-reviewer", "15-interpretation", "interpret", "queued", 5, "chris")   # played by the replay once the sandbox opens

    # with Akhil: thumbnail missing
    _case(root, "40-asset-generation", "FN-042-seven-checks-before-merge", {"label": "FN", "number": "042", "title": "Seven checks before merge", "created": _stamp(9)[:10]},
          {"substack.md": draft, "linkedin-post.txt": "Post.\n", "first-comment.txt": "Comment.\n", "visual-brief.md": "# Visual brief\n\nSeven small gates in a row.\n"},
          _entry(1, "Approve and send to Akhil", "Chris", status="approved", stage="30-review-human", when=_stamp(1, 15), step="demo-p1", frm="30-review-human", to="40-asset-generation", text="Good."))

    # ready for a date, scheduled, out
    _case(root, "50-ready-to-publish", "FN-040-the-boring-governance-win", {"label": "FN", "number": "040", "title": "The boring governance win", "created": _stamp(14)[:10]},
          {"substack.md": draft, "linkedin-post.txt": "Post.\n", "header-16x9.png": png, "linkedin-image.png": png},
          _entry(1, "Approve and send to Akhil", "Chris", status="approved", stage="30-review-human", when=_stamp(6, 9), step="demo-p2", frm="30-review-human", to="40-asset-generation") +
          _entry(2, "Added: Header image, LinkedIn image", "Akhil", stage="40-asset-generation", when=_stamp(3, 14), files=["header-16x9.png", "linkedin-image.png"], text="Two images, as in the brief.") +
          _entry(3, "Approve the visual", "Chris", status="approved", stage="40-asset-generation", when=_stamp(2, 9), step="demo-p3", frm="40-asset-generation", to="50-ready-to-publish"))
    _case(root, "55-scheduled", "WN-009-notes-on-friction", {"label": "WN", "number": "009", "title": "Notes on friction", "created": _stamp(10)[:10],
                                                           "publishDate": (dt.date.today() + dt.timedelta(days=(5 - dt.date.today().weekday()) % 7 or 7)).isoformat()},
          {"substack.md": draft, "header-16x9.png": png})
    for i, (cid, label, title, days) in enumerate([("FN-039-what-the-pilot-taught-us", "FN", "What the pilot taught us", 4), ("SP-031-one-file-per-decision", "SP", "One file per decision", 7),
                                                  ("POD-ARC-01-the-first-arc", "POD", "The first arc", 11), ("FN-038-the-quiet-audit", "FN", "The quiet audit", 14),
                                                  ("SP-030-the-handover-note", "SP", "The handover note", 18), ("FN-037-two-models-agreeing", "FN", "Two models agreeing", 21)]):
        meta = {"label": label, "number": cid.split("-")[1], "title": title, "created": _stamp(days + 12)[:10], "publishDate": (dt.date.today() - dt.timedelta(days=days)).isoformat(),
                "publishUrl": "https://example.invalid/fictional"}
        if "ARC" in cid:
            meta["series"] = "ARC"
            meta["number"] = "ARC-01"
        _case(root, "60-published", cid, meta, {"substack.md": draft, "header-16x9.png": png})
    _case(root, "10-ideas", "FN-044-the-audit-nobody-reads", {"label": "FN", "number": "044", "title": "The audit nobody reads", "created": _stamp(1)[:10]},
          {"source.md": "# Idea\n\nAn audit that is filed, never opened, and still changes behaviour.\n"})
    _case(root, "10-ideas", "POD-ARC-03-the-handoff-problem", {"label": "POD", "number": "ARC-03", "series": "ARC", "title": "The handoff problem", "created": _stamp(0)[:10]},
          {"script.md": script},
          _entry(1, "Script delivered", "Akhil", stage="10-ideas", when=_stamp(0, 9), files=["script.md"], text="Developed from the ARC-02 outtakes. Ready for the rest."))
    (root / "series").mkdir()
    (root / "series" / "ARC").mkdir()
    (root / "series" / "ARC" / "series.json").write_text(json.dumps({"label": "ARC", "title": "The Arc", "status": "running", "editor": "chris",
                                                                      "pieces": [{"ref": "POD-ARC-01", "role": "the finding"}, {"ref": "POD-ARC-02", "role": "spoken"}, {"ref": "POD-ARC-03", "role": "the handoff"}]}, indent=2))
    return root


# ----------------------------------------------------------------------------- the e-report (German, the assessor's organisation)

EGUT_STAGES = ["10-auftrag", "20-besichtigung", "30-vorpruefung", "40-fachpruefung", "50-versand", "60-versendet", "70-abgeschlossen"]

GUTACHTEN_MD = """# Kfz-Schadengutachten (Entwurf)

**Auftrag:** {order} · **Fahrzeug:** {car} · **Besichtigung:** {seen}

## Schadenhergang
{story}

## Befund
{finding}

## Kalkulation
Siehe Kalkulation (Anlage). Reparaturkosten netto {amount}. Reparaturwürdig.

## Wertminderung
{wm}

*Fiktives Gutachten für eine Demonstration. Textbausteine B-01, B-05 in der jeweils gültigen Fassung.*
"""

MODULES = {
    "B-01-haftungshinweis.md": "---\nid: B-01\nkind: Baustein\ntitle: Haftungshinweis\nversion: 3\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-09-02\n---\nDas Gutachten beruht auf der Besichtigung des Fahrzeugs und den vorgelegten Unterlagen. Verdeckte Schäden, die erst bei der Instandsetzung erkennbar werden, sind nicht Gegenstand dieses Gutachtens; sie werden auf Anforderung in einem Nachtrag bewertet.\n",
    "B-05-wertminderung.md": "---\nid: B-05\nkind: Baustein\ntitle: Wertminderung\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-06-14\n---\nDie merkantile Wertminderung wird nach dem im Hause freigegebenen Verfahren aus Fahrzeugalter, Laufleistung, Wiederbeschaffungswert und Reparaturkosten ermittelt. Liegt sie unter der Bagatellgrenze, wird sie mit 0 € ausgewiesen und begründet.\n",
    "B-07-restwert.md": "---\nid: B-07\nkind: Baustein\ntitle: Restwert und Wiederbeschaffung\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-06-14\n---\nDer Wiederbeschaffungswert wird anhand des regionalen Marktes ermittelt. Eine Restwertermittlung erfolgt, sobald die Reparaturkosten die hausinterne Grenze erreichen.\n",
    "B-08-schlussformel.md": "---\nid: B-08\nkind: Baustein\ntitle: Schlussformel\nversion: 1\nstatus: freigegeben\napproved_by: Innendienst\ndate: 2026-03-20\n---\nFür Rückfragen stehen wir gern zur Verfügung. Bitte beziehen Sie sich auf die Auftragsnummer.\n",
    "B-10-nutzungsausfall-haftpflicht.md": "---\nid: B-10\nkind: Baustein\ntitle: Nutzungsausfall (Haftpflicht)\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-08-03\n---\nNutzungsausfall nach Gruppe {nu_gruppe} der Tabelle für {nu_tage} Tage: Reparaturdauer zuzüglich Begutachtung und Auftragserteilung.\n",
    "B-11-reparaturweg.md": "---\nid: B-11\nkind: Baustein\ntitle: Reparaturweg\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-05-05\n---\nDie Instandsetzung erfolgt nach Herstellervorgaben in einer Fachwerkstatt mit den in der Kalkulation ausgewiesenen Ersatzteilen und Arbeitswerten.\n",
    "B-12-kein-totalschaden.md": "---\nid: B-12\nkind: Baustein\ntitle: Kein Totalschaden\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-09-30\n---\nDie Reparaturkosten brutto betragen {quote_rk|pct} des Wiederbeschaffungswerts von {wbw|eur}. Sie liegen unter 60 %; eine Restwertermittlung ist nicht erforderlich, ein wirtschaftlicher Totalschaden liegt nicht vor.\n",
    "B-13-totalschaden.md": "---\nid: B-13\nkind: Baustein\ntitle: Wirtschaftlicher Totalschaden\nversion: 3\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-09-30\n---\nDie Reparaturkosten brutto erreichen {quote_rk|pct} des Wiederbeschaffungswerts von {wbw|eur}. Es liegt ein wirtschaftlicher Totalschaden vor. Restwert {restwert|eur} (höchstes von drei Angeboten des regionalen Markts), Wiederbeschaffungsaufwand {wba|eur}.\n",
    "B-14-restwert-kontrolle.md": "---\nid: B-14\nkind: Baustein\ntitle: Restwert zur Kontrolle\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-09-30\n---\nDie Reparaturkosten brutto betragen {quote_rk|pct} des Wiederbeschaffungswerts von {wbw|eur} und liegen damit über 60 %. Der Restwert wurde zur Kontrolle ermittelt ({restwert|eur}); die Reparatur bleibt wirtschaftlich.\n",
    "B-15-nutzungsausfall-kasko.md": "---\nid: B-15\nkind: Baustein\ntitle: Nutzungsausfall (Kasko)\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-08-03\n---\nNutzungsausfall ist in der Kaskoversicherung nicht versichert. Nachrichtlich: Gruppe {nu_gruppe}, {nu_tage} Tage.\n",
    "B-16-keine-vorschaeden.md": "---\nid: B-16\nkind: Baustein\ntitle: Keine Vorschäden\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-04-08\n---\nAm Fahrzeug sind keine Vor- oder Altschäden erkennbar. Der Auftrag enthält keine Hinweise des Versicherers aus dem HIS.\n",
    "B-17-vorschaeden.md": "---\nid: B-17\nkind: Baustein\ntitle: Vorschäden benannt\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-04-08\n---\nVor- und Altschäden, nicht Gegenstand dieses Gutachtens: {vorschaeden_text}\n",
    "B-18-fotodokumentation.md": "---\nid: B-18\nkind: Baustein\ntitle: Fotodokumentation\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-08-11\n---\n{fotos} Aufnahmen nach Fotostandard R-02: Gesamtansichten, Detailaufnahmen je kalkulierter Position, Fahrgestellnummer, Tacho.\n",
    "R-01-vorschaeden.md": "---\nid: R-01\nkind: Regel\ntitle: Vorschäden und HIS\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-04-08\n---\nJedes Gutachten nennt Vorschäden und Altschäden, auch wenn es keine gibt. Hinweise des Versicherers aus dem HIS (Hinweis- und Informationssystem) kommen mit dem Auftrag und werden im Gutachten beantwortet; die Vorprüfung meldet, wenn ein Hinweis unbeantwortet bleibt.\n",
    "R-02-fotostandard.md": "---\nid: R-02\nkind: Regel\ntitle: Fotostandard je Schadenart\nversion: 4\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-08-11\n---\nPflichtansichten je Schadenart: Gesamtansicht vorne und hinten, beide Seiten, Fahrgestellnummer, Tacho, jede kalkulierte Position im Detail. Fehlt eine Ansicht, benennt die Vorprüfung sie; sie entscheidet nicht über die Position.\n",
    "R-03-plausibilitaet.md": "---\nid: R-03\nkind: Regel\ntitle: Plausibilität der Kalkulation\nversion: 2\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-05-05\n---\nDie Kalkulation wird gegen Fahrzeugtyp, Schadenbild und Erfahrungswerte des Hauses geprüft. Abweichungen werden benannt und begründet; eine Position wird nie durch die Vorprüfung geändert.\n",
    "R-04-wertminderung.md": "---\nid: R-04\nkind: Regel\ntitle: Wertminderung ausweisen\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-06-14\n---\nJedes Gutachten trägt eine Aussage zur Wertminderung, auch wenn sie 0 € lautet.\n",
    "R-05-vier-augen.md": "---\nid: R-05\nkind: Regel\ntitle: Vier-Augen-Schwelle\nversion: 1\nstatus: freigegeben\napproved_by: Geschäftsleitung\ndate: 2026-01-15\n---\nAb einer Schadenhöhe über der hausinternen Schwelle gibt eine zweite Person frei. Die Schwelle steht in dieser Regel, nicht im Code.\n",
    "R-07-totalschaden.md": "---\nid: R-07\nkind: Regel\ntitle: Totalschadengrenze und Restwert\nversion: 3\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-09-30\n---\nErreichen die Reparaturkosten 60 % des Wiederbeschaffungswerts, ermittelt der Gutachter den Restwert mit drei Angeboten vom regionalen Markt (BGH) und weist den Wiederbeschaffungsaufwand aus. Ab 100 % liegt ein wirtschaftlicher Totalschaden vor; bis 130 % ist die Reparatur bei Weiternutzung möglich (Integritätsinteresse). Die Vorprüfung rechnet das Verhältnis nach und meldet, wenn ein Pflichtteil fehlt.\n",
    "R-06-belegabgleich.md": "---\nid: R-06\nkind: Regel\ntitle: Belegabgleich\nversion: 1\nstatus: freigegeben\napproved_by: Fachliche Leitung\ndate: 2026-07-01\n---\nDie Rechnung wird Position für Position gegen Gutachten und Kalkulation gelegt. Die KI benennt Abweichungen; kürzen tut der Prüfer.\n",
}


def build_egutachten(root: Path) -> Path:
    cfg = CONFIG / "egutachten"
    root = _root(root, cfg, EGUT_STAGES)
    (root / "DEMO.md").write_text("Fiktive Gutachtenakten für die Demonstration. Jeder Name, jede Nummer und jeder Betrag ist erfunden.\n", encoding="utf-8")
    (root / "_bausteine").mkdir()
    for name, text in MODULES.items():
        (root / "_bausteine" / name).write_text(text, encoding="utf-8")
    photo, kalk, auftrag = SAMPLES / "foto.jpg", SAMPLES / "kostenvoranschlag.pdf", SAMPLES / "gutachten.pdf"
    pruef = (cfg / "replies" / "pruefbericht-default.md").read_text(encoding="utf-8")

    # the demo path: draft and pre-check are in, you approve, the letter gets drafted, the back office sends
    c = "KH-2026-1182-auffahrunfall-a3-kleinwagen"
    _case(root, "40-fachpruefung", c,
          {"label": "KH", "number": "2026-1182", "title": "Auffahrunfall A3, Kleinwagen", "created": _stamp(4)[:10], "external_id": "GA-2026-01182", "subtitle": "Heckschaden, Haftpflicht des Auffahrenden", "client": "Nordlicht Versicherung", "schaden_nr": "SN-2026-00811"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk,
           "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-01182", car="Kleinwagen, EZ 2022, 31.400 km", seen=_stamp(2)[:10], story="Auffahrunfall am Stauende der A3. Heck, Stoßfänger, Rückleuchte links.",
                                               finding="Stoßfänger hinten verformt, Heckklappe eingedrückt, Rückleuchte links gebrochen. Heckrahmen vermessen, ohne Befund. Airbags nicht ausgelöst.", amount="2.900 €", wm="Noch nicht ausgewiesen."),
           "pruefbericht.md": pruef},
          _entry(1, "Auftrag eingegangen", "Innendienst", stage="10-auftrag", when=_stamp(4, 9), files=["auftrag.pdf"], text="Nordlicht Versicherung, Haftpflicht, Besichtigung beim Kunden.") +
          _entry(2, "Besichtigung eingeplant", "Innendienst", stage="10-auftrag", when=_stamp(4, 10), text="Gutachter Lenz, Donnerstag.", step="demo-g1", frm="10-auftrag", to="20-besichtigung") +
          _entry(3, "Entwurf zur Vorprüfung", "Gutachter Lenz", stage="20-besichtigung", when=_stamp(2, 16), files=["fotos-1.jpg", "kalkulation.pdf", "gutachten.md"], text="Fassung 1 mit Fotos und Kalkulation.", step="demo-g2", frm="20-besichtigung", to="30-vorpruefung") +
          _entry(4, "Vorprüfung abgeschlossen", "KI", stage="30-vorpruefung", when=_stamp(2, 17), files=["pruefbericht.md"],
                 text="Zwei Befunde: eine Position ohne Detailfoto, Wertminderung nicht ausgewiesen. Keiner spricht gegen die Freigabe; beide sollte der Gutachter sehen.\n\nBefund mit Begründung · du entscheidest.", step="demo-g3", frm="30-vorpruefung", to="40-fachpruefung"))

    # with the assessor: order placed, draft missing
    c = "KK-2026-1190-parkschaden-tiefgarage"
    _case(root, "20-besichtigung", c, {"label": "KK", "number": "2026-1190", "title": "Parkschaden Tiefgarage", "created": _stamp(1)[:10], "external_id": "GA-2026-01190", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag},
          _entry(1, "Besichtigung eingeplant", "Innendienst", stage="10-auftrag", when=_stamp(1, 9), text="Gutachterin Kaya, morgen.", step="demo-g4", frm="10-auftrag", to="20-besichtigung"))

    # the AI is pre-checking right now (the replay finishes it after the sandbox opens)
    c = "KK-2026-1203-hagelschaden-pkw"
    _case(root, "30-vorpruefung", c, {"label": "KK", "number": "2026-1203", "title": "Hagelschaden Pkw", "created": _stamp(3)[:10], "external_id": "GA-2026-01203", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk,
           "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-01203", car="Kombi, EZ 2021, 58.200 km", seen=_stamp(1)[:10], story="Hagel am Abend, Fahrzeug im Freien.", finding="Dach, Motorhaube und Kofferraumdeckel mit zahlreichen Dellen, keine Lackrisse.", amount="3.480 €", wm="0 €, Bagatellgrenze.")},
          _entry(1, "Entwurf zur Vorprüfung", "Gutachterin Kaya", stage="20-besichtigung", when=_stamp(0, 8), files=["gutachten.md", "kalkulation.pdf", "fotos-1.jpg"], text="Fassung 1.", step="demo-g5", frm="20-besichtigung", to="30-vorpruefung"))
    _run(root, c, "30-vorpruefung", "vorpruefung", "queued", 3, "kaya")

    # approved, the letter is drafted, the back office sends
    c = "KH-2026-1175-glasschaden-frontscheibe"
    _case(root, "50-versand", c, {"label": "KH", "number": "2026-1175", "title": "Glasschaden Frontscheibe", "created": _stamp(6)[:10], "external_id": "GA-2026-01175", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk, "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-01175", car="Limousine, EZ 2019", seen=_stamp(4)[:10], story="Steinschlag auf der Autobahn.", finding="Frontscheibe im Sichtfeld gerissen, Austausch erforderlich.", amount="1.120 €", wm="0 €."),
           "pruefbericht.md": pruef, "anschreiben.md": (cfg / "replies" / "anschreiben-default.md").read_text(encoding="utf-8")},
          _entry(1, "Freigegeben und Anschreiben entwerfen", "Du", status="approved", stage="40-fachpruefung", when=_stamp(1, 11), text="Ohne Befund.", step="demo-g6", frm="40-fachpruefung", to="50-versand") +
          _entry(2, "Anschreiben entworfen", "KI", stage="50-versand", when=_stamp(1, 11), files=["anschreiben.md"], text="Aus den Bausteinen B-01, B-07, B-08.\n\nEntwurf · ein Mensch versendet."))

    # sent, the insurer asks, a follow-up becomes version 2
    c = "KK-2026-0902-wildunfall-landstrasse"
    _case(root, "60-versendet", c, {"label": "KK", "number": "2026-0902", "title": "Wildunfall L 412", "created": _stamp(30)[:10], "external_id": "GA-2026-00902", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk, "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-00902", car="Kombi, EZ 2021, 58.200 km", seen=_stamp(27)[:10], story="Zusammenstoß mit einem Reh auf der L 412.", finding="Frontschaden: Stoßfänger, Scheinwerfer links, Motorhaube, Grill, Lüfter. Kein Rahmenschaden.", amount="4.880 €", wm="250 €."),
           "pruefbericht.md": pruef, "anschreiben.md": (cfg / "replies" / "anschreiben-default.md").read_text(encoding="utf-8")},
          _entry(1, "Versendet", "Innendienst", stage="50-versand", when=_stamp(20, 10), step="demo-g7", frm="50-versand", to="60-versendet") +
          _entry(2, "Rückfrage des Versicherers", "Nordlicht Versicherung", status="open", for_="Gutachter Lenz", stage="60-versendet", when=_stamp(1, 14),
                 text="Der Restwert ist nicht ausgewiesen. Liegen die Reparaturkosten wirklich unter der Grenze? Bitte kurz bestätigen oder Nachtrag."))

    # new order
    _case(root, "10-auftrag", "KH-2026-1210-kreuzungsunfall", {"label": "KH", "number": "2026-1210", "title": "Kreuzungsunfall, Seitenschaden", "created": _stamp(0)[:10], "external_id": "GA-2026-01210", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag}, _entry(1, "Auftrag eingegangen", "Innendienst", stage="10-auftrag", when=_stamp(0, 9), files=["auftrag.pdf"], text="Haftpflicht, Besichtigung in der Werkstatt."))
    # closed
    for i, (cid, title, label, days) in enumerate([("KH-2026-1140-parkrempler", "Parkrempler Supermarkt", "KH", 12), ("KK-2026-1131-marderschaden", "Marderschaden Motorraum", "KK", 18)]):
        _case(root, "70-abgeschlossen", cid, {"label": label, "number": cid.split("-")[1] + "-" + cid.split("-")[2], "title": title, "created": _stamp(days + 8)[:10], "external_id": "GA-" + cid.split("-")[1] + "-0" + cid.split("-")[2], "publishDate": (dt.date.today() - dt.timedelta(days=days)).isoformat()},
              {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk, "gutachten.md": GUTACHTEN_MD.format(order="GA", car="Pkw", seen=_stamp(days + 4)[:10], story="Kurzfall.", finding="Kurzfall.", amount="900 €", wm="0 €."), "pruefbericht.md": pruef},
              _entry(1, "Versendet", "Innendienst", stage="50-versand", when=_stamp(days + 1, 10), step=f"demo-gs{i}", frm="50-versand", to="60-versendet") +
              _entry(2, "Abgeschlossen", "Innendienst", stage="60-versendet", when=_stamp(days, 15), step=f"demo-gc{i}", frm="60-versendet", to="70-abgeschlossen"))
    _signal(root, "M-001", "Dublette", "Identisches Foto in zwei Gutachtenakten",
            ["KH-2026-1140-parkrempler", "KK-2026-1131-marderschaden"],
            "Foto 1 der beiden Akten ist byteweise identisch. Zwei Aufträge, zwei Fahrzeuge, dasselbe Bild: entweder vertauscht oder doppelt abgelegt. Beide Gutachten sind versendet.\n\n*Hinweis, keine Feststellung · der Prüfer entscheidet, ob ein Nachtrag nötig ist.*", 1)
    _signal(root, "M-002", "Wiederholung", "Gleicher Halter in zwei Aufträgen innerhalb von 60 Tagen",
            ["KH-2026-1182-auffahrunfall-a3-kleinwagen", "KK-2026-0902-wildunfall-landstrasse"],
            "Herr Beispiel, Musterstadt: Wildunfall (Kasko) vor 30 Tagen, jetzt Geschädigter eines Auffahrunfalls (Haftpflicht), zwei verschiedene Fahrzeuge. Nichts daran ist auffällig; der Hinweis spart dem Prüfer das Nachschlagen und bringt die Fotos des ersten Falls neben die des zweiten.\n\n*Hinweis, keine Feststellung · der Prüfer entscheidet.*", 0)
    return root


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]).expanduser()
    build_claims(target / "claims")
    build_pressroom(target / "pressroom")
    build_egutachten(target / "egutachten")
    print(f"demo worlds in {target}")
