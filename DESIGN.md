# Design system

How everything looks, and why. Written so that someone who has never seen these screens, a developer or an AI,
can build a new screen that looks like it belongs. The code is the truth: `apps/casefile/web/src/tokens.css` and
`apps/cockpit/cockpit/static/tokens.css` (identical files) hold every value named here.

Inspiration: Apple's own apps (Mail, Reminders, System Settings) for calm and hierarchy, ElevenLabs for how a web
product uses colour: few colours, big doses, always on purpose.

---

## 1. Principles

1. **Calm first.** People read and decide here all day. Nothing competes for attention unless it needs the person.
2. **Type and space make the hierarchy, not lines and boxes.** A heading is bigger and bolder; a group is separated by
   space. Borders, dividers and nested boxes are the last resort.
3. **Content is ink, metadata is grey.** If you read it to understand the case, it is `--ink`. Only numbers, dates,
   labels, versions and counts are `--muted`. A page that whispers everywhere has no voice.
4. **Colour always means something.** Every colour on a screen answers "why is this coloured?" with one word: you,
   AI, urgent, decided, or which application. If there is no word, it is neutral.
5. **One big colour moment per screen.** In a case it is the AI's card. Everything else gets colour in small doses.
6. **The look changes, the function stays.** Every control from the function list in `sandbox/SANDBOX.md` stays
   reachable. Things may move; nothing disappears.

---

## 2. Tokens

No raw colour, font size, font family or radius outside the tokens files. `python3 tools/design_guard.py` enforces
it and only lets the count of old raw values go down (`--list` shows what is left, `--update` lowers the baseline).

### 2.1 Surfaces and ink

| Token | Light | Use |
|---|---|---|
| `--ground` | `#F5F5F7` | grey surfaces: sidebars and menus, the case area behind cards, grouped lists |
| `--ground-2` | `#FBFBFD` | hover on white |
| `--surface` | `#FFFFFF` | cards, the list column, the cockpit page |
| `--ink` | `#1D1D1F` | all content |
| `--ink-2` | `#424245` | supporting sentences (a section's lead line, secondary buttons' text) |
| `--muted` | `#6E6E73` | metadata only |
| `--hairline`, `--hairline-2` | `#E5E5EA`, `#D2D2D7` | the few lines we keep: pane edges, rows in a grouped list |
| `--fill-quiet`, `--fill-quiet-hover` | 4.5 % / 7.5 % black | selection and hover: a fill, not a line |

Dark mode redefines the same names (true black ground, `#1C1C1E` surfaces). Never write a dark colour by hand.

### 2.2 The colour model

**Three hues on any screen, besides the neutrals.** Every colour answers "why?" with one word; if it has no word,
it is neutral. More meaning does not earn more colour: six reasons on one screen still read as random.

| Token | Means | Where it appears | Never |
|---|---|---|---|
| `--c-you` (blue) | **your move**: this waits for you | the dot on a list row and in the case head, the counter in the menu, the current station, the main button | progress, selection, links, decoration |
| `--c-ai` / `--ai-glow` (violet, violet to orange) | **the AI** | the AI's card (the one colour moment: glow edge and soft wash), its proposal, the ✦ and name on its messages, the ✦ wherever you ask it | as a fill behind text, as a border on messages |
| `--c-seal` (red-brown) | **decided**: it holds now | a main action that seals (with the seal icon), seal events in the conversation | warnings or errors |

