"""The demo worlds: invented, labelled fictional, built fresh into a folder. Nothing here is real.

Two stories (Bauplan §5): a claims file in German, a content piece with two people. Both run on the same core;
only the configuration differs. `build_claims(root)` and `build_pressroom(root)` write a pipeline root the
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
    for name in ("artifacts.json", "vocabulary.json", "people.json", "run-policy.json", "calendar.json"):
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
          {"label": "KFZ", "number": "2026-0811", "title": "Auffahrunfall A3, Kleinwagen", "created": _stamp(3)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Auffahrunfall im Stau, Heck und Stoßfänger.\n", "fotos-1.jpg": photo})

    # newly reported
    _case(root, "10-meldung", "HR-2026-0430-einbruch-wohnung",
          {"label": "HR", "number": "2026-0430", "title": "Einbruch Wohnung 2. OG", "created": _stamp(0)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Balkontür aufgehebelt, Laptop und Schmuck fehlen. Polizeiliche Anzeige liegt vor.\n"})

    # in settlement and closed
    _case(root, "40-regulierung", "HP-2026-0309-sturz-glatteis",
          {"label": "HP", "number": "2026-0309", "title": "Sturz auf Glatteis, Hausmeisterdienst", "created": _stamp(20)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv.\n", "gutachten.pdf": pdf, "rechnung.pdf": kva, "abgleich.md": "# Abgleich\n\nKeine Abweichung.\n"},
          _entry(1, "Freigegeben und zur Regulierung", "Du", status="approved", stage="30-pruefung", when=_stamp(2, 9), text="Betrag wie im Gutachten.", step="demo-3", frm="30-pruefung", to="40-regulierung"))
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


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]).expanduser()
    build_claims(target / "claims")
    build_pressroom(target / "pressroom")
    print(f"demo worlds in {target}")
