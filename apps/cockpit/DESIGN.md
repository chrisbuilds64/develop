---
name: PressRoom Cockpit
description: A blue-black desk where each piece is a cover on a shelf with a six-dot path and one button.
colors:
  ground: "#030712"
  slate: "#0b1220"
  slate-raised: "#111a2e"
  line: "#1e293b"
  ink: "#f1f5f9"
  ink-quiet: "#94a3b8"
  ink-faint: "#64748b"
  accent: "#3b82f6"
  accent-soft: "#60a5fa"
  accent-ink: "#ffffff"
  ok: "#22c55e"
  warn: "#f59e0b"
  bad: "#ef4444"
  light-ground: "#f8fafc"
  light-slate: "#ffffff"
  light-slate-raised: "#f1f5f9"
  light-line: "#e2e8f0"
  light-ink: "#0f172a"
  light-ink-quiet: "#475569"
  light-ink-faint: "#94a3b8"
  cover-deep-tech: "#2f6fed"
  cover-provocative: "#e0a52a"
  cover-business: "#2fa36b"
  cover-weekend-notes: "#8a5cf6"
  cover-fallback: "#5a6270"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 750
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 800
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.012em"
  body:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  prose:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.08em"
  shelf:
    fontFamily: "Inter, ui-sans-serif, -apple-system, 'Segoe UI', system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 650
    letterSpacing: "0"
  mono:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "0.92em"
rounded:
  s: "8px"
  m: "12px"
  pill: "999px"
spacing:
  gap: "16px"
  page: "24px"
  page-mobile: "16px"
  shelf: "30px"
  shelf-row: "26px 32px"
  card: "18px 20px 16px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-primary-piece:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.pill}"
    padding: "10px 20px"
  button-small:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  quiet-link:
    backgroundColor: "transparent"
    textColor: "{colors.ink-quiet}"
    padding: "0"
  input:
    backgroundColor: "{colors.slate-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.s}"
    padding: "7px 10px"
  input-date:
    backgroundColor: "{colors.slate-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "7px 12px"
  surface-card:
    backgroundColor: "{colors.slate}"
    textColor: "{colors.ink}"
    rounded: "{rounded.m}"
    padding: "18px 20px 16px"
  badge:
    backgroundColor: "{colors.slate-raised}"
    textColor: "{colors.ink-quiet}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  rail-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-faint}"
    rounded: "{rounded.m}"
    size: "42px"
---

# Design System: PressRoom Cockpit

## Overview

**Creative North Star: "The Night Desk"**

One stylesheet, tokens first. The ground is blue-black (`ground`), surfaces are slate a step
lighter, text is cool off-white in three strengths, and one blue does all the pointing. Inter is
the only face and it is bundled; the page makes no request outside its own origin. Light mode is
the same tokens re-valued, not a second design.

Two surfaces share the system and differ in posture. The **workshop** (older: `.card`, `.kcol`,
`.cal`, `.matrix`, `.block`) is an operator's board: bordered slate cards on a tonal grid, small
uppercase tracked labels, status tones (ok / warn / bad) on bars, badges and dots. The **desk**
(newest: `.desk`, `.shelf`, `.pc`, `.path`, `.journey`, `.prose`) is a creator's start page:
pieces are generated covers laid on the bare ground without card chrome, state is a sentence in
plain words, a six-dot path shows the way, and one filled button per piece says what is next.
Where they differ, the desk is the newer intent; the workshop is kept as it is.

**Key Characteristics:**
- Dark primary, slate layering, almost no shadows except under covers.
- One sans (Inter variable), weights from 400 body to 800 brand.
- Blue accent reserved for the one action, the current step and focus.
- On the desk, the covers bring the colour; everything else is ink on slate.
- Secondary actions are quiet text, never a second filled button.

## Colors

A cool slate ramp from near-black to off-white, one blue, three status tones, and a small set
of cover hues that come from the data, not the stylesheet.

### Primary
- **Accent Blue** (`accent`): the filled button, the current dot on the path, links, focus
  outlines (as `accent-soft`), the "+" intake disc, the current matrix column at 10% mix.
- **Accent Soft** (`accent-soft`): the brand mark emphasis, the running pulse, focus rings,
  skill names in the matrix header, kanban tags.

