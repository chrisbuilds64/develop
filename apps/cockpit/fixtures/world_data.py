"""The two demo worlds as data: the content pipeline (en) and the claims assessor (de).

Every title, name and case is invented. A piece is a dict:
  stage, name, meta, files {name: text | None (generated) | "PNG"}, review [entries], runs [runs]
make.py turns it into folders. `D` carries the dates, computed from today.
"""
import json
from pathlib import Path

import world_texts as T

HERE = Path(__file__).resolve().parent


def P(stage, name, meta, files=None, review=None, runs=None, series_of=None):
    return {"stage": stage, "name": name, "meta": meta, "files": files or {}, "review": review or [], "runs": runs or []}


def M(label, number, title, track, created=None, publish=None, series=None, origin=None, subtitle=None):
    d = {"label": label, "number": number, "title": title, "track": track}
    if series:
        d["series"] = series
    if publish:
        d["publishDate"] = publish
    if created:
        d["created"] = created
    if origin:
        d["origin"] = origin
    if subtitle:
        d["subtitle"] = subtitle
    return d


def R(skill, status, minutes_ago, cost=None, note=None, by="alex", turns=None, secs=None, model="claude-opus-5-5"):
    return dict(skill=skill, status=status, minutes_ago=minutes_ago, cost=cost, note=note, by=by, turns=turns, secs=secs, model=model)


def E(date, author, status, title, text, for_=None, resolves=None):
    e = {"date": date, "author": author, "status": status, "title": title, "text": text}
    if for_:
        e["for"] = for_
    if resolves:
        e["resolves"] = resolves
    return e


def _vocab_base():
    return json.loads((HERE / "vocabulary.base.json").read_text(encoding="utf-8"))


