# The Case, Not the Diagram — positioning video, about 90 seconds

Brief for the animation. Written 2026-10-29 for Akhil, from the comparison of casefile with BPM systems
(`control/planning/2026-10-29_casefile-gegen-bpm.md`, internal). Same form as the canon video next door
(`../kanon/script.md`): no speaker, the on-screen text carries; a voiced cut can use the same sentences. English
first; a German cut is a decision for Chris (the canon video was German, for the insurance audience).

## What the video has to do

Two things, in this order: **position** (what casefile is, in the viewer's own words), then **draw the line** (what it
is not, so nobody measures it against the wrong thing). The viewer we picture knows workflow software from the inside:
a claims handler, an assessor who runs an office, a head of operations who has seen a process diagram. They should
finish the video able to say: *"It is a case file with gates. The AI drafts, a person seals. The files are mine."*

Honesty is part of the position (our rule "Show the Machine"): we did not invent stages, gates and rules, and the
video says so. The difference is in four things, and only those four get a scene each.

## Visual grammar (from the product, keep it)

- **Colour has meaning or it is grey.** Blue only for "this waits for you". The seal colour (`--seal`, a deep red)
  only for "decided, it holds now". Everything missing is **dashed**, never coloured.
- **The AI is never a face.** A dashed outline, a soft glow, a chip reading `AI`. It hands things over; it never presses
  a button and never stamps.
- **People press, stamp, carry.** Every decision in the picture is a hand.
- **The case is a folder** (the gold folder from the carexpert PoC may return), **a stage is a shelf**, **a gate is a
  door with a stamp beside it**, **the canon is a bound book**.
- No logos, no vendor names, no screenshots of other products. The diagram in scene 1 is generic: boxes, diamonds,
  arrows, a dot running along them.
- All names and documents on screen come from the invented worlds (Falk & Partner, Nordlicht). No customer, no
  partner, no real person.
- No confetti, no points, no faces of real people. Calm. One thing on screen at a time.

## Script

| Time | Picture | Text on screen (EN) · German below |
|---|---|---|
| 0–8 s | A process diagram draws itself: boxes, diamonds, arrows. A small dot starts running along the arrows, faster and faster. A tiny label in the corner reads `workflow`. | **Most work software is a diagram.** The work is a dot running through it. · *Die meiste Arbeitssoftware ist ein Diagramm. Die Arbeit ist ein Punkt, der hindurchläuft.* |
| 8–16 s | The diagram sinks into a grey database cylinder. Three people stand in front of it, looking at a blank wall. One of them holds a printout and shrugs. | **The state lives in a database only the machine can read.** · *Der Zustand liegt in einer Datenbank, die nur die Maschine lesen kann.* |
| 16–24 s | Hard cut. A single folder on a desk. It opens: documents, a running thread of notes, a date, a stamp. The camera moves in; everything inside is legible. | **We started from the other end. The case.** The folder is the status. Open it, and you see everything. · *Wir haben am anderen Ende angefangen. Bei der Akte. Der Ordner ist der Status. Öffne ihn, und du siehst alles.* |
| 24–34 s | A wall of six shelves; the folder sits on the third. Beside it a door with a stamp, a small rule table, and a paper strip unrolling with one line per step. Each lights up once as it is named, then settles. | **Stages. Gates. Rules. A record of every step.** We did not invent these. Every good process has them. · *Stufen. Tore. Regeln. Ein Protokoll jedes Schritts. Das haben wir nicht erfunden. Jeder gute Prozess hat das.* |
| 34–44 s | A person lifts the folder off the shelf, tucks it under their arm and walks out of the door. Outside, they open it on a park bench. It still reads. | **1 · Your cases are files you own.** Take them with you. Read them without us. · *1 · Deine Akten sind Dateien, die dir gehören. Nimm sie mit. Lies sie ohne uns.* |
| 44–54 s | At the gate: the dashed AI figure places a sheet marked `proposal` beside the door, with two lines highlighted. A person reads it, then presses the stamp. The seal lands in deep red. The AI steps back. | **2 · The AI proposes. A person decides.** Always. The seal says who. · *2 · Die KI schlägt vor. Ein Mensch entscheidet. Immer. Das Siegel sagt, wer.* |
| 54–64 s | A bound book in the centre: the canon. Lines run from it to four dashed AI figures of different shapes; as each line connects, the figure straightens, as if bound. (Continuity with the canon video.) | **3 · One canon for every AI in the house.** Readable by people, binding for machines. · *3 · Ein Kanon für jede KI im Haus. Lesbar für Menschen, bindend für Maschinen.* |
| 64–74 s | Inside the folder, one document in three versions, stacked: `v1`, `v2`, `v3`. Each carries a small chip: `human` (filled) · `AI-assisted, checked by M.K.` (half) · `AI` (dashed). The current one is bold; the older two sit behind it, still reachable. | **4 · Every version says who made it.** Human. AI-assisted. AI. Nothing is hidden. · *4 · Jede Fassung sagt, wer sie gemacht hat. Mensch. KI-unterstützt. KI. Nichts ist versteckt.* |
| 74–86 s | Split screen. Left: a factory hall, a conveyor belt, thousands of identical grey boxes rushing past, fading. Right: a desk, one folder open, one blue button, one hand. The left half dims to grey; the right half stays. | **Not a workflow factory for ten thousand cases a day.** A desk where one person decides the next case. · *Keine Prozessfabrik für zehntausend Fälle am Tag. Ein Schreibtisch, an dem ein Mensch die nächste Akte entscheidet.* |
| 86–94 s | End card. The folder, closed, calm. Below it the wordmark. | **casefile** · The case that leads itself. · Case management for the people who decide. · ChrisBuilds64 · *Die Akte führt sich selbst.* |

## What every sentence rests on (so nobody has to ask)

| Sentence | Where it is true in the product |
|---|---|
| The folder is the status | A case is a folder inside a stage folder; moving it is the step (ADR-013) |
| Stages, gates, rules, record | `stages.json`, actions with `requires`, the rule matrix `regeln.json`, `review.md` and the step journal |
| Files you own, read them without us | Folders synced to the person's own machine; no database; a customer can take the tree away (ADR-013, alternative rejected) |
| The AI proposes, a person decides | `25-abgleich` and the inbox helper write proposals and never act; every gate is a human role (ADR-022, ADR-024) |
| The seal says who | A gate passed is a thread entry with the person's name, stamped in the seal colour |
| One canon, binding for machines | Foundation principle 13; the canon is loaded into every agent run as context |
| Every version says who made it | Provenance per version: who, when, level (human · AI-assisted, checked by · AI); design rule C11 |
| Not for ten thousand cases a day | One writer, a lock per case, a file tree: built for hundreds of cases per desk, not for a mass-processing department |

Nothing on screen promises a feature that does not exist. If a scene needs a claim that is not in this table, ask
before drawing it.

## Open for Chris

1. **Language of the first cut:** English (default for public content) or German first, like the canon video.
2. **The word "BPM":** the script avoids it and shows the diagram instead. Saying "BPM" once (scene 1 label) would
   help viewers who think in that term, and risks sounding like an attack on a category. Decision needed.
3. **Where it goes first:** LinkedIn (burned-in subtitles, no sound needed) or the demo page next to the canon video.
