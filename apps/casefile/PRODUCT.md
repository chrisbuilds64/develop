# Product

<!-- impeccable:product-schema 1 -->

Written 2026-10-20 for the cockpit's desk; carried over 2026-10-21 to casefile, the rebuilt product (Bauplan
`control/planning/2026-10-21_pressroom-zielarchitektur-bauplan.md`). The product is the case that leads itself;
PressRoom is its first application, the claims file its demo. Lines marked *assumption* were not confirmed by a person.

## Platform

web

## Users

**Primary: the content creator who does not know the machine.** Akhil (execution partner: edit,
thumbnails, YouTube) and Chris on a phone between client meetings. They think in pieces and in
what happens to a piece next, never in folders, labels, skills or stage numbers. Frequency: a
few times a day, short visits, one decision per visit.

**Secondary: the prospect watching a five-minute demo.** A claims assessor (Kfz-Gutachter) who
runs a case-handling business and wants to see how a process is carried by this system, so he
can picture his own case flow in it. He does not want to see technology. He wants to recognise
his own work in the shape of ours. *Assumption:* he watches over Chris's shoulder on a laptop
or projector, not on his own device.

**Tertiary: the experienced creator (Chris) who switches to the workshop view** for the kanban
by stage, series, calendar, runs and every raw action. That view exists and stays as it is.

## Product Purpose

PressRoom turns an idea or a finished script into a published piece through a fixed sequence
of stages, with AI helpers doing the drafting and checking and humans holding the gates. The
cockpit is the surface over it: it shows what the tools know and owns none of their data.

Success on the desk: a person enters an idea or uploads material, has it worked out, reads the
draft and the notes, answers, approves, picks a date, and reports it published, without ever
asking what a folder, a skill or a label is. Success for the demo: the prospect can say in his
own words how a case of his would run through the same steps.

## Positioning

The process is the product. Every stage is a folder on disk, every gate is a person, every
helper run is a signed order with a cost. Nothing is hidden in a database; the whole thing is
inspectable files that a customer could own. A neighbouring product shows a dashboard over its
own database; this one shows the actual working folder of the operation.

## Operating Context

- Data: one pipeline folder (`flow/`) synced through Nextcloud; stages are `NN-name` folders,
  pieces are subfolders with `meta.json`, artifacts and a `review.md` thread. Helpers are
  ordered as JSON files in `_runs/` and executed by a runner elsewhere.
- Tools write; the cockpit never does. Every button runs a tool (`idea_new.py`, `move.py`,
  `review_append.py`, `run_request.py`, `schedule.py`, `asset_put.py`).
- Vocabulary is data: `vocabulary.json` at the pipeline root says what the desk calls labels,
  stages and files; `artifacts.json` says which artifacts a format collects at which stage.
- Two views on one data set: the desk (creator) and the workshop (operator). Switch top right.
- Stack: FastAPI, Jinja templates, HTMX as a file, one stylesheet, Inter self-hosted. No build
  step, no Node at runtime. Demo mode runs on fixtures only.
- Languages: German and English via locale files; the demo for the prospect runs in German.

## Capabilities and Constraints

- The six steps a piece takes: idea or material → worked out by a helper → draft read, notes
  answered, approved → visual by the partner → date chosen → reported published, then resonance.
- The state rule (concept §7): a running helper, a failed run, an open note addressed to me,
  then the stage decide the group and the one button. It lives once, in the reader.
- Roles and rights are out of scope for now (Chris, 13.10.: everyone may do everything).
- Publishing itself happens outside (Buffer); the desk only takes the report.
- Visuals are made by the partner; the desk shows them when they arrive.
- The workshop view and every tool contract stay untouched by this work.
- *Assumption:* the demo must run offline from fixtures, with pieces in every state, so that
  nothing real and nothing client-related is on screen.
- *Assumption:* the claims variant is the same code with a different vocabulary and a different
  fixture world; no new mechanism.

## Brand Commitments

Product name on screen: **PressRoom** for the content pipeline, **Schadenakte** for the claims demo; the engine has no name on screen. Colour: blue, and only for 'this waits for you' (Chris, 2026-10-21). Type: sans only, Instrument Sans and IBM Plex Mono (Chris, 2026-10-21). Brand
label elsewhere is ChrisBuilds64. Voice: short, plain, the person's own words; the machine's
names (stage folders, labels, file names) do not appear on the desk. Dark appearance is the
incumbent default with a derived light mode; both must hold.

## Evidence on Hand

- Working implementation: `cockpit/templates/desk.html`, `piece.html`, `cockpit/static/cockpit.css`,
  reader in `cockpit/plugins/pipeline/reader.py`.
- Demo fixtures: `fixtures/make.py` builds an invented world; it currently has few pieces and
  no notes, runs or visuals, so most desk states cannot be shown from it yet.
- Real pipeline: 40 published pieces, 7 in review, 5 with the partner (2026-10-06 count). Not
  for the demo.
- No testimonials, no customer names, no numbers for the prospect. Do not invent any.

## Product Principles

1. One screen says what is next, and one button does it.
2. Words, never codes: no stage name, label or file name reaches the desk.
3. Progress is visible as a path, so a person always knows where a piece is and what remains.
4. Nothing is hidden: every file of a piece is reachable from its page.
5. The demo is the product: what the prospect sees is the real surface on invented data.

## Accessibility & Inclusion

Keyboard focus visible, contrast at 4.5:1 for text, touch targets usable on a phone (390px),
German as primary demo language.