# =============================================================== content world (en)
def content(D):
    A, N, MAYA = "Alex", "Claude", "Maya"
    pieces = [
        # ---- 10 ideas
        P("10-ideas", "FN-047-the-audit-nobody-reads", M("FN", "047", "The audit nobody reads", "provocative", D.ago(2), origin="Alex, notes from a client audit"),
          {"source.md": "# The audit nobody reads\n\nA client has a yearly audit report of 80 pages. Nobody on the team can say what changed since last year. Idea: what an audit looks like when it is written to be diffed, not read.\n"}),
        P("10-ideas", "POD-048-the-handoff-problem", M("POD", "048", "The handoff problem", "deep-tech", D.ago(1), origin="Alex, voice memo"),
          {"script.md": "# The handoff problem\n\nRough script, brought in by hand.\n\n1. Two teams, one handoff, no owner.\n2. What the receiving side actually needs: a name, a state, a next step.\n3. A handoff is a file, not a meeting.\n"}),
        P("10-ideas", "WN-009-notes-on-friction", M("WN", "009", "Notes on friction", "weekend-notes", D.ago(4), origin="Sam, weekend thoughts"),
          {"source.md": "# Notes on friction\n\nWhen is friction a feature? Three examples from this week: the confirm dialog, the second reviewer, the waiting day.\n"},
          runs=[R("interpret", "failed", 55, cost=0.31, turns=9, secs=88.0, note="Start from the three examples.")]),
        # ---- 15 / 20
        P("15-interpretation", "FN-045-what-the-pilot-taught-us", M("FN", "045", "What the pilot taught us", "business", D.ago(6), origin="Alex, pilot debrief"),
          {"source.md": "# What the pilot taught us\n\nDebrief notes from the six-week pilot: what we expected, what happened, what we would change.\n",
           "interpretation.md": "# Interpretation (working)\n\nThe finding is not the result of the pilot but how long it took to see it.\n"},
          runs=[R("interpret", "running", 4, note="Take the debrief notes as the base.")]),
        P("20-produce", "SP-032-the-fourth-reviewer", M("SP", "032", "The fourth reviewer", "business", D.ago(7)),
          {"linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": None},
          runs=[R("interpret", "done", 190, cost=0.92, turns=14, secs=171.4)]),
        # ---- 30 review
        P("30-review-human", "FN-043-the-review-that-reads-itself", M("FN", "043", "The review that reads itself", "deep-tech", D.ago(5), subtitle="Why a green log measures agreement, not quality", origin="Alex, a week of agent self-review"),
          {"substack.md": T.ESSAY, "linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": None, "validation.md": "# Validation\n\n- Form: 5 checks passed (length, structure, tone, links, headings)\n- Facts: 1 open question, see review.md REV-003\n"},
          review=[
              E(D.stamp(3, 9, 40), A, "open", "Tighten the opening", "The first paragraph says the same thing twice. Cut to the second sentence and keep the one-week detail.", for_=N),
              E(D.stamp(3, 11, 5), N, "resolved", "Opening rewritten in v2", "Cut the first paragraph to two sentences and moved the one-week detail up. The rest is unchanged.", for_=A, resolves="REV-001"),
              E(D.stamp(2, 16, 20), N, "open", "Check the claim in the sixth paragraph", "The paragraph says the agent rounds numbers toward the story. That comes from your three weeks of notes, not from a log I can read. Please confirm the wording before it goes out.", for_=A),
          ],
          runs=[R("interpret", "done", 4300, cost=2.4, turns=31, secs=412.6, note="Make it an essay, not a report.")]),
        P("30-review-human", "POD-ARC-02-the-arc-spoken", M("POD", "ARC-02", "The Arc, Spoken", "deep-tech", D.ago(9), publish=D.nthu_after, series="ARC"),
          {"script.md": T.SCRIPT, "teleprompter.txt": T.TELEPROMPTER, "show-notes.txt": T.SHOWNOTES},
          review=[
              E(D.stamp(4, 10, 0), N, "info", "Script, teleprompter and show notes ready", "Derived the teleprompter and the show notes from the script. The script itself is unchanged.", for_=A),
              E(D.stamp(3, 14, 30), A, "approved", "Script approved", "Read it aloud twice. Good as it stands."),
          ],
          runs=[R("derive", "done", 5600, cost=1.1, turns=18, secs=205.0)]),
        P("30-review-human", "FN-041-the-long-one", M("FN", "041", "The Long One", "business", D.ago(12), publish=D.nmon_after),
          {"substack.md": "# The Long One\n\nA placeholder for a longer essay.\n"}),
        # ---- 40
        P("40-asset-generation", "SP-033-the-intern-that-never-sleeps", M("SP", "033", "The intern that never sleeps", "provocative", D.ago(10)),
          {"linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": "# Visual brief\n\nA night-time office with one lit desk and an empty chair. Cool blue, one warm lamp. No people.\n"},
          review=[E(D.stamp(1, 15, 0), A, "approved", "Text approved", "Text is final. Over to Maya for the image.", for_=MAYA)]),
        P("40-asset-generation", "POD-045-the-silent-failure", M("POD", "045", "The silent failure", "deep-tech", D.ago(14)),
          {"script.md": None, "teleprompter.txt": None, "show-notes.txt": None, "visual-brief.md": None, "thumbnail-16x9.png": "PNG:#2f6fed:#0b1b4a"},
          review=[E(D.stamp(6, 15, 0), A, "approved", "Script approved", "Recorded and approved."),
                  E(D.stamp(0, 9, 30), MAYA, "info", "Thumbnail uploaded", "First version is in the folder. Tell me if the crop is wrong.", for_=A)]),
        # ---- 50
        P("50-ready-to-publish", "FN-040-the-boring-governance-win", M("FN", "040", "The boring governance win", "business", D.ago(18)),
          {"substack.md": "# The boring governance win\n\nThe best result of the quarter was a rule nobody argued about.\n", "linkedin-post.txt": None, "first-comment.txt": None, "header-16x9.png": "PNG:#2fa36b:#0c3b27"},
          review=[E(D.stamp(8, 12, 0), A, "approved", "Text approved", "Good."), E(D.stamp(1, 10, 10), A, "approved", "Image approved", "The image works.")],
          runs=[R("interpret", "done", 12000, cost=1.9, turns=22, secs=260.0)]),
        # ---- 55
        P("55-scheduled", "FN-042-seven-checks-before-merge", M("FN", "042", "Seven checks before merge", "deep-tech", D.ago(20), publish=D.nmon),
          {"substack.md": "# Seven checks before merge\n\nA short list, in the order they are run.\n", "linkedin-post.txt": None, "first-comment.txt": None, "header-16x9.png": "PNG:#8a5cf6:#2a1767"},
          runs=[R("interpret", "done", 16000, cost=2.1, turns=27, secs=330.0)]),
        P("55-scheduled", "SP-034-the-handover-note", M("SP", "034", "The handover note", "business", D.ago(15), publish=D.nthu),
          {"linkedin-post.txt": None, "first-comment.txt": None, "linkedin-image.png": "PNG:#e0a52a:#5a3d05"}),
        # ---- 60 published
        P("60-published", "FN-ARC-01-the-first-arc", M("FN", "ARC-01", "The First Arc", "deep-tech", publish=D.back[2], series="ARC"), {"substack.md": None}),
        P("60-published", "SP-021-the-queue-is-the-product", M("SP", "021", "The queue is the product", "business", publish=D.back[3]), {"linkedin-post.txt": None}),
        P("60-published", "FN-GOV-02-the-human-gate-is-a-file", M("FN", "GOV-02", "The human gate is a file", "deep-tech", publish=D.back[4], series="GOV"), {"substack.md": None}),
        P("60-published", "SP-014-the-short-one", M("SP", "014", "The Short One", "business", publish=D.back[5]), {"linkedin-post.txt": None}),
        P("60-published", "POD-038-what-the-runner-forgot", M("POD", "038", "What the runner forgot", "deep-tech", publish=D.back[6]), {"script.md": None}),
        P("60-published", "WN-007-notes-from-a-quiet-week", M("WN", "007", "Notes from a quiet week", "weekend-notes", publish=D.back[7]), {"substack.md": None}),
        P("60-published", "FN-GOV-01-who-signs-the-agent-output", M("FN", "GOV-01", "Who signs the agent output", "deep-tech", publish=D.back[9], series="GOV"), {"substack.md": None}),
        P("60-published", "SP-019-ten-minutes-of-review", M("SP", "019", "Ten minutes of review", "provocative", publish=D.back[10]), {"linkedin-post.txt": None}),
        P("60-published", "FN-035-pipelines-are-not-prompts", M("FN", "035", "Pipelines are not prompts", "deep-tech", publish=D.back[12]), {"substack.md": None}),
        P("60-published", "WN-006-the-week-the-tests-lied", M("WN", "006", "The week the tests lied", "weekend-notes", publish=D.back[13]), {"substack.md": None}),
        # ---- 61
        P("61-field-observation", "FN-039-the-cost-of-a-yes", M("FN", "039", "The cost of a yes", "provocative", publish=D.back[1]), {"substack.md": None, "linkedin-post.txt": None}),
        P("61-field-observation", "SP-024-one-file-per-decision", M("SP", "024", "One file per decision", "business", publish=D.back[0]), {"linkedin-post.txt": None}),
    ]
    series = {
        "ARC": {"label": "ARC", "title": "The Arc", "spine": "One idea, told three ways, in an order that builds.", "status": "running", "editor": "alex",
                "sourced_by": ["alex", "sam"], "created": D.ago(10),
                "pieces": [{"ref": "FN-ARC-01", "role": "the finding"}, {"ref": "POD-ARC-02", "role": "the finding, spoken"}, {"ref": "SP-ARC-03", "role": "the hook, last"}]},
        "GOV": {"label": "GOV", "title": "Governance, in practice", "spine": "Two essays on who signs what, and one short post to close.", "status": "running", "editor": "alex",
                "sourced_by": ["alex"], "created": D.ago(70),
                "pieces": [{"ref": "FN-GOV-01", "role": "the question"}, {"ref": "FN-GOV-02", "role": "the answer"}, {"ref": "SP-GOV-03", "role": "the summary"}]},
    }
    v = _vocab_base()                                # no groups/product/helpers: the tests expect the locale words
    return {
        "people": [{"id": "alex", "name": "Alex", "kind": "human"}, {"id": "sam", "name": "Sam", "kind": "human"},
                   {"id": "claude", "name": "Claude", "kind": "agent"}, {"id": "maya", "name": "Maya", "kind": "human"}],
        "agent": "Claude", "placeholders": True, "pieces": pieces, "series": series, "vocabulary": v, "artifacts": json.loads((HERE / "artifacts.json").read_text(encoding="utf-8")),
        "meta_labels": ["FN", "POD", "SP", "WN"], "meta_tracks": ["deep-tech", "provocative", "business", "weekend-notes"], "cover": None,
    }


