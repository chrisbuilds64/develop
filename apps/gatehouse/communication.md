```
path:        develop/apps/gatehouse/communication.md
type:        communication · discussion before decision (append-only, newest at end)
purpose:     Design questions and open findings for the Gatehouse elicitation harness.
maintained:  Axel proposes; Chris decides. DISC numbers issued by Axel only.
```

# Gatehouse — Communication

Append-only. Newest at end. Discussion before a decision; decisions move to an ADR.

---

## **DISC-001 — A recorded marker does not say whether anyone chose it**

**2026-08-27 · Axel · OPEN**

**Where this came from.** A reader responded on LinkedIn to the post about the first
run, in which fifty-three of fifty-five answers came back marked `is`. He reached the
same conclusion we published in Field Notes 074, independently, and then went one step
further than we did.

His formulation:

> unresolved state was allowed to inherit resolved state.
> unknown -> default(is) -> recorded as is
> Nobody had to lie. The representation did it for them.
> So perhaps the more general rule is: don't just record the answer. Record enough
> state that the answer cannot silently become something it never was.

**Why this is not the same finding as FN-074.** The article fixes the problem by asking
which option should be free, and the answer there is that the free option must be the
weakest claim, not the strongest. That is a fix at input time and it is correct as far
as it goes.

His point is about what survives in storage. An answer actively marked `is` and an
answer left at a default `is` are indistinguishable in `run.json` once the run is over.
Both read as a claim. Only one of them was made by a person. Six months later nobody
can tell them apart, which is precisely the failure the marker was built to prevent,
reappearing one layer down.

**What that means concretely.** The marker is currently a value. It needs to be a value
plus its provenance:

- `marker` — `is` / `proposed` / `open`
- `marker_source` — `explicit` (the respondent selected it) or `default` (it was never
  touched)

`interview.md` should render the difference rather than hide it, because that file is
the one humans read. `audit.jsonl` does not cover this today; it records outbound model
calls, not the provenance of answers.

**Open, for Chris.**

1. Does provenance apply only to the marker, or to every answer field where a default
   exists?
2. Does a default-valued marker block the exit criteria of its block, the way a
   `VIOLATED` carry-forward constraint blocks an asset run? That would make the
   distinction operational rather than merely visible.
3. Attribution: the finding is a third party's and develop/ is a public repository, so
   he is unnamed here (CONTENT-BOUNDARIES rule 4). If he agrees to be named, this entry
   gets his name. The private record of who this was lives in `community/`.

**Not implemented. No code changed.**

---

## **DISC-002 — Was drei Tage Kommentare über den Fragebogen sagen**

**2026-08-27 · Axel · OPEN**

**Herkunft.** Fünf Kommentare auf SP-012 und SP-013 innerhalb von drei Tagen. Die Reichweite war klein, die Ausbeute nicht: **jeder einzelne Kommentar hat etwas über das Produkt gesagt, das der Echtlauf vom 23.08. nicht gezeigt hat.** Chris-Einordnung dazu: die Reaktionen sind wenige, aber durchweg qualitativ; dasselbe gilt für die Podcast-Rückmeldungen. Das ist die Begründung, warum Feldreaktionen hier als Entwicklungsinput geführt werden und nicht nur als Reichweitenzahl.

Drei Punkte betreffen den Pack direkt. Zwei weitere betreffen Positionierung und Briefing und liegen dort.

---

### 1. Fehlende Regel in `[directions]`: nach dem Vorrang fragen, nicht nach dem Versäumnis

**Der stärkste der drei Punkte, weil er jede einzelne Antwort betrifft.**

Regel 3 lautet heute *"Failures are worth more than successes. Structure sits where things broke."* Das ist richtig und bleibt. Ohne eine zweite Regel daneben produziert sie aber **Rechtfertigung statt Information**: wer gefragt wird, warum etwas nicht dokumentiert wurde, verteidigt sich; wer gefragt wird, was stattdessen Vorrang hatte, erzählt.

Vorschlag als neue Regel:

> "Never ask why something was not done. Ask what took precedence."