Small exceptions that sit inside the AI card and so read as part of it: the urgency tag (`--c-urgent`, orange, the
warm end of the AI's glow).

Neutral on purpose: the station line (ink), the list heading, selection (a grey fill), labels (a grey tag).

### 2.3 Identity colours

Each application has one identity colour, `--dot-1` to `--dot-6` (indigo, orange, green, purple, red, teal; Apple's
system colours). Indigo, not blue, is first, because blue is "your move". The application names its colour in its
theme (`"identity": "dot-1"`) and the surface sets `--app` from it. It is used for the application's **icon only**:
the cockpit card, the cockpit sidebar dot and the icon in the application's bar. Never inside the application's
content or controls.

Case labels (`covers` in each theme) are a second, finer identity: the insurance line of a case (motor, household).
Covers are no longer drawn as tiles: every application uses the same row and head layout. Where an application has
more than one kind of case, the kind is a small neutral tag beside the case number; the eyebrow of the case head names
it in words. Where all cases share one label, nothing is shown, because it would say nothing. Label colours
come from a palette that never collides with the vocabulary: teal, brown, green, indigo, pink; never blue (you),
violet (AI) or orange (urgent).

### 2.4 Type

The system font (SF Pro on Apple devices, Inter or Segoe elsewhere). Pick a **role**, never a pixel size.

| Role | Size | Use |
|---|---|---|
| `--text-hero` | 52 | at most once per page: intros, covers |
| `--text-display` | 40 | big numbers |
| `--text-large-title` | 34 | the page title (the cockpit greeting) |
| `--text-title-1` | 28 | the case title |
| `--text-title-2` | 22 | section headings, the list heading |
| `--text-headline` | 17 | card and block titles (semibold), section headings with an icon |
| `--text-reading` | 17 | long text: documents, mails, notes |
| `--text-body` | 15 | default UI text |
| `--text-callout` | 14 | buttons, grouped-list rows, secondary UI |
| `--text-subheadline` | 13 | status lines, meta lines |
| `--text-footnote` | 12 | labels, timestamps, case numbers in lists |
| `--text-caption` | 11 | the smallest readable text |
| `--text-micro` | 10 | only inside badges and covers |

**Weights:** regular 400 for text, semibold 600 for titles and emphasis, bold 700 only for titles of 22 px and up.
No medium (500); it makes text muddy.

**Tracking:** the browser does not apply Apple's optical tracking, so we do. `--tracking-text` on all UI text,
`--tracking-reading` (with line height 1.47) on long text, `--tracking-snug` on headlines, `--tracking-tight` on
titles of 22 px and up.

**Hierarchy by weight and colour, not by neighbouring sizes.** Two lines next to each other differ in weight or
colour, not by 2 px.

**Mono** (`--mono`) is for codes inside text only (a rule id like `R-05`). Never for headings, never for case numbers.

### 2.5 Shape, depth, motion

| Token | Value | Use |
|---|---|---|
| `--r-s` | 8 | buttons, segmented items, chips |
| `--r-m` | 12 | main buttons, list rows, grouped lists, tiles |
| `--r-l` | 16 | document tiles, message bubbles |
| `--r-card` | 18 | cards (workspace cards, the AI card) |
| `--r-pill` | 999 | tags and counters only |
| `--shadow-card` | soft, 2 layers | a card on a grey ground |
| `--shadow-card-hover` | deeper | hover on a clickable card (with a 2 px lift) |
| `--shadow-float` | small | things that float: bar buttons, popovers |
| `--ease`, `--slide` | | all transitions |

Every animation stops under `prefers-reduced-motion`.

Spacing is not tokenized yet (see section 8).

---

## 3. Layout

### The cockpit
A grey sidebar against the left edge, a white page, a header bar across the top with the page name on the left and
global actions on the right. The dashboard: greeting and status line top left (compact; this is a working tool),
the timestamp quiet on the right, then sections with a bold heading and a one-line lead, then cards three to a row.

### An application (workspace)
Three panes, three tones, so each pane differs from its neighbour:

| Pane | Tone | Holds |
|---|---|---|
| Menu | `--ground` (grey) | views, places, tools, settings |
| List | `--surface` (white) | the cases, as rows |
| Case | `--ground` (grey) | the open case; its cards are white |

The bar over all three is a breadcrumb: `Cockpit › [app icon] Name  STAGE`, with support actions on the right.

### The case, top to bottom
1. **Eyebrow:** label and date, then the case number, both small and grey.
2. **Title:** the case's subject, `--text-title-1`, bold. The one dominant title of the screen.
3. **Next step:** what happens next, once, semibold (never repeat the title after it).
4. **Status:** a dot and a grey line; the dot is blue when it is your move. "Details" opens the meta sheet.
5. **Stations.**
6. **On the desk** (documents) beside **Conversation**.
7. **The main action**, bottom right.

---

## 4. Components

### List row (`.card`)
Case number (footnote, grey) with the date on the right; subject (body, semibold); status line (footnote, grey).
When it is your move, a blue dot: in the left margin of a row without a cover, in front of the status line
when there is one. Hover: `--fill-quiet`. The open case: `--fill-quiet-hover`, the same neutral selection as the
menu (as in Finder). A cover only where labels differ. *Don't* box rows; separate them with space.

### AI card (`.triage`)
The one colour moment of a case: a 1.5 px `--ai-glow` edge, a soft violet-to-orange wash across its top, a ✦ top
right. Inside: kind (headline, semibold), urgency tag, summary (ink), facts as a grouped list, quotes, and the
proposal in a soft violet box with the action in `--c-ai`. *Use* for anything the AI read or proposed. *Don't* use
the glow for anything else, and never two AI cards' worth of colour on one screen.

### Facts: grouped list (`.triage-fields`)
The Settings pattern for key and value: one `--ground` panel, a row per fact, label left in grey, value right in ink,
hairlines between rows, callout size. *Use* for any key/value data. *Don't* float labels above values in a grid.

### Document tile (`.file`)
White, `--r-l`, `--shadow-card`; a document symbol and the name, then one line of metadata (ellipsis, never
wrapping). Tiles are uniform in a grid of at least 200 px.

### Section heading with symbol (`.kicker`)
Headline size, bold, preceded by a neutral line icon in a 26 px outlined tile. Symbols are neutral; colour belongs
to meaning.

### Buttons
| Kind | Look | Use |
|---|---|---|
| Main | `--r-m`, 46 px, blue fill | the next step that is your move |
| Main, sealing | `--c-seal` fill with the seal icon | a decision that will be sealed |
| Secondary | white, 1 px hairline, `--r-s`, 32 px (44 on touch) | alternative actions under the conversation |
| Segmented | grey track, white chosen item with a card shadow | views (Cases, Board, List), documents in the reader |
| Icon | borderless, fill on hover | reader arrows, open in new window |
| Bar | white, hairline, `--r-s` | Help, Demos, Reset data |

*Never* an underlined text link as an action. States for every button: default, hover, focus (the global focus
ring), disabled (45 % opacity), loading (the label shows "…").

### Tags
Pill, tinted background, text in the deeper tone of the same colour. Urgency (`--c-urgent`), "can wait" and other
urgencies the same family. *Don't* outline tags.

### Conversation
Messages sit on the conversation's grey panel as white bubbles with sender and time on top. A **seal event** is a
soft seal-tinted row with the seal icon and plain text (no rotation, no uppercase, no mono). The **ask field** starts
with a violet ✦ and gets a violet ring while typing; the send button turns ink when there is something to send.

### AI working state
When the AI holds a case: the next step shimmers in `--c-ai`, the status carries a pulsing ✦ instead of the dot, the
list row's progress bar uses `--ai-glow`. Still under reduced motion.

### Workspace card (cockpit)
White card, `--r-card`, hairline ring plus `--shadow-card`, lifts on hover. A 44 px app icon in the identity colour
with a white symbol, the name (headline, semibold, one line), one meta line. When "In use" is empty, the add tile
spans the row.

---

## 5. Do and don't

| Do | Don't |
|---|---|
| Pick a type role | Write a pixel size |
| Content in `--ink` | Grey paragraphs |
| One colour moment per screen | Sprinkle colours for liveliness |
| Separate with space and fills | Nest boxes in boxes |
| Buttons for actions | Underlined text as an action |
| Say a thing once | Repeat the title in the next line |
| Neutral symbols | Coloured icons without a meaning |
| Hide what says nothing (covers in a one-label workspace) | Show decoration "so it is not empty" |

---

## 6. Hand-back: this step

Branch `design/tokens`. What it covers, beyond the tokens alone:
- Tokens: Apple-style neutrals, the type scale as roles, tracking, shadows, fills, radius, identity colours, the
  colour vocabulary. Raw values: 739 → 216.
- The cockpit shell and dashboard; the workspace's three panes, list, case head, AI card, grouped facts, buttons,
  conversation, reader toolbar.
- Markup changes, kept small: `List.tsx` (covers only where labels differ, the date on the row), `Case.tsx` (no cover
  in one-label workspaces, the next step without the repeated title, the AI-working class), `TopBar.tsx` (app icon,
  identity colour), cockpit `index.html`, `base.html`, `glyphs.html` (cards with app icons, page name in the bar).

## 7. Requests for development

1. **Application identity in the theme.** Each theme now has `"identity": "dot-N"`. Please accept the key (it is
   outside `covers`), and let the cockpit read it instead of assigning colours by position.
2. **An icon per application** in its theme. The cockpit currently maps icons by application id.
3. **Mark actions the AI performs** (for example `"actor": "ai"` on a move), so they can wear the AI's colour
   without the core naming an application's action.
4. **No file names or extensions in the interface** (`fragebogen.json`, `anfrage.md`): show the document's word.
5. **One sentence per step.** The next step, the status and the button often say the same sentence.
6. **The workspace server reads `index.html` once at start**, so after any rebuild the sandbox serves a page whose
   script no longer exists (a blank page) until restarted.
7. **Label colours live in the value lists**, which take precedence over `covers`. Several are blue, which reads
   as "your move". Please move them to teal, brown, green, indigo or pink.
8. **Build output (`dist/`) is tracked in git**, so every design branch carries rebuilt bundles. Intended?

## 8. Not done yet

- Spacing tokens (a 4/8 scale) and moving the remaining 216 raw values.
- The assessor's on-site tablet view, the rules, signals, canon and value-list screens: tokens only so far.
- Dark mode: derived and checked lightly, not designed screen by screen.