### Neutral
- **Ground** (`ground`): the page. On the desk, shelves and covers sit directly on it.
- **Slate** (`slate`): cards, the top bar, the rail, the journey box, the prose column, notes.
- **Slate Raised** (`slate-raised`): inputs, selects, badges, the rail's active item.
- **Line** (`line`): every 1px border and divider; path connectors between undone dots.
- **Ink / Ink Quiet / Ink Faint** (`ink`, `ink-quiet`, `ink-faint`): primary text; state
  sentences, shelf headings, labels; kind lines, dates, counts, done and hollow dots.
- **Light derivation**: `light-*` values replace the six neutrals under `[data-theme="light"]`
  or `prefers-color-scheme: light`. Accent and status tones do not change.

### Status (tertiary, workshop and piece page only)
- **Ok / Warn / Bad** (`ok`, `warn`, `bad`): card edge bars, badge tones, note-for-me tint
  (warn at 6%), matrix dots, flash backgrounds (ok 10% / bad 12% mixed into slate). The desk
  card itself carries none of them; the state is a sentence.

### Covers
- **Cover hues** (`cover-*`): chosen per piece by its track in `reader.py` (`COVER.track`),
  overridable by a `cover.json` in the pipeline. Each cover is a 3:4 SVG poster: flat hue,
  a white-to-black diagonal gradient at 35%, a white glyph, the number, up to two title lines,
  a 28% black series band. Covers are the only chroma on the desk besides the accent.

### Named Rules
**The Covers Carry the Colour Rule.** On the desk, no element except the cover and the one
accent button is coloured. Status tones stay in the workshop and in the piece page's notes.

**The One Button Rule.** A piece shows exactly one filled accent button: on its card and at
its current step. Everything else it can do is quiet text (`.quiet`) or a ghost button.

## Typography

**Display Font:** Inter (variable, self-hosted) with ui-sans-serif, system-ui fallback
**Body Font:** Inter, same file
**Label/Mono Font:** ui-monospace, SF Mono, Menlo for file names, record keys and the mono
label on the cover

**Character:** One sans, tightened as it grows. Headings sit at 650–800 with negative tracking
(-0.012em at 17px to -0.03em at 20px brand mark); body is 15px/1.5; reading text is 16px/1.65
in a 72ch column.

### Hierarchy
- **Display** (750, 30px, 1.15, -0.025em, balanced wrap): the desk lead sentence and the
  piece title. 24px under 640px. The workshop greeting is the older cousin (800, 28px).
- **Headline** (800, 20px, -0.03em): the brand name in the top bar. Module page titles are
  650 at 22px.
- **Title** (650, 17px, 1.25, -0.012em): a piece's title on a shelf; 18px on the "waits for
  you" shelf. Workshop card titles are 650 at 15px.
- **Body** (400, 15px, 1.5): default. State sentences 14px in `ink-quiet`; kind lines 12.5px
  in `ink-faint`; hints 13px.
- **Prose** (400, 16px, 1.65, max 72ch): the draft read in the page. Pre-formatted text is
  reset to the sans.
- **Shelf heading** (650, 13px, sentence case, no tracking, `ink-quiet`): the desk's section
  heading, with a tabular count in `ink-faint`. The "waits for you" shelf is 15px in `ink`.
- **Label** (700, 12px, uppercase, 0.08em, `ink-faint`): the workshop's block headings and the
  piece page's subsections (draft, notes, files, helpers). Tables and kanban columns use 600 at
  11px with 0.05–0.06em.
- **Path label** (600, 13px, `ink-faint`): step names on the big path; current step 700 at
  15px in `ink`; done steps in `ink-quiet`.
- **Big number** (700, 40px, -0.03em, 1): the workshop's headline figure. 34px under 640px.

### Named Rules
**The One Sans Rule.** Inter for everything that is read. Mono only for things a machine
named: file names, keys, the label code on a cover.

**The Sentence Not Badge Rule.** On the desk a piece's state is a sentence in `ink-quiet`,
never a pill. Badges remain on the piece page for note status and helper runs.

## Layout

A fixed 64px rail on the left (`body.has-rail` pads for it), a sticky top bar (14px 24px,
1px line below) and a centred main column: 1400px for the workshop, 1180px for the desk, 24px
page padding (16px under 640px). The base gap is 16px.

