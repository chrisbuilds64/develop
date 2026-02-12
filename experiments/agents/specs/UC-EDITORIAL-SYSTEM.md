# Use-Case: Agenten-basiertes Redaktionssystem

**Status:** KONZEPT (Diskussionsgrundlage)
**Erstellt:** 2026-02-12
**Ziel:** Content-Produktion von Idee bis Publish automatisieren -- mit Mensch an den richtigen Stellen

---

## DAS PROBLEM

Aktuell: Christian + Claude in einer Session produzieren 11 Deliverables pro Artikel.
Funktioniert, aber:
- Dauert 1-2 Stunden pro Artikel
- Qualitaet haengt von Session-Energie ab
- Kein systematisches Review (ausser manuell)
- Kein Lerneffekt zwischen Artikeln (gleiche Fehler wiederholen sich)

## DIE VISION

Ein System aus spezialisierten Agents das Content produziert, prueft und (teilweise) publiziert.
Christian ist an genau 3 Stellen aktiv -- alles andere laeuft automatisch.

## DIE 3 HUMAN HOOKS

```
HOOK 1: INPUT          Christian liefert Idee + Prosa
    |                  (Thema, Gedanken, Anekdoten, Stimmung)
    v
[--- AGENT PIPELINE ---]
    |
    v
HOOK 2: REVIEW         Christian bewertet das Ergebnis
    |                  (Liest Drafts, gibt Feedback)
    |
    +--> "Nochmal" --> [REFINEMENT LOOP] --> zurueck zu HOOK 2
    |
    +--> "Passt" ----> HOOK 3
    |
    v
HOOK 3: PUBLISH        Christian gibt Freigabe
                       (Publish / Schedule / Hold)
```

Alles zwischen den Hooks = Agents.
Christian steuert WAS und WANN. Agents machen WIE.

## DIE AGENT-PIPELINE (KISS-Version)

### Phase 1: Briefing (nach Hook 1)

**Agent: Strategist**
- Input: Christians Rohidee + Prosa
- Tut: Angle schaerfen, Track zuordnen, Hook-Varianten, Key Points
- Output: Structured Briefing

### Phase 2: Produktion (automatisch)

**Agent: Writer**
- Input: Briefing + Content Rules + Brand Voice Examples
- Tut: Substack Draft im Logbook-Format schreiben
- Output: substack.md

**Agent: LinkedIn Voice**
- Input: Briefing + Substack Draft (als Referenz, NICHT als Vorlage)
- Tut: Eigene LinkedIn-Erzaehlung + First Comment
- Output: linkedin-post.txt, first-comment.txt

**Agent: Package Builder**
- Input: Substack + LinkedIn Post
- Tut: Restliche Deliverables ableiten (TikTok Script, DALL-E Prompt, meta.json, Title SVGs, LinkedIn Article)
- Output: Komplettes 11-File-Paket

### Phase 3: QA (automatisch)

**Agent: QA Analyst (AG-001 -- existiert bereits!)**
- Input: Komplettes Paket
- Tut: Review gegen alle Regeln
- Output: QA Review mit READY/NEEDS WORK/HOLD

### Phase 4: Review (Hook 2)

Christian bekommt:
- Alle Drafts
- QA Review
- Editorial Notes

Christian entscheidet:
- **"Passt"** -> weiter zu Hook 3
- **"Nochmal, [Feedback]"** -> Feedback geht zurueck in Refinement

### Phase 5: Refinement (bei Bedarf)

**Agent: Refiner**
- Input: Bestehende Drafts + Christians Feedback
- Tut: Gezielte Ueberarbeitung basierend auf Feedback
- Output: Ueberarbeitetes Paket -> zurueck zu QA -> zurueck zu Hook 2

### Phase 6: Publish (Hook 3)

Christian gibt Freigabe. Dann:

**Stufe A (jetzt):** Christian postet manuell
**Stufe B (spaeter):** Agent posted auf Befehl ("Post jetzt")
**Stufe C (noch spaeter):** Agent posted Routine-Content selbst (z.B. Campaign Posts)

---

## KISS-VORSCHLAG: WENIGER AGENTS

Die Pipeline oben hat 5+ Agents. Das ist die VISION.
Fuer den Start empfehle ich 3:

```
[Briefing + Writing Agent]  <-- EIN Agent der beides kann
         |
         v
[Package Builder Agent]     <-- Mechanisch: leitet restliche Files ab
         |
         v
[QA Agent (AG-001)]         <-- Existiert bereits
```