**Woher der Punkt kommt.** Eine Leserin widersprach der These von SP-013, Modelle hätten gelernt, wo Menschen aufgeben. Ihr Einwand: fast niemand hört aus Mangel an Beharrlichkeit auf. Man hört auf, weil eine Frist kommt, ein Kunde zufrieden ist oder ein Workaround für die Aufgabe reicht. Übertragen auf das Interview heißt das: **jedes Loch in der Dokumentation hat eine Ursache, die keine Charakterfrage ist.** Ein Fragebogen, der das nicht unterstellt, bekommt schlechtere Antworten.

Nebenbefund für die Editorial-Seite, hier nur als Vermerk: der Hook von SP-013 verstößt gegen ESSAY-POSITIONING (Blame, Layer 4). Steht im `review.md` des Containers.

### 2. Der Default muss die schwächste Behauptung sein — und zwar überall, nicht nur beim Marker

DISC-001 behandelt die Herkunft des Markers. Dieser Punkt liegt daneben und ist breiter.

Ein Kommentar zum Null-Island-Fall brachte die Verallgemeinerung: **ungültige Defaults werden gefangen, gültige werden still zum Record.** 0,0 übersteht jede Validierung, weil es eine legale Koordinate ist. Nichts wirft, nichts ist malformed, und das System sagt nicht "could not geocode", sondern "here it is" — mit derselben Zuversicht wie bei einer echten Antwort.

Für den Pack heißt das: **jedes Feld mit einem plausiblen Vorgabewert ist betroffen, nicht nur `is/proposed/open`.** Regel: keine vorbelegten Antworten, nirgends. Wo ein Default unvermeidlich ist, muss er die schwächste Behauptung sein, die das Feld zulässt.

Das ist der Echtlauf-Befund (53 von 55) in seiner allgemeinen Form.

### 3. Zwei neue Trigger

Beide aus Kommentaren von Praktikern, beide zielen auf Dinge, die niemand freiwillig erzählt.

```
[[trigger]]
cue = "they name a rule or a policy"
ask = "What happens when someone does not follow it? Who finds out, and how?"
seeks = "whether the rule is enforced or merely written"
```

**Herkunft:** ein Software Architect berichtete von einem 100k-Zeilen-Projekt mit Coding-Agenten. Seine Repo-Regeln hatten in beiden dokumentierten Vorfällen nichts bewirkt: schwächere Modelle konnten ihnen nicht folgen, stärkere brauchten sie nicht. **Eine Regel, die nur dort hält, wo sie nicht gebraucht wird, ist keine Regel.** Der bestehende Trigger auf Qualitätskriterien deckt das für Kriterien ab, nicht für Regeln und Richtlinien.

```
[[trigger]]
cue = "they describe a change that shipped"
ask = "What did not get updated along with it?"
seeks = "the consumer that quietly gets skipped"
```

**Herkunft:** ein Entwickler mit dreiunddreißig Jahren in derselben Firma. Sein Befund: was die Entwicklung bremst, ist immer ein einzelner Konsument, der am schwersten zu refaktorieren ist. Weil man nicht ewig entwickeln kann, beginnt man ihn zu überspringen. *"Nothing really breaks but maintenance becomes harder and harder."* **Der Trigger ist wertvoll, weil es kein Ereignis gibt, an das sich jemand erinnert.** Niemand erzählt von der Aktualisierung, die nicht stattgefunden hat.

---

**Offen, für Chris.**

1. Gehen alle drei Punkte in den Pack, oder erst Punkt 1 und 2 und die Trigger nach dem nächsten Echtlauf?
2. Punkt 2 verlangt eine Durchsicht **aller** Felder auf Vorgabewerte, nicht nur des Markers. Jetzt oder zusammen mit DISC-001?
3. Regel 1 und die bestehende Regel 3 stehen in Spannung zueinander (Fehler sind wertvoll / nicht nach dem Versäumnis fragen). Das ist beabsichtigt, sollte aber in den `[directions]` als Paar sichtbar sein, damit ein Interviewer die Absicht sieht.

**Attribution.** Alle vier Personen sind Dritte, `develop/` ist public, daher unbenannt (CONTENT-BOUNDARIES Regel 4). Zuordnung privat in `community/interactions/linkedin-interactions.md`, Eintrag 2026-08-27.

**Nicht implementiert. Kein Pack geändert.**