# ============================================================== claims world (de)
def claims(D):
    A, N, J = "Alex", "Nova", "Jonas Weber"
    pieces = [
        # ---- 10 Eingang
        P("10-ideas", "KFZ-0820-auffahrunfall-a3-golf-vii", M("KFZ", "0820", "Auffahrunfall A3, Golf VII", "standard", D.ago(1), origin="Meldung per Portal"),
          {"source.md": "# Schadenmeldung\n\nAuffahrunfall auf der A3 bei Beispielstadt, Fahrzeug VW Golf VII, Kennzeichen XX-AB 1234 (erfunden). Heckschaden, Fahrer unverletzt, Polizei nicht vor Ort.\n"}),
        P("10-ideas", "HAUS-0420-rohrbruch-erdgeschoss-reihenhaus", M("HAUS", "0420", "Rohrbruch Erdgeschoss, Reihenhaus", "komplex", D.ago(2), origin="Meldung per Telefon"),
          {"script.md": "# Besichtigungsprotokoll (Vorab)\n\nVor Ort aufgenommen vom Regulierer. Rohrbruch in der Küche, Boden und Unterschränke durchnässt, Trocknung bereits begonnen. Fotos folgen.\n"}),
        P("10-ideas", "KFZ-0821-motorschaden-nach-reparatur", M("KFZ", "0821", "Motorschaden nach Reparatur", "komplex", D.ago(4), origin="Meldung per Mail"),
          {"source.md": "# Schadenmeldung\n\nMotorschaden drei Wochen nach einer Reparatur in einer Vertragswerkstatt. Streitig ist, ob der Schaden auf die Reparatur zurückgeht.\n"},
          runs=[R("interpret", "failed", 55, cost=0.28, turns=8, secs=74.0, note="Streitpunkt zuerst benennen.")]),
        # ---- 15 / 20
        P("15-interpretation", "HAUS-0419-brand-dachstuhl-einfamilienhaus", M("HAUS", "0419", "Brand im Dachstuhl, Einfamilienhaus", "eilig", D.ago(3), origin="Meldung per Telefon"),
          {"source.md": "# Schadenmeldung\n\nBrand im Dachstuhl nach Blitzeinschlag, Feuerwehr war vor Ort. Teilräumung des Obergeschosses.\n", "interpretation.md": "# Aufbereitung (Entwurf)\n\nUrsache voraussichtlich Blitzeinschlag, Nachweis durch Feuerwehrbericht offen.\n"},
          runs=[R("interpret", "running", 4, note="Feuerwehrbericht einbeziehen.")]),
        P("20-produce", "KFZ-0818-seitenschaden-parkplatz-audi-a4", M("KFZ", "0818", "Seitenschaden Parkplatz, Audi A4", "standard", D.ago(6)),
          {"linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": None},
          runs=[R("interpret", "done", 190, cost=0.88, turns=13, secs=160.2)]),
        # ---- 30 Gutachten liegt vor
        P("30-review-human", "HAUS-0416-wasserschaden-badezimmer", M("HAUS", "0416", "Wasserschaden Badezimmer, Mehrfamilienhaus", "komplex", D.ago(7), subtitle="Ursache: defekte Wannenfuge, kein Rohrbruch", origin="Meldung per Portal"),
          {"substack.md": T.GUTACHTEN, "linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": None, "validation.md": "# Prüfprotokoll\n\n- Form: 5 Prüfungen bestanden (Aufbau, Länge, Anrede, Anlagen, Aktenzeichen)\n- Inhalt: 1 offene Frage, siehe Anmerkungen REV-003\n"},
          review=[
              E(D.stamp(3, 9, 40), A, "open", "Ursache klarer formulieren", "Der Abschnitt Ursache soll früher sagen, dass kein Rohrbruch vorliegt. Bitte vorziehen.", for_=N),
              E(D.stamp(3, 11, 5), N, "resolved", "Ursache vorgezogen", "Die Feststellung steht jetzt im ersten Satz des Abschnitts. Der Rest ist unverändert.", for_=A, resolves="REV-001"),
              E(D.stamp(2, 16, 20), N, "open", "Schadenhöhe: Annahme bitte bestätigen", "Die 6.800 Euro beruhen auf dem Angebot des Fliesenlegers, das nur mündlich vorliegt. Bitte bestätigen, ob die Zahl so in das Gutachten soll.", for_=A),
          ],
          runs=[R("interpret", "done", 4300, cost=2.4, turns=29, secs=388.0, note="Als Gutachten, nicht als Bericht.")]),
        P("30-review-human", "HAUS-HGL-02-hagelschaden-reihenhaus-ostring", M("HAUS", "HGL-02", "Hagelschaden Reihenhaus Ostring", "standard", D.ago(9), publish=D.nthu_after, series="HGL"),
          {"script.md": T.BESICHTIGUNG, "teleprompter.txt": "Gesprächsnotiz für den Rückruf beim Eigentümer\n\nDach: zwölf Steine auf der Südseite beschädigt.\nFassade: Ursache der Putzschäden offen.\nNächster Schritt: Angebot des Dachdeckers, Nachholtermin für Fassadenfotos.\n", "show-notes.txt": "Anlagen\n\n1. Fotodokumentation Dach (14 Aufnahmen)\n2. Fotodokumentation Innen (24 Aufnahmen)\n3. Wetterdaten zum Ereignis\n"},
          review=[
              E(D.stamp(4, 10, 0), N, "info", "Protokoll, Gesprächsnotiz und Anlagen liegen vor", "Gesprächsnotiz und Anlagenverzeichnis sind aus dem Protokoll abgeleitet. Das Protokoll selbst ist unverändert.", for_=A),
              E(D.stamp(3, 14, 30), A, "approved", "Protokoll freigegeben", "Passt so, kann in die Akte."),
          ],
          runs=[R("derive", "done", 5600, cost=1.0, turns=16, secs=190.0)]),
        P("30-review-human", "HAUS-0414-sturmschaden-garage", M("HAUS", "0414", "Sturmschaden Garage", "standard", D.ago(12), publish=D.nmon_after),
          {"substack.md": "# Gutachten (Entwurf)\n\nPlatzhalter für ein längeres Gutachten.\n"}),
        # ---- 40
        P("40-asset-generation", "KFZ-0816-unfallflucht-rueckwaertsfahrer", M("KFZ", "0816", "Unfallflucht, Rückwärtsfahrer", "eilig", D.ago(10)),
          {"linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": "# Fotoauftrag\n\nFahrzeugheck aus drei Winkeln, Lackspuren in Nahaufnahme, Parksituation von der Straße aus. Kennzeichen unkenntlich machen.\n"},
          review=[E(D.stamp(1, 15, 0), A, "approved", "Kurzbericht freigegeben", "Text steht. Jonas, bitte die Fotos.", for_=J)]),
        P("40-asset-generation", "HAUS-0415-einbruchschaden-wohnung", M("HAUS", "0415", "Einbruchschaden, Wohnung 2. OG", "standard", D.ago(14)),
          {"script.md": None, "linkedin-post.txt": None, "first-comment.txt": None, "visual-brief.md": None, "header-16x9.png": "PNG:#2fa36b:#0c3b27"},
          review=[E(D.stamp(6, 15, 0), A, "approved", "Protokoll freigegeben", "Erledigt."),
                  E(D.stamp(0, 9, 30), J, "info", "Fotos hochgeladen", "Erste Serie liegt im Ordner. Bitte sagen, falls ein Winkel fehlt.", for_=A)]),
        # ---- 50
        P("50-ready-to-publish", "HAUS-0410-sturmschaden-gartenhaus", M("HAUS", "0410", "Sturmschaden Gartenhaus", "standard", D.ago(18)),
          {"substack.md": "# Gutachten\n\nSturmschaden am Gartenhaus, Schadenhöhe 2.300 Euro.\n", "linkedin-post.txt": None, "first-comment.txt": None, "header-16x9.png": "PNG:#2fa36b:#0c3b27"},
          review=[E(D.stamp(8, 12, 0), A, "approved", "Gutachten freigegeben", "In Ordnung."), E(D.stamp(1, 10, 10), A, "approved", "Fotos freigegeben", "Die Fotos reichen.")],
          runs=[R("interpret", "done", 12000, cost=1.7, turns=20, secs=240.0)]),
        # ---- 55
        P("55-scheduled", "KFZ-0812-totalschaden-motorrad", M("KFZ", "0812", "Totalschaden Motorrad", "komplex", D.ago(20), publish=D.nmon),
          {"substack.md": "# Gutachten\n\nWiederbeschaffungswert 6.400 Euro, Restwert 900 Euro.\n", "linkedin-post.txt": None, "first-comment.txt": None, "header-16x9.png": "PNG:#8a5cf6:#2a1767"},
          runs=[R("interpret", "done", 16000, cost=2.0, turns=26, secs=310.0)]),
        P("55-scheduled", "HAFT-0309-sturz-auf-glatteis-hausmeister", M("HAFT", "0309", "Sturz auf Glatteis, Hausmeisterdienst", "komplex", D.ago(15), publish=D.nthu),
          {"linkedin-post.txt": None, "first-comment.txt": None, "header-16x9.png": "PNG:#e0a52a:#5a3d05"}),
        # ---- 60 abgeschlossen
        P("60-published", "HAUS-HGL-01-hagelschaden-lagerhalle-nord", M("HAUS", "HGL-01", "Hagelschaden Lagerhalle Nord", "standard", publish=D.back[2], series="HGL"), {"substack.md": None}),
        P("60-published", "KFZ-0811-parkrempler-tiefgarage-ford-fiesta", M("KFZ", "0811", "Parkrempler Tiefgarage, Ford Fiesta", "standard", publish=D.back[3]), {"linkedin-post.txt": None}),
        P("60-published", "HAUS-0407-leitungswasser-keller-mfh", M("HAUS", "0407", "Leitungswasser Keller, Mehrfamilienhaus", "komplex", publish=D.back[4]), {"substack.md": None}),
        P("60-published", "KFZ-0809-wildunfall-b27-skoda-octavia", M("KFZ", "0809", "Wildunfall B27, Skoda Octavia", "standard", publish=D.back[5]), {"linkedin-post.txt": None}),
        P("60-published", "HAFT-0306-sturz-auf-gehweg-streupflicht", M("HAFT", "0306", "Sturz auf Gehweg, Streupflicht", "komplex", publish=D.back[6]), {"script.md": None}),
        P("60-published", "HAUS-0404-rohrbruch-dachgeschoss", M("HAUS", "0404", "Rohrbruch Dachgeschoss", "eilig", publish=D.back[7]), {"substack.md": None}),
        P("60-published", "KFZ-0802-auffahrunfall-a8-vw-passat", M("KFZ", "0802", "Auffahrunfall A8, VW Passat", "standard", publish=D.back[9]), {"linkedin-post.txt": None}),
        P("60-published", "HAFT-0301-hundebiss-gartenzaun", M("HAFT", "0301", "Hundebiss am Gartenzaun", "komplex", publish=D.back[10]), {"script.md": None}),
        P("60-published", "HAUS-0399-sturmschaden-carport", M("HAUS", "0399", "Sturmschaden Carport", "standard", publish=D.back[12]), {"substack.md": None}),
        P("60-published", "KFZ-0795-glasbruch-frontscheibe-kia-ceed", M("KFZ", "0795", "Glasbruch Frontscheibe, Kia Ceed", "standard", publish=D.back[13]), {"linkedin-post.txt": None}),
        # ---- 61 abgeschlossen, Nachlauf
        P("61-field-observation", "KFZ-0814-vorfahrtsverletzung-kreuzung-b10", M("KFZ", "0814", "Vorfahrtsverletzung Kreuzung B10", "komplex", publish=D.back[1]), {"substack.md": None, "linkedin-post.txt": None}),
        P("61-field-observation", "HAFT-0308-baustelle-schaden-nachbargrundstueck", M("HAFT", "0308", "Baustelle, Schaden am Nachbargrundstück", "komplex", publish=D.back[0]), {"linkedin-post.txt": None}),
    ]
    series = {
        "HGL": {"label": "HGL", "title": "Hagelereignis Raum Beispielstadt", "spine": "Ein Unwetter, drei Fälle: Halle, Reihenhaus, Fahrzeug.", "status": "running", "editor": "alex",
                  "sourced_by": ["alex", "sam"], "created": D.ago(25),
                  "pieces": [{"ref": "HAUS-HGL-01", "role": "Gewerbe"}, {"ref": "HAUS-HGL-02", "role": "Wohngebäude"}, {"ref": "KFZ-HGL-03", "role": "Fahrzeug"}]},
    }
    vocab = {
        "de": {
            "product": "Schadenakte",
            "journey": {"idea": "Eingang", "work": "Aufbereitung", "review": "Gutachten", "visual": "Fotos", "date": "Termin", "out": "Abgeschlossen"},
            "words": {                                   # the desk's own locale keys, said the way a claims office says them
                "app.tagline": "Jeder Fall, vom Eingang bis zum Abschluss.",
                "desk.lead.one": "Ein Fall wartet auf dich.", "desk.lead.many": "{n} Fälle warten auf dich.",
                "desk.lead.clear": "Kein Fall wartet auf dich.", "desk.lead.sub": "Alle anderen laufen.",
                "desk.new_piece": "Neuer Fall", "desk.field.format": "Schadenart", "desk.ph.title": "Kurzbezeichnung, z. B. Auffahrunfall A3, Golf VII",
                "desk.ph.text": "Was ist passiert, wer meldet, was liegt schon vor", "field.idea_text": "Die Schadenmeldung",
                "desk.artifacts_have": "Was schon vorliegt", "desk.act.keep": "Fall anlegen", "desk.empty": "Noch kein Fall. Leg den ersten an.",
                "desk.act.interpret": "Aufbereiten lassen", "desk.act.to_review": "Zur Prüfung", "desk.act.read": "Gutachten lesen",
                "desk.act.approve": "Gutachten freigeben", "desk.act.approve_image": "Fotos freigeben", "desk.act.schedule": "Termin setzen",
                "desk.act.published": "Abgeschlossen melden", "desk.state.running": "wird gerade aufbereitet",
                "desk.state.material": "Besichtigungsprotokoll liegt vor, der Rest fehlt", "desk.state.open_notes": "{n} Rückfrage(n) an dich offen",
                "desk.draft": "Das Gutachten", "desk.no_text": "Noch kein Gutachten. Es entsteht im nächsten Schritt.",
                "desk.notes": "Rückfragen", "desk.notes_empty": "Keine Rückfragen.", "desk.note.write": "Rückfrage stellen",
                "desk.ask": "Den Sachbearbeiter-Agenten bitten", "desk.nothing_now": "Gerade nichts zu tun — der Fall ist unterwegs.",
                "desk.nameless": "{n} Akten ohne Deckblatt liegen in der Werkstatt.",
            },
            "labels": {"KFZ": "Kfz-Schaden", "HAUS": "Gebäudeschaden", "HAFT": "Haftpflichtfall"},
            "stages": {"10-ideas": "Eingang", "15-interpretation": "wird aufbereitet", "20-produce": "wird aufbereitet", "30-review-human": "Gutachten liegt vor",
                       "40-asset-generation": "beim Partner, Fotos", "50-ready-to-publish": "fertig, Termin wählen", "55-scheduled": "Termin steht",
                       "60-published": "abgeschlossen", "61-field-observation": "abgeschlossen, Nachlauf"},
            "files": {"source.md": "Schadenmeldung", "interpretation.md": "Aufbereitung", "substack.md": "Gutachten (Entwurf)", "linkedin-post.txt": "Kurzbericht an den Versicherer",
                      "first-comment.txt": "Anschreiben", "script.md": "Besichtigungsprotokoll", "teleprompter.txt": "Gesprächsnotiz", "show-notes.txt": "Anlagenverzeichnis",
                      "visual-brief.md": "Fotoauftrag", "validation.md": "Prüfprotokoll", "review.md": "Anmerkungen", "meta.json": "Steckbrief",
                      "header-16x9.png": "Fotodokumentation", "linkedin-image.png": "Fotodokumentation (Kurzbericht)"},
            "groups": {"you": "Wartet auf dich", "working": "In Prüfung", "akhil": "Beim Fotopartner", "planned": "Terminiert", "ideas": "Eingang", "out": "Abgeschlossen"},
            "helpers": {"interpret": "Gutachten aufbereiten", "canonical-review": "Qualitätsprüfung", "reflect": "Beobachtung festhalten", "derive": "Rest erzeugen", "asset": "Fotos anfordern"},
        },
        "en": {
            "product": "Claims File",
            "journey": {"idea": "Received", "work": "Preparation", "review": "Assessment", "visual": "Photos", "date": "Date", "out": "Closed"},
            "labels": {"KFZ": "Motor claim", "HAUS": "Building claim", "HAFT": "Liability case"},
            "stages": {"10-ideas": "received", "15-interpretation": "being prepared", "20-produce": "being prepared", "30-review-human": "assessment ready",
                       "40-asset-generation": "with the partner, photos", "50-ready-to-publish": "done, pick a date", "55-scheduled": "date set",
                       "60-published": "closed", "61-field-observation": "closed, follow-up"},
            "files": {"source.md": "Claim notice", "interpretation.md": "Preparation", "substack.md": "Assessment (draft)", "linkedin-post.txt": "Short report to the insurer",
                      "first-comment.txt": "Cover letter", "script.md": "Inspection report", "teleprompter.txt": "Call note", "show-notes.txt": "List of enclosures",
                      "visual-brief.md": "Photo order", "validation.md": "Check log", "review.md": "Notes", "meta.json": "Record",
                      "header-16x9.png": "Photo documentation", "linkedin-image.png": "Photo documentation (short report)"},
            "groups": {"you": "Waiting for you", "working": "Under review", "akhil": "With the photo partner", "planned": "Dated", "ideas": "Received", "out": "Closed"},
            "helpers": {"interpret": "Prepare the assessment", "canonical-review": "Quality check", "reflect": "Capture an observation", "derive": "Produce the rest", "asset": "Order photos"},
        },
    }
    art = json.loads((HERE / "artifacts.json").read_text(encoding="utf-8"))
    fmt_fn, fmt_pod = art["formats"]["FN"], art["formats"]["POD"]
    art["formats"] = {"KFZ": {"primary": "script.md", "artifacts": [x for x in fmt_pod["artifacts"] if x["file"] not in ("teleprompter.txt", "show-notes.txt", "edit-instructions.txt", "reel-hooks.txt")
                                                                     and x["stage"] != "40-asset-generation"] + [{"file": "header-16x9.png", "stage": "40-asset-generation", "by": "akhil"}]},
                      "HAUS": {"primary": "script.md", "artifacts": [x for x in fmt_pod["artifacts"] if x["file"] not in ("edit-instructions.txt", "reel-hooks.txt")
                                                                     and x["stage"] != "40-asset-generation"] + [{"file": "header-16x9.png", "stage": "40-asset-generation", "by": "akhil"}]},
                      "HAFT": {"primary": "substack.md", "artifacts": [x for x in fmt_fn["artifacts"] if x["stage"] != "40-asset-generation"] + [{"file": "header-16x9.png", "stage": "40-asset-generation", "by": "akhil"}]}}
    return {
        "people": [{"id": "alex", "name": "Alex", "kind": "human"}, {"id": "sam", "name": "Sam", "kind": "human"},
                   {"id": "jonas", "name": "Jonas Weber", "kind": "human"}, {"id": "nova", "name": "Nova", "kind": "agent"},
                   {"id": "claude", "name": "Claude", "kind": "agent"}],
        "agent": "Nova", "pieces": pieces, "series": series, "vocabulary": vocab, "artifacts": art,
        "meta_labels": ["KFZ", "HAUS", "HAFT"], "meta_tracks": ["standard", "komplex", "eilig"],
        "cover": {"track": {"standard": "#2f6fed", "komplex": "#8a5cf6", "eilig": "#d9534f"},
                  "label": {"KFZ": "Kfz-Schaden", "HAUS": "Gebäudeschaden", "HAFT": "Haftpflicht"}, "fallback": "#5a6270"},
    }