**Warum?**
- Ein guter System Prompt kann Strategist + Writer + LinkedIn Voice in EINEM Agent vereinen
- Separate Personas lohnen sich erst wenn nachweislich ein Agent die Qualitaet nicht schafft
- Package Builder ist zu 80% Template-Arbeit (meta.json, SVGs, TikTok) -- das braucht kaum AI
- QA Agent ist schon fertig

**3 statt 6 Agents. Gleicher Output. Halb so komplex.**

---

## AUTONOMIE-STUFEN (Roadmap)

| Stufe | Was der Mensch tut | Was Agents tun | Wann |
|-------|-------------------|----------------|------|
| **1. Assisted** | Idee + Review + Publish | Drafts + QA | JETZT |
| **2. Supervised** | Review + Freigabe | Alles andere inkl. Scheduling | Wenn Qualitaet bewiesen |
| **3. Autonomous** | Nur bei neuem Content-Typ | Routine-Posts selbst (Campaigns, Reposts) | Spaeter |

**Regel:** Aufsteigen nur wenn die vorherige Stufe zuverlaessig funktioniert.
Stufe 3 nur fuer Content der bereits Template-basiert ist (WARMTH Campaign Scripts, LinkedIn Article Crosspost).
Nie fuer neuen Original-Content.

---

## DATEN-ARCHITEKTUR

```
inbox/                  <-- Christians Input (Idee + Prosa)
  YYYY-MM-DD_slug.md

pipeline/               <-- Zwischenergebnisse
  YYYY-MM-DD_slug/
    briefing.md
    substack-draft.md
    linkedin-post.txt
    ...
    qa-review.md
    editorial-notes.md
    status.json         <-- { "phase": "review", "iteration": 1 }

output/                 <-- Finale, freigegebene Pakete
  DAY-XXX-slug/
    [alle 11 Deliverables]

archive/                <-- Abgeschlossene Pipelines (fuer Learning)
```

**status.json** trackt wo jeder Artikel in der Pipeline steht.
Kein Workflow-Engine noetig -- Files + Status reicht.

---

## LERN-LOOP (Langfristig)

```
QA Reviews    ──┐
Metriken      ──┼──> [Learning Agent] ──> Aktualisierte Regeln
Feedback      ──┘
```

Der Learning Agent (AG-002 Fix Collector + AG-004 Performance Analyst) analysiert:
- Welche Fixes werden immer wieder vorgeschlagen? -> Regel anpassen
- Welcher Content performed gut? -> Muster erkennen
- Welches Feedback gibt Christian wiederholt? -> System Prompt verbessern

Das ist Phase 2. Erst wenn die Grundpipeline stabil laeuft.

---

## KOSTEN-SCHAETZUNG (pro Artikel)

| Agent | Modell | Geschaetzte Tokens | Kosten |
|-------|--------|-------------------|--------|
| Briefing + Writing | Sonnet | ~8K in / ~4K out | ~$0.05 |
| Package Builder | Haiku | ~3K in / ~2K out | ~$0.005 |
| QA Analyst | Sonnet | ~6K in / ~3K out | ~$0.04 |
| **Gesamt** | | | **~$0.10/Artikel** |

Zum Vergleich: Eine Claude-Code-Session fuer denselben Artikel kostet $0.50-2.00.
10x guenstiger bei vergleichbarer Qualitaet.

---

## OFFENE FRAGEN (zur Diskussion)

1. **Personas vs. ein Agent?** Lena/Marcus/Sarah/Tom als separate Agents -- oder ein Agent der in Phasen denkt? KISS sagt: Ein Agent, ausser er liefert nachweislich schlechtere Qualitaet.

2. **Wo lebt das System?** Lokal (Scripts + Cron) oder im Backend (FastAPI Endpoints)? Stufe 1 = lokal. Ab Stufe 2 = Backend.

3. **Wie kommt Christians Input rein?** Markdown-File in inbox/? Telegram Message? CLI Prompt? Einfachste Variante: Markdown-File.

4. **Wie bekommt Christian das Review?** Terminal? Email? Telegram? File im pipeline/ Ordner?

5. **Wann lohnt sich Stufe 3 (Autonomous)?** Erst wenn 20+ Artikel durch die Pipeline gelaufen sind und die Qualitaet konsistent ist.