The workshop grid is `auto-fill, minmax(320px, 1fr)` with 16px gaps; the kanban is a
horizontal scroll of 240px columns; the calendar is seven `minmax(120px, 1fr)` columns.

The desk is vertical: head (lead sentence, 20px below), the intake fold (30px below), then
shelves 30px apart. A shelf row is `auto-fill, minmax(300px, 1fr)` with 26px × 32px gaps; the
"waits for you" shelf widens to 360px minimums and 30px × 36px gaps. A piece card is a two-column
grid, cover left (92px; 108px on the first shelf; 76px on phones), text and foot right, 8px × 18px
gaps. The piece page is a `1.4fr / minmax(300px, 1fr)` split (draft left, notes right) with a
28px gutter; the path box spans the full width above.

Breakpoints: 900px collapses the piece grid, the head and the big path (to three columns with
18px row gaps, connectors hidden); 640px stacks shelves to one column, hides the tagline and
control labels, shrinks covers, lead and prose.

## Elevation & Depth

Tonal layering, not shadow. Depth is ground → slate → slate-raised, with 1px `line` borders
doing the separation. The one token shadow (`--shadow`: a 1px inset white at 3% plus
`0 8px 24px rgba(0,0,0,.35)`) sits under workshop cards and the approval visual; it lightens to a
2px 6% shadow in light mode. Hover lifts are border-colour changes (to `ink-faint` or accent),
not shadow changes.

Covers are the exception and the point: they are objects on the desk and cast real soft shadow.

### Shadow Vocabulary
- **Card** (`box-shadow: var(--shadow)`): workshop cards, the approval image.
- **Cover on shelf** (`0 6px 18px rgba(0,0,0,.45), 0 1px 0 rgba(255,255,255,.06) inset`):
  rises to `0 12px 26px rgba(0,0,0,.5)` with a 3px lift on card hover (200ms, `.2,.7,.2,1`).
- **Cover on piece head** (`0 10px 28px rgba(0,0,0,.5)` + same inset): 120 × 160px.
- **Cover in workshop** (`0 1px 4px rgba(0,0,0,.4)` at 56px; `0 2px 10px rgba(0,0,0,.45)` at
  120px): older, smaller versions on kanban cards and the document head.
- **Current dot ring** (`0 0 0 4px` accent at 25%): the lit step on the path.
- **Login card** (`0 20px 60px rgba(0,0,0,.35)`): one-off.

### Named Rules
**The Flat Slate, Lifted Cover Rule.** Surfaces are flat and bordered. Only covers (and the
login card) cast shadow, and a cover's shadow is the same in light mode: it is an object, not
a surface.

## Shapes

Three radii: 12px for cards, boxes, prose, notes, the journey and rail items; 8px for inputs,
kanban cards, calendar days, the artifacts fieldset; a full pill for every button, badge, select
and the date input. Covers use their own smaller radii because they are posters, not panels:
7px on a shelf, 9px on the piece head, 6px/10px in the workshop, and the SVG itself rounds at
size/12. Dots are circles: 10px hollow with a 2px `ink-faint` stroke, filled when done, 14px
accent when current (14/18px on the big path). Connectors are 14px × 2px lines of `line`,
`ink-faint` once passed. Borders are 1px solid `line`; dashed only for the artifacts fieldset,
open calendar slots and assumption badges. Workshop cards carry a 3px rounded state bar on
the left edge; the desk card carries none.

## Components

### Buttons
Confident but small; the pill shape and the single accent do the work.
- **Shape:** full pill (999px)
- **Primary:** accent fill, white text, 600, 9px 18px (`.button`); 10px 20px at 15px text at
  the current step of the big path; 6px 14px at 13px as `.small`. Workshop form buttons are
  8px 16px with no border (`.action button`).
- **Hover / Focus:** `filter: brightness(1.1)`, no underline; focus-visible is a 2px
  `accent-soft` outline offset 2px.
- **Ghost:** transparent, `ink` text, 1px `line` border; hover darkens the border to
  `ink-faint`. Used for "Answer · n", "Done", helper runs.
- **Quiet:** `.quiet` is plain `ink-quiet` 13px text with no box; hover turns `ink` and
  underlines. The workshop link, "show all", "open →", the record toggle.

