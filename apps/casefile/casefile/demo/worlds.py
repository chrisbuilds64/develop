"""The demo worlds: invented, labelled fictional, built fresh into a folder. Nothing here is real.

Three stories (Bauplan §5): a claims file in German, a content piece with two people, and the e-report of an assessment
organisation (the report as an editorial file). All run on the same core; only the configuration differs. `build_claims(root)` and `build_pressroom(root)` write a pipeline root the
core can serve; the demo copies it once per visitor (ADR-016).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
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


# The demo cases in English too (request 8): a viewer who reads English sees these, through `i18n.en` in the case's meta.
EN_WORDS = {
    "Hagelschaden Reihenhaus": "Hail damage, terraced house", "Dachziegel und Dachfenster, Ostseite": "Roof tiles and roof window, east side",
    "Wasserschaden Badezimmer": "Water damage, bathroom", "Rohrbruch hinter der Dusche, Wasser in Decke und Flur": "Burst pipe behind the shower, water in the ceiling and hall",
    "Einbruch Wohnung 2. OG": "Burglary, 2nd floor flat", "Parkschaden Tiefgarage, Kleinwagen": "Parking damage in a garage, small car",
    "Fahrertür und Schweller, Vollkasko": "Driver's door and sill, comprehensive cover", "Sturmschaden Carport": "Storm damage, carport",
    "Sturz auf Glatteis, Hausmeisterdienst": "Fall on black ice, caretaker service", "Parkrempler Tiefgarage": "Parking bump in a garage",
    "Leitungswasser Küche": "Water leak, kitchen", "Blitzschlag Dachstuhl": "Lightning strike, roof truss", "Glasbruch Wintergarten": "Broken glass, conservatory",
    "Auffahrunfall A3, Kleinwagen": "Rear-end collision on the A3, small car", "wartet auf das eGutachten GA-2026-01182": "waiting for the assessment GA-2026-01182",
    "Wildunfall L 412": "Wildlife collision on the L 412", "Heckschaden, Haftpflicht des Auffahrenden": "Rear damage, the other driver's liability",
    "Hagelschaden Pkw": "Hail damage, car", "Glasschaden Frontscheibe": "Glass damage, windscreen", "Kreuzungsunfall, Seitenschaden": "Crash at a junction, side damage",
    "Parkrempler Supermarkt": "Parking bump at a supermarket", "Marderschaden Motorraum": "Marten damage in the engine bay", "Parkschaden Tiefgarage": "Parking damage in a garage",
}

# the conversation of each demo case in English: per entry, its title and text (i18n.en.entries.<REV-id>)
EN_LINES = {'Gutachten übergeben': 'Assessment handed over',
    'Gutachten und Fotos liegen bei.': 'Assessment and photos attached.',
    'Rückfrage zum Dachfenster': 'Question about the roof window',
    'Das Dachfenster war laut Nachbar schon vor dem Hagel undicht. Soll ich es im Gutachten ausklammern oder als Vorschaden führen?': 'According to a neighbour, the roof window was already leaking before the hail. Should I leave it out of the assessment or list it as earlier damage?',
    'Besichtigung angesetzt': 'Inspection scheduled',
    'Gutachter Berger am Donnerstag 10 Uhr.': 'Assessor Berger, Thursday at 10.',
    'Fotos und Gutachten übergeben': 'Photos and assessment handed over',
    'Fünf Fotos, Feuchtemessung an drei Stellen, Gutachten als Fassung 1.': 'Five photos, moisture measured in three places, assessment as version 1.',
    'Gutachten Fassung 2': 'Assessment version 2',
    'Fotos der Decke nachgereicht, Gutachten in Fassung 2. Fassung 1 bleibt erhalten.': 'Photos of the ceiling added, assessment in version 2. Version 1 is kept.',
    'Kostenvoranschlag mit Gutachten abgeglichen': 'Estimate checked against the assessment',
    'Zwei Positionen weichen ab: Trocknung (KVA 1.840 €, Gutachten 1.420 €) und Malerarbeiten Flur (KVA 980 €, im Gutachten nicht enthalten). Die Rechnung fehlt noch; sobald sie da ist, gleiche ich alle drei ab.\n\nVorschlag mit Begründung · du entscheidest.': 'Two items differ: drying (estimate 1,840 €, assessment 1,420 €) and painting the hall (estimate 980 €, not in the assessment). The invoice is still missing; once it is in, I check all three against each other.\n\nA proposal with its reasons · you decide.',
    'Schaden aufgenommen': 'Claim recorded',
    'Vollkasko, Fahrzeug fahrbereit. Gutachten beauftragen.': 'Comprehensive cover, the car can be driven. Order the assessment.',
    'Dach und Pfosten, siehe Gutachten.': 'Roof and posts, see the assessment.',
    'Freigegeben und zur Regulierung': 'Approved for settlement',
    'Betrag wie im Gutachten.': 'Amount as in the assessment.',
    'Termin Freitag.': 'Appointment on Friday.',
    'Als reguliert gemeldet': 'Reported as settled',
    'Auftrag eingegangen': 'Order received',
    'Nordlicht Versicherung, Haftpflicht, Besichtigung beim Kunden.': "Nordlicht Versicherung, liability, inspection at the customer's.", 'Besichtigung eingeplant': 'Inspection planned',
    'Gutachter Lenz, Donnerstag.': 'Assessor Lenz, Thursday.',
    'Entwurf zur Vorprüfung': 'Draft for the pre-check',
    'Fassung 1 mit Fotos und Kalkulation.': 'Version 1 with photos and calculation.',
    'Vorprüfung abgeschlossen': 'Pre-check done',
    'Zwei Befunde: eine Position ohne Detailfoto, Wertminderung nicht ausgewiesen. Keiner spricht gegen die Freigabe; beide sollte der Gutachter sehen.\n\nBefund mit Begründung · du entscheidest.': 'Two findings: one item without a close-up photo, loss in value not stated. Neither speaks against approval; the assessor should see both.\n\nFindings with their reasons · you decide.',
    'Freigegeben und Anschreiben entwerfen': 'Approved, cover letter to be drafted',
    'Ohne Befund.': 'No findings.',
    'Anschreiben entworfen': 'Cover letter drafted',
    'Aus den Bausteinen B-01, B-07, B-08.\n\nEntwurf · ein Mensch versendet.': 'From the text blocks B-01, B-07, B-08.\n\nA draft · a person sends it.',
    'Haftpflicht, Besichtigung in der Werkstatt.': 'Liability, inspection at the garage.',
    'Fassung 1.': 'Version 1.',
    'Versendet': 'Sent',
    'Rückfrage des Versicherers': 'Question from the insurer',
    'Der Restwert ist nicht ausgewiesen. Liegen die Reparaturkosten wirklich unter der Grenze? Bitte kurz bestätigen oder Nachtrag.': 'The residual value is not stated. Are the repair costs really below the limit? Please confirm briefly or send an addendum.',
    'Gutachterin Kaya, morgen.': 'Assessor Kaya, tomorrow.',
    'Abgeschlossen': 'Closed',
    'Angebot freigegeben und Anschreiben entwerfen': 'Quote approved, letter to be drafted',
    'An den Kunden versendet': 'Sent to the customer'}


def _case(root: Path, stage: str, cid: str, meta: dict, files: dict[str, bytes | str | Path] | None = None, review: str = "") -> Path:
    d = root / stage / cid
    d.mkdir(parents=True)
    meta = {"configVersion": "1", "fictional": True, **meta}
    en = {k: EN_WORDS[str(meta[k])] for k in ("title", "subtitle") if str(meta.get(k) or "") in EN_WORDS}
    entries = {}
    for m in re.finditer(r"^## (REV-\d+) — (.*?)\n[^\n]*\n\n(.*?)(?=\n## REV-|\Z)", review or "", re.M | re.S):
        t, x = m.group(2).strip(), m.group(3).strip()
        tr = {k: EN_LINES[v] for k, v in (("title", t), ("text", x)) if v in EN_LINES}
        if tr:
            entries[m.group(1)] = tr
    if entries:
        en["entries"] = entries
    if en and "i18n" not in meta:
        meta["i18n"] = {"en": en}
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


def _signal(root: Path, sid: str, kind: str, title: str, cases: list[str], text: str, days_ago: float = 0, en: tuple[str, str] | None = None) -> None:
    """A hint from the pattern helper across files: never a finding, always with reasoning and the files it rests on.
    `en`: its title and text in English, for a viewer who reads English (title_en, and the text after `<!-- en -->`)."""
    (root / "_signale").mkdir(exist_ok=True)
    head_en = f"title_en: {en[0]}\n" if en else ""
    body_en = f"\n<!-- en -->\n{en[1]}" if en else ""
    (root / "_signale" / f"{sid}.md").write_text(f"---\nid: {sid}\nkind: {kind}\ntitle: {title}\n{head_en}cases: {', '.join(cases)}\nstatus: offen\ndate: {_stamp(days_ago)[:10]}\n---\n{text}{body_en}\n", encoding="utf-8")


def _run(root: Path, cid: str, stage: str, skill: str, status: str, minutes_ago: float, by: str, **extra) -> None:
    when = dt.datetime.now().astimezone() - dt.timedelta(minutes=minutes_ago)
    doc = {"id": f"{when.strftime('%Y%m%d-%H%M%S')}_{skill}_{cid}", "skill": skill, "container": f"{stage}/{cid}", "requested_by": by,
           "runner": "claude-code", "status": status, "created": when.isoformat(timespec="seconds"), **extra}
    (root / "_runs" / f"{doc['id']}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- the claims file (German)

CLAIMS_STAGES = ["10-meldung", "20-besichtigung", "25-abgleich", "30-pruefung", "40-regulierung", "60-abgeschlossen"]


def _mod(mid: str, kind: str, title: str, version: int, status: str, body: str, **head: str) -> str:
    lines = [f"id: {mid}", f"kind: {kind}", f"title: {title}", f"version: {version}", f"status: {status}"] + [f"{k}: {v}" for k, v in head.items() if v]
    return "---\n" + "\n".join(lines) + "\n---\n" + body + "\n"


# The claims office's rulebook (design hand-back, 2026-11-05): rules in force, letter templates, and what the AI proposes.
EN = "\n<!-- en -->\n"
CLAIMS_IN_FORCE = {
    "R-01-freigegebene-bausteine.md": _mod("R-01", "Regel", "Briefe aus Bausteinen", 2, "freigegeben",
        "Jeder Brief an Kunden nutzt freigegebene Textbausteine." + EN + "Every letter to a customer uses approved text blocks.",
        title_en="Letters from text blocks", approved_by="Geschäftsleitung", approved_by_en="Management", date="2026-09-12", source="Kommunikationsrichtlinien 2026", source_en="Communication guidelines 2026"),
    "R-02-keine-auszahlung-ohne-rechnung.md": _mod("R-02", "Regel", "Keine Auszahlung ohne Rechnung", 1, "freigegeben",
        "Ohne Rechnung wird nichts ausgezahlt." + EN + "Nothing is paid out without an invoice.",
        title_en="No payout without an invoice", areas="HR, WG", approved_by="Du", date="2026-10-30",
        source="Aus einem Gespräch mit Jana Koch, 30. Okt.", source_en="Heard in a talk with Jana Koch, 30 Oct"),
    "R-03-vier-augen-ab-5000.md": _mod("R-03", "Regel", "Vier Augen ab 5.000 €", 1, "freigegeben",
        "Ab 5.000 € Schadenhöhe gibt eine zweite Person die Regulierung frei." + EN + "From 5,000 € of damage, a second person approves the settlement.",
        title_en="Four eyes from 5,000 €", areas="WG", approved_by="Geschäftsleitung", approved_by_en="Management", date="2026-03-02", source="Vollmachtsregeln", source_en="Authority rules"),
    "B-01-anrede-und-fallbezug.md": _mod("B-01", "Baustein", "Anrede und Fallbezug", 3, "freigegeben",
        "Sehr geehrte Damen und Herren,\n\nvielen Dank für Ihre Nachricht zu {Falltitel}. Ihre Schadennummer lautet {Schadennummer}. Bitte geben Sie sie bei jeder Rückfrage an."
        + EN + "Dear {customer name},\n\nthank you for your message about {case title}. Your claim number is {claim number}. Please mention it whenever you contact us.",
        title_en="Greeting and case reference", use="Jeder Brief", use_en="Every letter", approved_by="Geschäftsleitung", approved_by_en="Management", date="2026-08-20"),
    "B-04-naechste-schritte.md": _mod("B-04", "Baustein", "Nächste Schritte nach einer Schadenmeldung", 2, "freigegeben",
        "Wir haben Ihre Schadenmeldung erhalten. So geht es weiter:\n\n1. Wir prüfen Ihren Vertrag und Ihre Angaben.\n2. Brauchen wir noch etwas, melden wir uns innerhalb von zwei Werktagen.\n3. Sobald alles vollständig ist, entscheiden wir und geben Ihnen Bescheid."
        + EN + "We have received your claim report. Here is what happens next:\n\n1. We check your policy and the details you sent.\n2. If we need anything else, we will ask you within two working days.\n3. Once everything is complete, we decide on the claim and let you know.",
        title_en="Next steps after a claim report", use="Antworten auf eine neue Schadenmeldung", use_en="Replies to a new claim", approved_by="Geschäftsleitung", approved_by_en="Management", date="2026-07-14"),
    "B-07-fehlende-unterlagen.md": _mod("B-07", "Baustein", "Anforderung fehlender Unterlagen", 1, "freigegeben",
        "Damit wir weitermachen können, brauchen wir noch: {fehlende Unterlagen}. Antworten Sie einfach auf diese Mail und hängen Sie die Unterlagen an."
        + EN + "To continue with your case, we still need the following: {missing documents}. You can simply reply to this mail with the documents attached.",
        title_en="Request for missing documents", use="Wenn ein Dokument fehlt", use_en="Whenever a document is missing", approved_by="Du", date="2026-06-03"),
    "B-09-auszahlung.md": _mod("B-09", "Baustein", "Auszahlung", 1, "freigegeben",
        "Wir überweisen {Betrag} in den nächsten drei Werktagen auf das Konto, das Sie uns genannt haben."
        + EN + "We will transfer {amount} within the next three working days to the account you gave us.",
        title_en="Payout", use="Jede Regulierung", use_en="Every settlement", approved_by="Geschäftsleitung", approved_by_en="Management", date="2026-05-19"),
}
CLAIMS_HISTORY = {
    "R-01.v1.md": _mod("R-01", "Regel", "Briefe aus Bausteinen", 1, "freigegeben",
        "Briefe an Kunden nutzen nach Möglichkeit freigegebene Textbausteine." + EN + "Letters to customers use approved text blocks where possible.",
        title_en="Letters from text blocks", approved_by="Geschäftsleitung", approved_by_en="Management", date="2026-02-01", source="Kommunikationsrichtlinien 2026", source_en="Communication guidelines 2026"),
}
CLAIMS_PROPOSED = {
    "R-10.v1.md": _mod("R-10", "Regel", "Glas ohne Gutachter", 1, "entwurf",
        "Glasschäden unter 1.000 € werden ohne Gutachter reguliert." + EN + "Glass damage under 1,000 € is settled without an assessor.",
        title_en="Glass without an assessor", areas="KFZ", drafted_by="KI", date="2026-10-28",
        source="Aus einem Gespräch mit Jana Koch, 28. Okt.", source_en="Heard in a talk with Jana Koch, 28 Oct",
        note="Gespräch mit Jana Koch: Glas unter 1.000 € zahlen wir immer direkt.  ¶  Letzte 40 Glasschäden: 38 wurden ohne Gutachter reguliert.",
        note_en="Interview, team lead: glass under 1,000 € we always pay directly.  ¶  Last 40 glass claims: 38 of 40 were settled without one."),
    "R-11.v1.md": _mod("R-11", "Regel", "Diebstahl wartet auf das Aktenzeichen", 1, "entwurf",
        "Eine Diebstahlmeldung ohne polizeiliches Aktenzeichen kann angelegt werden, die Regulierung wartet aber darauf."
        + EN + "A theft report without a police file number can be opened, but settlement waits for it.",
        title_en="Theft waits for the file number", areas="HR", drafted_by="KI", date="2026-10-29",
        source="Aus einem Gespräch mit Tobias Wendt, 29. Okt.", source_en="Heard in a talk with Tobias Wendt, 29 Oct",
        note="Gespräch mit Tobias Wendt: Ohne Aktenzeichen zahlen wir bei Diebstahl nie.", note_en="Interview, claims team: without a file number we never pay for theft."),
    "R-12.v1.md": _mod("R-12", "Regel", "Ursache bei Wasserschäden", 1, "entwurf",
        "Bei Wasserschäden über 2.000 € bestätigt ein Installateur die Ursache, bevor reguliert wird."
        + EN + "For water damage above 2,000 €, a plumber confirms the cause before it is settled.",
        title_en="The cause of water damage", areas="WG, HR", drafted_by="KI", date="2026-10-31",
        source="Aus den letzten 30 Wasserschäden", source_en="Taken from the last 30 water damage claims",
        note="Letzte 30 Wasserschäden: bei 27 lag die Bestätigung eines Installateurs vor.  ¶  Hausrichtlinie: Ursache klären, dann zahlen.",
        note_en="Last 30 water damage claims: 27 had a plumber's confirmation.  ¶  House policy: clear the cause, then pay."),
}

def _claims_rulebook(root: Path) -> None:
    (root / "_bausteine" / "_fassungen").mkdir(parents=True)
    for name, text in CLAIMS_IN_FORCE.items():
        (root / "_bausteine" / name).write_text(text, encoding="utf-8")
    for name, text in {**CLAIMS_HISTORY, **CLAIMS_PROPOSED}.items():
        (root / "_bausteine" / "_fassungen" / name).write_text(text, encoding="utf-8")


def build_claims(root: Path) -> Path:
    cfg = CONFIG / "claims-demo"
    root = _root(root, cfg, CLAIMS_STAGES)
    _claims_rulebook(root)
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
          {"label": "WG", "number": "2026-0402", "title": "Hagelschaden Reihenhaus", "reported_by": "Petra Lang, Am Hang 4", "created": _stamp(9)[:10], "subtitle": "Dachziegel und Dachfenster, Ostseite"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Hagel am Abend des 9., Ziegel gebrochen, ein Dachfenster undicht.\n", "fotos-1.jpg": photo, "gutachten.pdf": pdf, "kostenvoranschlag.pdf": kva, "rechnung.pdf": kva},
          _entry(1, "Gutachten übergeben", "Gutachter Berger", stage="20-besichtigung", when=_stamp(4, 15), files=["gutachten.pdf", "fotos-1.jpg"], text="Gutachten und Fotos liegen bei.") +
          _entry(2, "Rückfrage zum Dachfenster", "Gutachter Berger", status="open", for_="Du", stage="30-pruefung", when=_stamp(2, 9),
                 text="Das Dachfenster war laut Nachbar schon vor dem Hagel undicht. Soll ich es im Gutachten ausklammern oder als Vorschaden führen?"))

    # the AI is reconciling right now
    _case(root, "25-abgleich", "WG-2026-0421-sturmschaden-carport",
          {"label": "WG", "number": "2026-0421", "title": "Sturmschaden Carport", "reported_by": "Jonas Weber, Lindenweg 9", "created": _stamp(2)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Sturm, Carportdach abgedeckt.\n", "gutachten.pdf": pdf, "kostenvoranschlag.pdf": kva, "rechnung.pdf": kva},
          _entry(1, "Gutachten übergeben", "Gutachter Berger", stage="20-besichtigung", when=_stamp(1, 14), files=["gutachten.pdf"], text="Dach und Pfosten, siehe Gutachten.", step="demo-c21", frm="20-besichtigung", to="25-abgleich"))
    _run(root, "WG-2026-0421-sturmschaden-carport", "25-abgleich", "reconcile", "queued", 3, "du")   # the replay finishes it a few seconds after the sandbox opens

    # with the assessor
    _case(root, "20-besichtigung", "WG-2026-0425-glasbruch-wintergarten",
          {"label": "WG", "number": "2026-0425", "title": "Glasbruch Wintergarten", "reported_by": "Familie Roth, Gartenstraße 3", "created": _stamp(1)[:10], "publishDate": (dt.date.today() + dt.timedelta(days=2)).isoformat()},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Scheibe im Wintergarten gesprungen, Ursache unklar.\n"},
          _entry(1, "Besichtigung angesetzt", "Du", stage="10-meldung", when=_stamp(1, 10), text="Termin Freitag.", step="demo-2", frm="10-meldung", to="20-besichtigung"))
    _case(root, "20-besichtigung", "KFZ-2026-0811-auffahrunfall-a3",
          {"label": "KFZ", "number": "2026-0811", "title": "Auffahrunfall A3, Kleinwagen", "reported_by": "Marco Seidel", "created": _stamp(3)[:10], "gutachten_auftrag": "GA-2026-01182", "subtitle": "wartet auf das eGutachten GA-2026-01182"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Auffahrunfall im Stau, Heck und Stoßfänger.\n", "fotos-1.jpg": photo})

    # newly reported: a motor claim that orders its assessment (the hand-over into the e-report world)
    _case(root, "10-meldung", "KFZ-2026-0815-parkschaden-tiefgarage",
          {"label": "KFZ", "number": "2026-0815", "title": "Parkschaden Tiefgarage, Kleinwagen", "reported_by": "Erika Brandt", "created": _stamp(0)[:10], "subtitle": "Fahrertür und Schweller, Vollkasko"},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Beim Ausparken in der Tiefgarage an einem Betonpfeiler entlanggeschrammt. Fahrertür und Schweller. Fahrzeug fahrbereit, Fotos liegen bei.\n", "fotos-1.jpg": photo},
          _entry(1, "Schaden aufgenommen", "Du", stage="10-meldung", when=_stamp(0, 9), files=["meldung.md", "fotos-1.jpg"], text="Vollkasko, Fahrzeug fahrbereit. Gutachten beauftragen."))
    _case(root, "10-meldung", "HR-2026-0430-einbruch-wohnung",
          {"label": "HR", "number": "2026-0430", "title": "Einbruch Wohnung 2. OG", "reported_by": "Anna Vogel, Schillerstraße 21", "created": _stamp(0)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv. Balkontür aufgehebelt, Laptop und Schmuck fehlen. Polizeiliche Anzeige liegt vor.\n"})

    # in settlement and closed
    _case(root, "40-regulierung", "HP-2026-0309-sturz-glatteis",
          {"label": "HP", "number": "2026-0309", "title": "Sturz auf Glatteis, Hausmeisterdienst", "reported_by": "Hausverwaltung Sommer", "created": _stamp(20)[:10]},
          {"meldung.md": "# Schadenmeldung\n\nFiktiv.\n", "gutachten.pdf": pdf, "rechnung.pdf": kva, "abgleich.md": "# Abgleich\n\nKeine Abweichung.\n"},
          _entry(1, "Freigegeben und zur Regulierung", "Du", status="approved", stage="30-pruefung", when=_stamp(2, 9), text="Betrag wie im Gutachten.", step="demo-3", frm="30-pruefung", to="40-regulierung"))
    _signal(root, "M-001", "Wiederholung", "Gleiche Risikoanschrift in zwei Akten innerhalb von fünf Wochen",
            ["HR-2026-0417-wasserschaden-badezimmer", "HR-2026-0430-einbruch-wohnung"],
            "Musterstraße 12, 2. OG: Wasserschaden gemeldet am {a}, Einbruch gemeldet am {b}. Zwei verschiedene Schadenarten, derselbe Vertrag. Das ist kein Verdacht; es ist ein Hinweis, die zweite Akte mit Kenntnis der ersten zu lesen (Zustand der Wohnung nach der Trocknung, Zugänglichkeit).\n\n*Hinweis, keine Feststellung · ein Mensch entscheidet, ob daraus etwas folgt.*".format(a=_stamp(6)[:10], b=_stamp(0)[:10]), 0,
            en=("Same insured address in two cases within five weeks", "Musterstraße 12, 2nd floor: water damage reported on {a}, a burglary reported on {b}. Two different kinds of damage, the same policy. This is not a suspicion; it is a hint to read the second case knowing the first (the state of the flat after the drying, access).\n\n*A hint, not a finding · a person decides whether anything follows.*".format(a=_stamp(6)[:10], b=_stamp(0)[:10])))
    _signal(root, "M-002", "Abweichung", "Kostenvoranschlag 18 % über dem Üblichen für diesen Schaden",
            ["WG-2026-0402-hagelschaden-reihenhaus"],
            "Dachziegel und ein Dachfenster an einem Reihenhaus liegen hier meist bei etwa 6.200 €. Dieser Kostenvoranschlag nennt 7.300 €. Das kann am Dachfenster liegen oder an der Zufahrt; es ist ein Hinweis, die Positionen mit dem Gutachten zu lesen.\n\n*Hinweis, keine Feststellung · ein Mensch entscheidet, ob daraus etwas folgt.*", 1,
            en=("Repair estimate 18 % above the usual for this damage", "Roof tiles and one roof window on a terraced house usually come to about 6,200 € here. This estimate says 7,300 €. That may be the roof window or the access; it is a hint to read the items against the assessment.\n\n*A hint, not a finding · a person decides whether anything follows.*"))
    _signal(root, "M-003", "Dublette", "Dasselbe Foto in zwei Kfz-Akten",
            ["KFZ-2026-0815-parkschaden-tiefgarage", "KFZ-2026-0790-parkrempler"],
            "Das Foto der Fahrertür in der neuen Meldung ist dieselbe Datei wie in der abgeschlossenen Akte vom Oktober, mit derselben Aufnahmezeit. Vielleicht nur falsch angehängt, vielleicht derselbe Schaden zweimal gemeldet.\n\n*Hinweis, keine Feststellung · ein Mensch entscheidet, ob daraus etwas folgt.*", 0,
            en=("The same photo in two motor cases", "The photo of the driver's door in the new report is the same file as in the closed case from October, with the same time it was taken. Maybe just attached by mistake, maybe the same damage reported twice.\n\n*A hint, not a finding · a person decides whether anything follows.*"))
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


# The assessment office's rulebook in English, for a viewer who reads English. Letters always take the German original.
MODULES_EN = {
    "B-01": ("Liability note", "The assessment is based on the inspection of the vehicle and the documents provided. Hidden damage that only shows during the repair is not part of this assessment; on request it is valued in an addendum."),
    "B-05": ("Loss in value", "The loss in market value is worked out with the method approved in this office, from the vehicle's age, mileage, replacement value and repair costs. Below the minor-damage limit it is stated as 0 € with the reason."),
    "B-07": ("Residual value and replacement", "The replacement value is worked out from the regional market. A residual value is determined once the repair costs reach the office's limit."),
    "B-08": ("Closing line", "We are happy to answer any questions. Please quote the order number."),
    "B-10": ("Loss of use (liability)", "Loss of use per group {nu_gruppe} of the table for {nu_tage} days: repair time plus assessment and placing the order."),
    "B-11": ("Repair method", "The repair is done to the manufacturer's specifications in a specialist garage, with the parts and labour values stated in the calculation."),
    "B-12": ("No total loss", "The gross repair costs are {quote_rk|pct} of the replacement value of {wbw|eur}. They are below 60 %; no residual value is needed, and there is no economic total loss."),
    "B-13": ("Economic total loss", "The gross repair costs reach {quote_rk|pct} of the replacement value of {wbw|eur}. This is an economic total loss. Residual value {restwert|eur} (the highest of three offers from the regional market), replacement cost {wba|eur}."),
    "B-14": ("Residual value as a check", "The gross repair costs are {quote_rk|pct} of the replacement value of {wbw|eur}, above 60 %. The residual value was determined as a check ({restwert|eur}); the repair remains economical."),
    "B-15": ("Loss of use (comprehensive)", "Loss of use is not covered by comprehensive insurance. For information: group {nu_gruppe}, {nu_tage} days."),
    "B-16": ("No earlier damage", "No earlier or old damage is visible on the vehicle. The order contains no notes from the insurer's HIS."),
    "B-17": ("Earlier damage named", "Earlier and old damage, not part of this assessment: {vorschaeden_text}"),
    "B-18": ("Photo documentation", "{fotos} photos to photo standard R-02: overall views, close-ups of each calculated item, VIN, odometer."),
    "R-01": ("Earlier damage and HIS", "Every assessment names earlier and old damage, even when there is none. Notes from the insurer's HIS (the industry's information system) come with the order and are answered in the assessment; the pre-check reports any note left unanswered."),
    "R-02": ("Photo standard per kind of damage", "Required views per kind of damage: front and rear overall, both sides, VIN, odometer, each calculated item in close-up. If a view is missing, the pre-check names it; it does not decide on the item."),
    "R-03": ("A plausible calculation", "The calculation is checked against the vehicle type, the damage and the office's experience. Differences are named with their reasons; the pre-check never changes an item."),
    "R-04": ("State the loss in value", "Every assessment says something about the loss in value, even when it is 0 €."),
    "R-05": ("Four-eyes limit", "Above the office's damage limit, a second person approves. The limit is set in this rule, not in the code."),
    "R-06": ("Checking the invoice", "The invoice is laid item by item against the assessment and the calculation. The AI names the differences; the reviewer makes any cuts."),
    "R-07": ("Total loss limit and residual value", "When the repair costs reach 60 % of the replacement value, the assessor determines the residual value with three offers from the regional market (Federal Court of Justice) and states the replacement cost. From 100 % it is an economic total loss; up to 130 % a repair is possible if the owner keeps the car. The pre-check recalculates the ratio and reports a missing required part."),
}
PEOPLE_EN = {"Fachliche Leitung": "Technical lead", "Innendienst": "Back office", "Geschäftsleitung": "Management"}


def _with_english(text: str) -> str:
    """A module file with its English title, approver and text added (title_en, approved_by_en, body after `<!-- en -->`)."""
    head, body = text.split("\n---\n", 1)
    mid = re.search(r"^id: (\S+)", head, re.M).group(1)
    if mid not in MODULES_EN:
        return text
    title, body_en = MODULES_EN[mid]
    by = re.search(r"^approved_by: (.+)$", head, re.M)
    extra = f"\ntitle_en: {title}" + (f"\napproved_by_en: {PEOPLE_EN[by.group(1)]}" if by and by.group(1) in PEOPLE_EN else "")
    return head + extra + "\n---\n" + body.rstrip("\n") + f"\n<!-- en -->\n{body_en}\n"


def build_egutachten(root: Path) -> Path:
    cfg = CONFIG / "egutachten"
    root = _root(root, cfg, EGUT_STAGES)
    (root / "DEMO.md").write_text("Fiktive Gutachtenakten für die Demonstration. Jeder Name, jede Nummer und jeder Betrag ist erfunden.\n", encoding="utf-8")
    (root / "_bausteine").mkdir()
    for name, text in MODULES.items():
        (root / "_bausteine" / name).write_text(_with_english(text), encoding="utf-8")
    photo, kalk, auftrag = SAMPLES / "foto.jpg", SAMPLES / "kostenvoranschlag.pdf", SAMPLES / "gutachten.pdf"
    pruef = (cfg / "replies" / "pruefbericht-default.md").read_text(encoding="utf-8")

    # the demo path: draft and pre-check are in, you approve, the letter gets drafted, the back office sends
    c = "KH-2026-1182-auffahrunfall-a3-kleinwagen"
    _case(root, "40-fachpruefung", c,
          {"label": "KH", "number": "2026-1182", "title": "Auffahrunfall A3, Kleinwagen", "reported_by": "Marco Seidel", "created": _stamp(4)[:10], "external_id": "GA-2026-01182", "subtitle": "Heckschaden, Haftpflicht des Auffahrenden", "client": "Nordlicht Versicherung", "schaden_nr": "SN-2026-00811"},
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
    _case(root, "20-besichtigung", c, {"label": "KK", "number": "2026-1190", "title": "Parkschaden Tiefgarage", "reported_by": "Erika Brandt", "created": _stamp(1)[:10], "external_id": "GA-2026-01190", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag},
          _entry(1, "Besichtigung eingeplant", "Innendienst", stage="10-auftrag", when=_stamp(1, 9), text="Gutachterin Kaya, morgen.", step="demo-g4", frm="10-auftrag", to="20-besichtigung"))

    # the AI is pre-checking right now (the replay finishes it after the sandbox opens)
    c = "KK-2026-1203-hagelschaden-pkw"
    _case(root, "30-vorpruefung", c, {"label": "KK", "number": "2026-1203", "title": "Hagelschaden Pkw", "reported_by": "Familie Roth", "created": _stamp(3)[:10], "external_id": "GA-2026-01203", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk,
           "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-01203", car="Kombi, EZ 2021, 58.200 km", seen=_stamp(1)[:10], story="Hagel am Abend, Fahrzeug im Freien.", finding="Dach, Motorhaube und Kofferraumdeckel mit zahlreichen Dellen, keine Lackrisse.", amount="3.480 €", wm="0 €, Bagatellgrenze.")},
          _entry(1, "Entwurf zur Vorprüfung", "Gutachterin Kaya", stage="20-besichtigung", when=_stamp(0, 8), files=["gutachten.md", "kalkulation.pdf", "fotos-1.jpg"], text="Fassung 1.", step="demo-g5", frm="20-besichtigung", to="30-vorpruefung"))
    _run(root, c, "30-vorpruefung", "vorpruefung", "queued", 3, "kaya")

    # approved, the letter is drafted, the back office sends
    c = "KH-2026-1175-glasschaden-frontscheibe"
    _case(root, "50-versand", c, {"label": "KH", "number": "2026-1175", "title": "Glasschaden Frontscheibe", "reported_by": "Lukas Hartmann", "created": _stamp(6)[:10], "external_id": "GA-2026-01175", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk, "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-01175", car="Limousine, EZ 2019", seen=_stamp(4)[:10], story="Steinschlag auf der Autobahn.", finding="Frontscheibe im Sichtfeld gerissen, Austausch erforderlich.", amount="1.120 €", wm="0 €."),
           "pruefbericht.md": pruef, "anschreiben.md": (cfg / "replies" / "anschreiben-default.md").read_text(encoding="utf-8")},
          _entry(1, "Freigegeben und Anschreiben entwerfen", "Du", status="approved", stage="40-fachpruefung", when=_stamp(1, 11), text="Ohne Befund.", step="demo-g6", frm="40-fachpruefung", to="50-versand") +
          _entry(2, "Anschreiben entworfen", "KI", stage="50-versand", when=_stamp(1, 11), files=["anschreiben.md"], text="Aus den Bausteinen B-01, B-07, B-08.\n\nEntwurf · ein Mensch versendet."))

    # sent, the insurer asks, a follow-up becomes version 2
    c = "KK-2026-0902-wildunfall-landstrasse"
    _case(root, "60-versendet", c, {"label": "KK", "number": "2026-0902", "title": "Wildunfall L 412", "reported_by": "Sabine Krüger", "created": _stamp(30)[:10], "external_id": "GA-2026-00902", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk, "gutachten.md": GUTACHTEN_MD.format(order="GA-2026-00902", car="Kombi, EZ 2021, 58.200 km", seen=_stamp(27)[:10], story="Zusammenstoß mit einem Reh auf der L 412.", finding="Frontschaden: Stoßfänger, Scheinwerfer links, Motorhaube, Grill, Lüfter. Kein Rahmenschaden.", amount="4.880 €", wm="250 €."),
           "pruefbericht.md": pruef, "anschreiben.md": (cfg / "replies" / "anschreiben-default.md").read_text(encoding="utf-8")},
          _entry(1, "Versendet", "Innendienst", stage="50-versand", when=_stamp(20, 10), step="demo-g7", frm="50-versand", to="60-versendet") +
          _entry(2, "Rückfrage des Versicherers", "Nordlicht Versicherung", status="open", for_="Gutachter Lenz", stage="60-versendet", when=_stamp(1, 14),
                 text="Der Restwert ist nicht ausgewiesen. Liegen die Reparaturkosten wirklich unter der Grenze? Bitte kurz bestätigen oder Nachtrag."))

    # new order
    _case(root, "10-auftrag", "KH-2026-1210-kreuzungsunfall", {"label": "KH", "number": "2026-1210", "title": "Kreuzungsunfall, Seitenschaden", "reported_by": "Jonas Weber", "created": _stamp(0)[:10], "external_id": "GA-2026-01210", "client": "Nordlicht Versicherung"},
          {"auftrag.pdf": auftrag}, _entry(1, "Auftrag eingegangen", "Innendienst", stage="10-auftrag", when=_stamp(0, 9), files=["auftrag.pdf"], text="Haftpflicht, Besichtigung in der Werkstatt."))
    # closed
    for i, (cid, title, label, days) in enumerate([("KH-2026-1140-parkrempler", "Parkrempler Supermarkt", "KH", 12), ("KK-2026-1131-marderschaden", "Marderschaden Motorraum", "KK", 18)]):
        _case(root, "70-abgeschlossen", cid, {"label": label, "number": cid.split("-")[1] + "-" + cid.split("-")[2], "title": title, "created": _stamp(days + 8)[:10], "external_id": "GA-" + cid.split("-")[1] + "-0" + cid.split("-")[2], "publishDate": (dt.date.today() - dt.timedelta(days=days)).isoformat()},
              {"auftrag.pdf": auftrag, "fotos-1.jpg": photo, "kalkulation.pdf": kalk, "gutachten.md": GUTACHTEN_MD.format(order="GA", car="Pkw", seen=_stamp(days + 4)[:10], story="Kurzfall.", finding="Kurzfall.", amount="900 €", wm="0 €."), "pruefbericht.md": pruef},
              _entry(1, "Versendet", "Innendienst", stage="50-versand", when=_stamp(days + 1, 10), step=f"demo-gs{i}", frm="50-versand", to="60-versendet") +
              _entry(2, "Abgeschlossen", "Innendienst", stage="60-versendet", when=_stamp(days, 15), step=f"demo-gc{i}", frm="60-versendet", to="70-abgeschlossen"))
    _signal(root, "M-001", "Dublette", "Identisches Foto in zwei Gutachtenakten",
            ["KH-2026-1140-parkrempler", "KK-2026-1131-marderschaden"],
            "Foto 1 der beiden Akten ist byteweise identisch. Zwei Aufträge, zwei Fahrzeuge, dasselbe Bild: entweder vertauscht oder doppelt abgelegt. Beide Gutachten sind versendet.\n\n*Hinweis, keine Feststellung · der Prüfer entscheidet, ob ein Nachtrag nötig ist.*", 1,
            en=("Identical photo in two assessment files", "Photo 1 of both files is identical byte for byte. Two orders, two vehicles, the same picture: either swapped or filed twice. Both assessments have been sent.\n\n*A hint, not a finding · the reviewer decides whether an addendum is needed.*"))
    _signal(root, "M-002", "Wiederholung", "Gleicher Halter in zwei Aufträgen innerhalb von 60 Tagen",
            ["KH-2026-1182-auffahrunfall-a3-kleinwagen", "KK-2026-0902-wildunfall-landstrasse"],
            "Herr Beispiel, Musterstadt: Wildunfall (Kasko) vor 30 Tagen, jetzt Geschädigter eines Auffahrunfalls (Haftpflicht), zwei verschiedene Fahrzeuge. Nichts daran ist auffällig; der Hinweis spart dem Prüfer das Nachschlagen und bringt die Fotos des ersten Falls neben die des zweiten.\n\n*Hinweis, keine Feststellung · der Prüfer entscheidet.*", 0,
            en=("Same owner in two orders within 60 days", "Mr Beispiel, Musterstadt: a wildlife collision (comprehensive) 30 days ago, now the injured party in a rear-end collision (liability), two different vehicles. Nothing about it is unusual; the hint saves the reviewer the lookup and puts the photos of the first case next to those of the second.\n\n*A hint, not a finding · the reviewer decides.*"))
    return root


# ---------------------------------------------------------------------------------------------------- the inbox and the quotes
# (design hand-back, 2026-11-05): the two workspaces the design draws first. Both run on Chris's own configuration
# (config/posteingang, config/angebot); the demo only adds example content: real mails taken in by the mailbox connector,
# and quote requests whose premium the core computes from the questionnaire. Everything in German with English beside it.
INBOX_STAGES = ["10-eingang", "30-erledigt", "40-abgelegt"]
QUOTE_STAGES = ["10-anfrage", "20-rueckfrage", "30-angebot", "40-versand", "50-versendet"]
DEMO_PEOPLE = {"people": [{"id": "du", "name": "Du", "kind": "human", "roles": ["operator", "approver"]},
                          {"id": "ki", "name": "KI", "kind": "agent", "roles": []}]}


def _mail(subject: str, sender: str, address: str, body: str, days_ago: float, photo: Path | None = None, newsletter: bool = False) -> bytes:
    from email.message import EmailMessage
    from email.utils import format_datetime
    m = EmailMessage()
    m["From"] = f"{sender} <{address}>"
    m["To"] = "post@example.invalid"
    m["Subject"] = subject
    m["Date"] = format_datetime(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago))
    m["Message-ID"] = f"<{hashlib.sha1(subject.encode()).hexdigest()[:16]}@example.invalid>"
    m.set_content(body)
    if photo is not None:
        m.add_attachment(photo.read_bytes(), maintype="image", subtype="jpeg", filename="foto.jpg")
    return bytes(m)


INBOX_MAILS = [
    # (subject, sender, address, body, days ago, photo?, reading, English: (subject, body, summary, title, short))
    ("Unfall gestern Abend auf der B27, Seitenschaden", "Erika Brandt", "erika.brandt@example.invalid",
     "Guten Tag,\n\ngestern Abend hat mich auf der B27 bei Tübingen ein Transporter beim Spurwechsel seitlich gestreift. Fahrertür und hintere Tür sind eingedrückt, das Auto fährt noch. Kennzeichen TÜ-EB 118, Police KFZ 4471-2209. Fotos anbei.\n\nViele Grüße\nErika Brandt",
     3, True, {"kind": "schadensmeldung", "rule": "R-01", "summary": "Seitenschaden nach einem Spurwechsel-Unfall auf der B27. Fahrzeug fahrbereit, Fotos liegen bei.",
               "fields": {"title": "Unfall auf der B27, Seitenschaden", "summary_short": "Fahrertür und hintere Tür, TÜ-EB 118", "policy": "KFZ 4471-2209"}},
     ("Accident last night on the B27, side damage",
      "Hello,\n\nlast night on the B27 near Tübingen a van scraped the side of my car while changing lanes. The driver's door and the rear door are dented, the car still drives. Plate TÜ-EB 118, policy KFZ 4471-2209. Photos attached.\n\nKind regards\nErika Brandt",
      "Side damage after a lane-change accident on the B27. The car can be driven, photos attached.", "Accident on the B27, side damage", "Driver's door and rear door, TÜ-EB 118")),
    ("Herbstangebot: 20 % auf die Reifeneinlagerung", "Fuhrpark-Profi", "news@example.invalid",
     "Jetzt Winterreifen einlagern und 20 % sparen. Nur bis Ende November.\n\nIhr Fuhrpark-Profi-Team",
     3, False, {"kind": "werbung", "rule": "R-09", "summary": "Werbung für Reifeneinlagerung. Keine Aufgabe für uns.", "fields": {}},
     ("Autumn offer: 20 % off winter tyre storage", "Store your winter tyres now and save 20 %. Only until the end of November.\n\nYour Fuhrpark-Profi team",
      "An advert for tyre storage. No task for us.", "", "")),
    ("Kfz-Versicherung für einen neuen Skoda Octavia", "Lukas Hartmann", "lukas.hartmann@example.invalid",
     "Hallo,\n\nich hole nächste Woche einen neuen Skoda Octavia ab und möchte ihn bei Ihnen versichern, Haftpflicht und Vollkasko. Ich fahre etwa 12.000 km im Jahr, SF-Klasse 8, das Auto steht in der Garage.\n\nGruß\nLukas Hartmann",
     3, False, {"kind": "angebotsanfrage-kfz", "rule": "R-05", "summary": "Angebotsanfrage für einen neuen Skoda Octavia, Haftpflicht und Vollkasko.",
                "fields": {"title": "Skoda Octavia, Haftpflicht und Vollkasko", "summary_short": "Neuwagen, 12.000 km, SF 8, Garage", "customer": "Lukas Hartmann"}},
     ("Car insurance quote for a new Skoda Octavia",
      "Hello,\n\nI am picking up a new Skoda Octavia next week and would like to insure it with you, liability and comprehensive. I drive about 12,000 km a year, no-claims class 8, the car is kept in a garage.\n\nRegards\nLukas Hartmann",
      "A quote request for a new Skoda Octavia, liability and comprehensive.", "Skoda Octavia, liability and comprehensive", "New car, 12,000 km, class 8, garage")),
    ("Hausratversicherung für unsere neue Wohnung", "Anna Vogel", "anna.vogel@example.invalid",
     "Guten Tag,\n\nwir ziehen zum 1. Dezember in eine neue Wohnung, etwa 70 m², und brauchen eine Hausratversicherung. Was würde das kosten?\n\nAnna Vogel",
     2 / 24, False, {"kind": "angebotsanfrage-hausrat", "rule": "R-06", "summary": "Angebotsanfrage Hausrat für eine neue Wohnung, etwa 70 m², ab 1. Dezember.",
                     "fields": {"title": "Hausrat, neue Wohnung", "summary_short": "etwa 70 m², ab 1. Dezember", "customer": "Anna Vogel"}},
     ("Contents insurance for our new flat",
      "Hello,\n\nwe are moving into a new flat on 1 December, about 70 m², and need contents insurance. What would it cost?\n\nAnna Vogel",
      "A contents quote request for a new flat, about 70 m², from 1 December.", "Contents, new flat", "about 70 m², from 1 December")),
]
INBOX_LIVE = ("Wasserschaden in der Wohnung, Rohrbruch in der Dusche", "Sabine Kühn", "sabine.kuehn@example.invalid",
              "Hallo,\n\nheute früh ist hinter der Dusche ein Rohr geplatzt, das Wasser steht im Bad und läuft in den Flur. Der Installateur kommt am Nachmittag. Police HR 3390-1182.\n\nSabine Kühn",
              2 / 24, False, {"kind": "schadensmeldung-hausrat", "rule": "R-02", "summary": "Rohrbruch hinter der Dusche, Wasser in Bad und Flur. Installateur kommt heute.",
                              "fields": {"title": "Wasserschaden, Rohrbruch in der Dusche", "summary_short": "Bad und Flur, Installateur heute", "policy": "HR 3390-1182"}},
              ("Water damage in the flat, burst pipe in the shower",
               "Hello,\n\nthis morning a pipe burst behind the shower, the water is standing in the bathroom and running into the hall. The plumber comes this afternoon. Policy HR 3390-1182.\n\nSabine Kühn",
               "A burst pipe behind the shower, water in the bathroom and hall. The plumber comes today.", "Water damage, burst pipe in the shower", "Bathroom and hall, plumber today"))


def _reading(reading: dict, en: tuple) -> dict:
    _, _, summary, title, short = en
    fields = {k: v for k, v in (("title", title), ("summary_short", short)) if v}
    return {**reading, "i18n": {"en": {"summary": summary, **({"fields": {**reading.get("fields", {}), **fields}} if fields else {})}}}


def build_inbox(root: Path) -> Path:
    """The inbox: every mail is a case. The AI has read four of them and proposes a row of the rule matrix; the fifth it is reading now."""
    from ..config import DomainConfig
    from ..connectors import mailbox
    from ..store import FsStore
    cfg = CONFIG / "posteingang"
    root = _root(root, cfg, INBOX_STAGES)
    (root / "people.json").write_text(json.dumps(DEMO_PEOPLE, ensure_ascii=False, indent=2), encoding="utf-8")
    store, config = FsStore(root), DomainConfig.load(cfg, root)
    photo = SAMPLES / "foto.jpg"

    def take_in(mail: tuple, read: bool) -> str:
        subject, sender, address, body, days, with_photo, reading, en = mail
        cid, _ = mailbox.ingest(store, config, _mail(subject, sender, address, body, days, photo if with_photo else None), by="du", source="demo")
        for f in (root / "_runs").glob("*.json"):                 # the demo reads its mails itself; no order stays open
            if cid in f.read_text(encoding="utf-8"):
                f.unlink()
        meta_p = root / "10-eingang" / cid / "meta.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        entries = {"REV-001": {"title": "Mail received", "text": en[1][:600]}}
        if read:
            (root / "10-eingang" / cid / "einordnung.json").write_text(json.dumps(_reading(reading, en), ensure_ascii=False, indent=2), encoding="utf-8")
            from ..domain import step as stepping
            stepping._append_entry(store, config, cid, "10-eingang", {"author": "KI", "status": "info", "title": "Mail eingeordnet",
                                   "text": reading["summary"] + "\n\nVorschlag mit Begründung · du entscheidest."})
            entries["REV-002"] = {"title": "Mail read", "text": en[2] + "\n\nA proposal with its reasons · you decide."}
        meta["i18n"] = {"en": {"title": en[0], "entries": entries}}
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        when = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        rev = root / "10-eingang" / cid / "review.md"
        rev.write_text(re.sub(r"\*\*Date:\*\* [0-9-]+ [0-9:]+", f"**Date:** {when}", rev.read_text(encoding="utf-8")), encoding="utf-8")
        return cid

    for m in INBOX_MAILS:
        take_in(m, True)
    live = take_in(INBOX_LIVE, False)
    # the fifth mail: the AI is reading it right now; its prepared answer plays when the order runs
    from ..domain import runs as ordering
    ordering.order(store, config, live, "10-eingang", "posteingang-einordnen", "du", "", request_id=f"demo-read-{live}"[:60])
    (root / "_replies").mkdir(exist_ok=True)
    (root / "_replies" / f"einordnung-{live}.json").write_text(json.dumps(_reading(INBOX_LIVE[6], INBOX_LIVE[7]), ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "_replies" / f"posteingang-einordnen.{live}.json").write_text(json.dumps({
        "delay_s": 25, "files": {"einordnung.json": f"einordnung-{live}.json"},
        "entry": {"title": "Mail eingeordnet", "text": INBOX_LIVE[6]["summary"] + "\n\nVorschlag mit Begründung · du entscheidest."}, "model": "replay"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return root


QUOTE_KFZ_TIGUAN = dict(sf_klasse=6, sf_klasse_vk=6, fahrleistung=15000, juengster_fahrer=19, garage="nein", kasko="vollkasko")
QUOTE_KFZ_MAZDA = dict(sf_klasse=14, sf_klasse_vk=14, fahrleistung=8000, juengster_fahrer=52, garage="ja", kasko="keine")


def _form(product: str, values: dict, words: dict[str, tuple[str, str]], missing: tuple[str, ...] = ()) -> dict:
    fields = [{"id": k, "word": words.get(k, (k, k))[0], "value": v, "quote": "…"} for k, v in values.items()]
    fields += [{"id": k, "word": words.get(k, (k, k))[0], "value": None, "missing": True} for k in missing]
    return {"product": product, "fields": fields,
            "i18n": {"en": {"fields": [{**f, "word": words.get(f["id"], (f["id"], f["id"]))[1]} for f in fields]}}}


QUOTE_WORDS = {"sf_klasse": ("SF-Klasse Haftpflicht", "No-claims class, liability"), "sf_klasse_vk": ("SF-Klasse Vollkasko", "No-claims class, comprehensive"),
               "fahrleistung": ("Fahrleistung pro Jahr", "Mileage per year"), "juengster_fahrer": ("Jüngster Fahrer", "Youngest driver"),
               "garage": ("Garage", "Garage"), "kasko": ("Kasko", "Own-damage cover"), "wohnflaeche": ("Wohnfläche (m²)", "Living space (m²)"),
               "tarifzone": ("Tarifzone", "Rate zone"), "vorschaeden": ("Schäden in den letzten fünf Jahren", "Claims in the last five years"),
               "elementar": ("Elementarschutz", "Flood cover"), "fahrrad": ("Fahrrad über 1.000 €", "Bicycle over 1,000 €")}


def build_quotes(root: Path) -> Path:
    """Quote requests: one waits for answers from the customer, one is computed and waits for approval, one went out today."""
    from ..config import DomainConfig
    from ..domain import step as stepping
    from ..models import StepRequest
    from ..store import FsStore
    cfg = CONFIG / "angebot"
    root = _root(root, cfg, QUOTE_STAGES)
    (root / "people.json").write_text(json.dumps(DEMO_PEOPLE, ensure_ascii=False, indent=2), encoding="utf-8")

    # waits for the customer's answers: the AI filled what the mail said and drafted the question for the rest
    c = "HR-2026-0007-hausrat-tuebingen"
    _case(root, "10-anfrage", c, {"label": "HR", "number": "2026-0007", "title": "Hausrat, Wohnung in Tübingen", "reported_by": "Familie Neumann", "customer": "Familie Neumann",
                                  "created": _stamp(0)[:10], "subtitle": "Umzug zum 1. Dezember, etwa 85 m²",
                                  "i18n": {"en": {"title": "Contents cover, flat in Tübingen", "subtitle": "Moving on 1 December, about 85 m²"}}},
          {"anfrage.md": "# Anfrage\n\nFiktiv. Familie Neumann zieht in eine Wohnung in Tübingen und fragt nach einer Hausratversicherung.\n",
           "fragebogen.json": json.dumps(_form("HR", {"wohnflaeche": 85, "tarifzone": "2"}, QUOTE_WORDS, ("vorschaeden", "elementar", "fahrrad")), ensure_ascii=False, indent=2),
           "rueckfrage.md": "Guten Tag,\n\nfür Ihr Angebot fehlen uns noch drei Angaben: Hatten Sie in den letzten fünf Jahren Schäden? Sollen Überschwemmung und Starkregen mitversichert sein? Haben Sie ein Fahrrad im Wert von über 1.000 €?\n"},
          _entry(1, "Anfrage eingegangen", "Familie Neumann", stage="10-anfrage", when=_stamp(0, 8), files=["anfrage.md"], text="Hausrat für die neue Wohnung in Tübingen.") +
          _entry(2, "Fragebogen vorausgefüllt", "KI", stage="10-anfrage", when=_stamp(0, 9), files=["fragebogen.json", "rueckfrage.md"],
                 text="Wohnfläche und Tarifzone stehen in der Anfrage. Drei Antworten fehlen; die Rückfrage an die Kundin ist entworfen.\n\nVorschlag mit Begründung · du entscheidest."))
    meta_p = root / "10-anfrage" / c / "meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["i18n"]["en"]["entries"] = {"REV-001": {"title": "Request received", "text": "Contents cover for the new flat in Tübingen."},
                                     "REV-002": {"title": "Questionnaire prefilled", "text": "Living space and rate zone are in the request. Three answers are missing; the question to the customer is drafted.\n\nA proposal with its reasons · you decide."}}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # computed by the core from the questionnaire, waits for approval
    store, config = FsStore(root), DomainConfig.load(cfg, root)
    c = "KFZ-2026-0005-tiguan"
    _case(root, "10-anfrage", c, {"label": "KFZ", "number": "2026-0005", "title": "Tiguan, Sohn fährt mit", "reported_by": "Familie Roth", "customer": "Familie Roth",
                                  "created": _stamp(4)[:10], "subtitle": "VW Tiguan, Haftpflicht und Vollkasko, Fahrer ab 19",
                                  "i18n": {"en": {"title": "Tiguan, son also drives", "subtitle": "VW Tiguan, liability and comprehensive, drivers from 19"}}},
          {"anfrage.md": "# Anfrage\n\nFiktiv. Familie Roth möchte ihren Tiguan versichern; der Sohn (19) fährt mit.\n",
           "fragebogen.json": json.dumps(_form("KFZ", QUOTE_KFZ_TIGUAN, QUOTE_WORDS), ensure_ascii=False, indent=2)},
          _entry(1, "Anfrage eingegangen", "Familie Roth", stage="10-anfrage", when=_stamp(4, 10), files=["anfrage.md"], text="Tiguan, der Sohn fährt mit.") +
          _entry(2, "Fragebogen ausgefüllt", "KI", stage="10-anfrage", when=_stamp(4, 11), files=["fragebogen.json"], text="Alle Antworten stehen in der Anfrage."))
    stepping.step(store, config, c, StepRequest(action="calculate", step_id="demo-q1"), "du")     # the core computes the premium; the AI never does
    rev = root / "30-angebot" / c / "review.md"                   # computed four days ago, in the story
    rev.write_text(re.sub(r"(## REV-003[^\n]*\n\*\*Date:\*\* )[0-9-]+ [0-9:]+", lambda m: m.group(1) + _stamp(4, 12), rev.read_text(encoding="utf-8")), encoding="utf-8")
    meta_p = root / "30-angebot" / c / "meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta.setdefault("i18n", {}).setdefault("en", {})["entries"] = {"REV-001": {"title": "Request received", "text": "Tiguan, the son also drives."},
                                                                  "REV-002": {"title": "Questionnaire filled", "text": "Every answer is in the request."}}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # went out today
    c = "KFZ-2026-0003-mazda-2"
    _case(root, "50-versendet", c, {"label": "KFZ", "number": "2026-0003", "title": "Mazda 2, nur Haftpflicht", "reported_by": "Marco Seidel", "customer": "Marco Seidel",
                                    "created": _stamp(2)[:10], "i18n": {"en": {"title": "Mazda 2, liability only"}}},
          {"anfrage.md": "# Anfrage\n\nFiktiv. Mazda 2, nur Haftpflicht.\n", "fragebogen.json": json.dumps(_form("KFZ", QUOTE_KFZ_MAZDA, QUOTE_WORDS), ensure_ascii=False, indent=2),
           "angebot.md": "# Angebot\n\nKfz-Haftpflicht, 412,60 € im Jahr.\n", "anschreiben.md": "Sehr geehrter Herr Seidel,\n\nanbei Ihr Angebot für den Mazda 2.\n"},
          _entry(1, "Angebot freigegeben und Anschreiben entwerfen", "Du", status="approved", stage="30-angebot", when=_stamp(0, 9), step="demo-m1", frm="30-angebot", to="40-versand") +
          _entry(2, "An den Kunden versendet", "Du", status="approved", stage="40-versand", when=_stamp(0, 9), step="demo-m2", frm="40-versand", to="50-versendet"))
    return root


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]).expanduser()
    build_inbox(target / "inbox")
    build_quotes(target / "quotes")
    build_claims(target / "claims")
    build_pressroom(target / "pressroom")
    build_egutachten(target / "egutachten")
    print(f"demo worlds in {target}")
