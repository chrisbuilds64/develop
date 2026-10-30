# The design sandbox

The whole system on your Mac: the cockpit and five sample applications with their demo flows. It runs offline and uses fictional
data only. Break anything you like; `reset` brings it back.

You work on **the look**. We keep working on the features in parallel. You hand your design back to us, and we bring it into
the running version.

## Install (once, needs the network)

You need macOS with [Homebrew](https://brew.sh), git, Python 3.11 or newer and Node.js 20 or newer:

```bash
brew install python@3.12 node git
git clone https://github.com/chrisbuilds64/develop.git
cd develop
python3.12 sandbox/sandbox.py setup        # Python environment, the web surface, a headless browser (~5 min)
```

## Run (offline from here on)

```bash
python3 sandbox/sandbox.py up              # http://127.0.0.1:8200 — sign in as designer / sandbox-local
python3 sandbox/sandbox.py reset           # every workspace back to its sample world
python3 sandbox/sandbox.py check           # play every demo flow headless; must stay green
```

`up` also watches the surface. When you save a file under `apps/casefile/web/src`, it rebuilds in a second or two. Reload the
browser to see the change. Cockpit templates and CSS are read on each request.

What you find inside:

| Workspace | What it is |
|---|---|
| Posteingang · Muster | an inbox: mails are read by the AI, a person confirms, the mail becomes a case elsewhere |
| Angebotsakte · Muster | quotes: questionnaire, rate, document |
| Schadenakte · Muster | claims: report, inspection, check, settlement |
| Gutachtenakte · Muster | the assessor's side, including the on-site tablet view |
| PressRoom · Muster | the content pipeline, with invented pieces |

In a sample workspace, **Abläufe** (top bar) plays a flow step by step. These are the same flows we present to customers.
The AI answers are recorded, so nothing calls out to a model.

## What to change, and what not

**Yours: everything that is the look.**

| Where | What |
|---|---|
| `apps/casefile/web/src/tokens.css` | colours, type, spacing, radii, motion: the design tokens of the applications |
| `apps/casefile/web/src/app.css` | how every screen and component looks |
| `apps/casefile/web/src/components/*.tsx`, `screens/*.tsx` | markup and class names, where the look needs it |
| `apps/cockpit/cockpit/static/tokens.css`, `cockpit.css` | the cockpit (shell, dashboard, sign-in) |
| `apps/cockpit/cockpit/templates/*.html` | the cockpit's markup |
| `apps/casefile/config/*/theme.json` → `covers` | the colour per case label |

**Not yours. Please leave these alone:**

- the API and the engine: `apps/casefile/casefile/`, `apps/cockpit/cockpit/*.py`
- the stages, rules, vocabulary and value lists in `apps/casefile/config/*/` (except `covers`)
- the demo flows and worlds in `sandbox/worlds/`

When a design needs a change on that side, write it down in the hand-back and we build it.

## What must keep working

The rule from the last redesign: **the look changes, the function stays, 100 %.** Every one of these stays reachable in every
application that has it today. It may move, but it must not disappear:

- **Views:** cases · Kanban · list; groups with counters ("Du bist dran" is the only one in colour)
- **The case:** head (cover, label, number, title, status line) · meta sheet (`meta.json` as a table) · station line · documents on
  the desk (newest version first, images as thumbnails) · reader with versions and "own window" · missing slots that take a drop
  or a file · thread with author, date, status, open questions · note, question to the AI, answer, done · main action with its
  inputs (amount, date, link, note), rejection with reason · "blocked until …" and four-eyes hints
- **Special screens:** mail triage (AI reading, rule row, confirm / file / read again) · interview · outcome (accept / change /
  discard line by line, seal) · on-site tablet (photos per view, note, hints) · rules · signals · house canon · value lists
- **Menu and bar:** new case · AI ⌘K · left/right hand · language · light/dark/system (shared with the cockpit) · sound ·
  person picker in samples · back to the cockpit · help · videos · flows (Shift+Alt+D) · reset data · agent panel
- **The flows:** `sandbox.py check` plays all five. Green before you hand back, every time.

## What we need from you: a design system, not only a new look

Your result becomes the rule every future application follows, including the ones an AI builds. An application here is only a
configuration on the core: it gets its whole look from the core, and may set nothing but the colour per case label (`covers`)
and its words. So what you deliver has to work as a **system**:

- **Tokens** (`tokens.css`, for the applications and the cockpit alike) are the only source of colour, type, spacing, radius,
  shadow and motion. No raw values anywhere else; we will add a check that fails on them.
- **Components** with a name, their variants and states (default, hover, focus, disabled, loading, empty, error). A screen is
  built from components, not styled one by one.
- **`DESIGN.md`** as the design system's documentation: principles and the reasons behind them, the tokens and what each is for,
  every component with when to use it and when not, layout and patterns (lists, the case, gates, empty states), do and don't.
  Write it so that someone who has never seen your screens, a developer or an AI, builds a new screen that looks like yours.

## Hand-back

Hand back in steps, not all at once: **tokens first, then components, then screens.** We take each step into the running
version before the next one starts. Work on a branch `design/<step>`. When a step is ready:

1. `python3 sandbox/sandbox.py check` is green.
2. `DESIGN.md` in the branch root is up to date for this step.
3. Before/after screenshots of the screens you touched.
4. Push the branch and tell us. We review it, run the check again and bring it to production through our stages.

If you prefer to work in mock-ups instead of code, that works too: put them with a `DESIGN.md` in the branch, and we implement
them.

Questions and decisions go in `sandbox/communication.md` (append only, newest at the bottom, date and name per entry).

## Keep it clean

This repository is public. Commit nothing that names a real person, customer or company, and no data from real work. The
sample worlds are fictional, and new material must be fictional too.