### Six-dot Path (signature)
`.path`: an ordered list of six steps, each a circle and a 14px connector. Hollow = ahead,
filled `ink-faint` = done, accent with a 25% ring = current. On a card it is dots only (titles
on hover); on the piece page `.path.big` becomes a six-column grid with labels under the dots
and the current step's `.jact` holding the one button, a ghost "Answer" if notes wait, or a
hint. Under 900px it wraps to three columns and drops connectors.

### Piece Card (`.pc`)
No box. Cover (3:4 SVG, 92px) left; title 17px, kind line 12.5px faint, state sentence 14px
quiet; below, the small path and the action. A running helper adds a pulsing 8px `accent-soft`
dot after the state. "Out" shelf cards sit at 72% opacity. Card without a cover: the foot spans
both columns.

### Shelf
A sentence-case 13px heading with a tabular count, then the row grid. The "out" shelf is a
`<details>` whose summary is the heading plus a quiet "show all".

### Cards / Containers (workshop, older)
- **Corner Style:** 12px
- **Background:** slate, 1px `line` border, `--shadow`
- **State bar:** 3px left edge in ok / warn / bad / faint
- **Internal Padding:** 18px 20px 16px; kanban cards 10px 12px on `ground`
- **Hover:** border to `ink-faint` (cards) or accent (kanban cards, tiles)

### Journey, Prose, Notes (desk boxes)
Slate, 1px `line`, 12px radius. Journey 22px 24px 20px; prose 28px 32px (18px on phones); a
note 12px 14px with 10px between notes. A note for me tints warn at 6% with a warn-mixed
border; a resolved note drops to 70% opacity.

### Inputs / Fields
- **Style:** `slate-raised` fill, 1px `line`, 8px radius, 7px 10px, 14px text; labels 12px
  `ink-quiet` stacked above. The date input is a pill (7px 12px, 13px) and declares
  `color-scheme: dark light`.
- **Focus:** only the login input defines one (2px accent at 55% outline, accent border);
  other fields rely on the browser default.
- **Folds:** `<details>` with hidden markers; the desk's "new piece" has a 28px accent disc
  with a white "+"; the notes' "ask" and "write" folds use a 20px bordered circle that flips
  "+" to "–".

### Navigation
- **Rail:** 64px fixed, slate, 1px right border; 42px square items at 12px radius in
  `ink-faint`; hover/active fill `slate-raised` and take the module's own colour (`--m`);
  active adds a 1px inset `line` ring. Home sits top with 8px extra below, setup is pushed to
  the bottom.
- **Top bar:** brand name 20px/800 with a faint 13px tagline; controls at 13px with pill
  selects; the avatar is a 26px circle with an accent-to-ok gradient.
- **Crumbs:** 13px, accent back link, quiet workshop link.

### Badges
Pill, 11px/600, `slate-raised`, `line` border, `ink-quiet`; tone variants recolour the text
(ok/warn/bad) and, for running/draft, mix the tone into background (12%) and border (30%).

### File Tiles
`auto-fill, minmax(150px, 1fr)` (110px on phones), 10px radius, slate, 8px padding, a 4:3
thumb at 6px radius; type icons are inline stroked SVGs in `ink-quiet` with accent rule lines.

## Do's and Don'ts

### Do:
- **Do** put the one action in a filled accent pill and every other action in quiet text or a
  ghost pill.
- **Do** let covers be the colour: generated SVG posters with shadow, placed on the bare ground.
- **Do** say state as a sentence in `ink-quiet` on the desk; keep ok/warn/bad for the workshop
  and the notes thread.
- **Do** keep the six dots identical on card and page; only size and labels change.
- **Do** use the three radii (8 / 12 / pill) for panels and controls; covers keep their own.
- **Do** derive light mode by re-valuing the six neutral tokens only.
- **Do** keep every file of a piece reachable from its page (tiles, matrix, record).

### Don't:
- **Don't** name a stage, label or file on the desk; the reader translates through
  `vocabulary.json`.
- **Don't** add a second filled button to a piece.
- **Don't** box a piece card on the desk; the workshop card is the older pattern.
- **Don't** add a second typeface or load anything from outside the origin.
- **Don't** put shadows on panels; shadow belongs to covers.
- **Don't** colour the desk card by state; the dots and the sentence carry it.
