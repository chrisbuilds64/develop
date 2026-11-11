# REQ-001 — casefile core: what it does today

**Status:** reconstructed from the code on 2026-11-08 and **accepted by the product owner the same
day**, line by line. Nobody specified these before they were built; this list is what the code did,
and now it is what the code must do. Each line is a requirement; its test is the evidence. Where a
line has no test, the test is owed (decision E3). What the product owner asked for beyond today's
code is listed separately under *Wanted, not built*.

**Scope:** `apps/casefile/casefile/` (core, API) and `apps/casefile/web/` (surface). Not in scope:
cockpit, the domain configurations under `config/`, operations.

**Evidence** means a test in `apps/casefile/tests/` that would fail if the capability broke.
Suite on 2026-11-08: 164 tests, all green.

## The case

| # | Capability | Code | Evidence |
|---|---|---|---|
| C-01 | A case is a folder; the stage folder it sits in is its status. | `store/fs.py`, `domain/cases.py` | yes — `test_entries_assets_store` |
| C-02 | Every write is atomic, a per-case lock serialises steps, nothing is overwritten or lost. | `store/fs.py` | yes — `test_entries_assets_store` (lock, refuse overwrite) |
| C-03 | A step is one move, whole or not at all: lock, precondition, journal, thread entry, move. Same step twice is a no-op. | `domain/step.py` | yes — `test_step` (11) |
| C-04 | A step left half-way by a crash is completed on the next start; a folder moved by hand is detected and recorded. | `domain/step.py` `recover()` | yes — `test_step` |
| C-05 | Undo until the case goes on, afterwards only a correction (ADR-025). | `domain/step.py` | yes — `test_demo` |
| C-06 | Deliverables are versioned upward (`.v2`, `.v3`), never replaced. | `domain/assets.py` | yes — `test_entries_assets_store` |
| C-07 | The thread (`review.md`) is data: one format, read and written in one place; old entries still parse. | `domain/entries.py` | yes — `test_entries_assets_store` |
| C-08 | A new case gets its number from the domain's rule (per year, per series, placeholder). | `domain/numbering.py` | yes — `test_numbering` |
| C-09 | A free file attached at creation is stored beside the deliverables, never as one, never overwriting another file: a taken name, or one a deliverable of the label would read as its own (`task.md`, `task.v2.md`), gets `-2`, `-3`; only images, PDF, text and video, never HTML. *(Added with SW-2026-007, 2026-11-11.)* | `domain/assets.py` `put_free` | yes — `test_new_case` |

## Whose move

| # | Capability | Code | Evidence |
|---|---|---|---|
| T-01 | One function decides whose move it is: running run → AI; failed run → operator; open entry → addressee; else by stage. | `domain/turn.py` | yes — `test_turn` |
| T-02 | Four eyes: the approver is not the author of the newest version — by person, not by name. | `domain/turn.py`, `domain/step.py` | yes — `test_turn`, `test_step`, `test_rulebook` |
| T-03 | A person sees their own moves across workspaces; roles resolve to persons. | `domain/turn.py`, `api/app.py` `/api/me/turns` | yes — `test_turn`, `test_api` |
| T-04 | Read/unread per person, like mail. | `domain/seen.py` | yes — `test_demo` |
| T-05 | A case somebody else holds can be reminded or taken back. | `domain/step.py` | yes — `test_demo` |
| T-06 | The stack (my desk) is ordered by rule; a date puts a case first; order is configurable. | `domain/turn.py`, `domain/cases.py` | yes — `test_stack` |
| T-07 | Rhythm: what a person did today and this week. | `api/app.py` `/api/me/rhythm` | **no** |

## Configuration instead of code (ADR-015)

| # | Capability | Code | Evidence |
|---|---|---|---|
| K-01 | Stages, deliverables, words, people and theme come from `config/<domain>/`; the pipeline root overrides without erasing. | `config.py` | partly — `test_config` (1 test) |
| K-02 | Value lists: loaded from domain and tree, changed only by an operator, every change logged, retired entries stay readable. | `domain/lists.py` | yes — `test_lists` |
| K-03 | An operator adds a new kind of case, starting from an existing one. | `domain/schemas.py` | yes — `test_schemas`, `test_demo_sessions` |
| K-04 | The core names no domain and imports no adapter or web framework. | guard in `tools/` | yes — `test_guards` |

## AI helpers and people

| # | Capability | Code | Evidence |
|---|---|---|---|
| A-01 | A helper is ordered as one file in `_runs/`; an application orders only its own skills. | `domain/runs.py` | yes — `test_step`, `test_handoff` |
| A-02 | Every thread entry says whether a person or the AI wrote it. | `domain/entries.py` | yes — `test_demo` |
| A-03 | The live runner that executes orders is its own application beside casefile and cockpit (decision E1, 2026-11-08). Today it still sits in cockpit (`plugins/pipeline/runner.py`); casefile itself only has the demo replay. | — | n/a — move pending |
| A-04 | What the AI proposes for the rulebook waits; a person accepts or rejects with a reason. | `domain/rulebook.py` | yes — `test_rulebook` |
| A-05 | A helper writes in the case only the files its action delivers (`produces`, file names only); a helper without a delivery (the free question) only reads and answers through the thread. The same in every application. An order that names no delivery (an action without `produces`, a follow-up, a mail intake) is not guarded yet. | `domain/runs.py`, `plugins/pipeline/write_guard.py` | yes — `test_shipyard`, `test_runner_write_guard` |

## Deterministic work (by the core, never by the AI)

| # | Capability | Code | Evidence |
|---|---|---|---|
| D-01 | Rating: a quote computed from questionnaire and rate table, line by line; a missing answer is named, never guessed. | `domain/rating.py` | yes — `test_rating` |
| D-02 | Compose: a document assembled from approved text modules by rules; an unapproved module or missing value refuses. | `domain/compose.py` | yes — `test_compose` |
| D-03 | Rulebook: modules as versions; a change is a draft until a second person approves; a running case keeps the rulebook it started with. | `domain/rulebook.py` | yes — `test_rulebook` (7) |
| D-04 | Sorting: rules decide first, the AI reads only what no rule decides, nothing is deleted. | `domain/sorting.py` | yes — `test_sorting` |

## Between applications and from outside

| # | Capability | Code | Evidence |
|---|---|---|---|
| H-01 | Hand-off: a case creates or feeds a case in another application, described by a spec. | `domain/handoff.py` | yes — `test_handoff` |
| H-02 | A mail becomes exactly one case (idempotent by Message-ID), attachments beside it. | `connectors/mailbox.py` | yes — `test_mailbox` |
| H-03 | Fetching the mailbox over IMAP/TLS, credentials from the environment. | `connectors/mailbox.py` | **no** — only ingest is tested |
| H-04 | Interview: questions from a pack, several respondents, follow-ups, a draft decided line by line, compiled canon. | `domain/interview.py` | yes — `test_interview` (10) |
| H-05 | Outcome decision over the API (`/outcome`, `/outcome/decide`). | `api/app.py` | partly — domain tested (`test_deviation`), API not |
| H-06 | The house canon at one glance (layers, depth). | `domain/house.py` | domain yes — `test_interview`; `/api/canon` **no** |
| H-07 | On-site photo series and the helper's next round. | `api/app.py` `/vorort`, `/samples` | yes — `test_onsite` |

## Access and surface

| # | Capability | Code | Evidence |
|---|---|---|---|
| S-01 | Identity by cookie, or from outside (cockpit) replacing the cookie; roles missing at the root are lent by the domain. | `api/app.py` | yes — `test_api` |
| S-02 | Writes go to the write root, reads stay on the root. | `api/app.py` | yes — `test_api` |
| S-03 | Text files are rendered with raw HTML shown, not run. | `api/app.py` | yes — `test_api` |
| S-04 | The committed OpenAPI contract is the one the core serves; TypeScript types derive from it. | `models.py`, `web/openapi.json` | yes — `test_guards` |
| S-05 | The surface is served under any prefix. | `api/app.py` | yes — `test_api` |
| S-06 | Content follows the reader's language, the original stays. | `api/app.py` `/translate` | yes — `test_demo`, `test_demo_sessions` |
| S-07 | Design values only go down (no raw colours outside tokens). | `tools/` guard | yes — `test_design_guard` |
| S-08 | The surface (39 files, ~9,500 lines React/TS) is checked end to end: CI job `flows` clicks every demo flow in a headless browser (`sandbox.py check`). It has no component tests of its own. | `web/src/`, `sandbox/walks/` | end-to-end yes — CI `flows`; component tests **no** |
| S-09 | A note is written in a large editor: ⌘J or a click opens it, ⌘Enter sends, Esc closes and keeps the draft per case. *(Added with SW-2026-001, 2026-11-09.)* | `web/src/components/NoteField.tsx` | end-to-end yes — walk `note-editor` in CI `flows` (`web/walks/note-editor-shot.mjs`) |
| S-10 | Facets: every application gets filter, sort and card values from its own configuration — each value list, each declared field (person, date, list), the data points of an instance and the stages; defaults by kind, a list or field overrides them with `view` (`filter`, `sort`, `card`). No facet names a domain. *(Added 2026-11-10.)* | `domain/facets.py`, `/api/config` `facets`, card `values` | yes — `test_facets` |
| S-11 | Board and table carry one facet bar: title search, a multiple choice per filter facet, "mine", "overdue" (the first date facet), an order by any sort facet, and how many of how many show. The choice lives in the address, so a view survives a reload and can be sent as a link. *(Added 2026-11-10.)* | `web/src/components/Facets.tsx`, `screens/Board.tsx` | end-to-end — walk `facets-shot` (`web/walks/facets-shot.mjs`), not yet in CI `flows` |
| S-12 | A card shows its card facets as chips: a list value with its colour, the person, the date (marked when past and the case is still open), the data point. *(Added 2026-11-10.)* | `web/src/components/Facets.tsx` | end-to-end — walk `facets-shot` |
| S-13 | While a workspace loads, the frame shows at once and the list shows placeholder rows; they respect reduced motion and both themes. *(Added with SW-2026-003, 2026-11-10.)* | `web/src/components/Skeleton.tsx`, `App.tsx`, `screens/Queue.tsx`, `screens/Home.tsx` | end-to-end yes — walk `loading-state` in CI `flows` (`web/walks/loading-state-shot.mjs`) |
| S-14 | A text file the application marks `editable` (artifacts.json) opens in an editor from the reader; saving writes the next version beside the old ones. The core refuses every other file, and the thread and `meta.json` whatever a configuration says. A free note (S-17) is editable without being declared. *(Added with SW-2026-004, 2026-11-11; notes with SW-2026-006.)* | `domain/edit.py`, `domain/cases.py` `editable`, `POST /api/cases/{id}/edit`, `web/src/components/Editor.tsx` | yes — `test_edit`; end-to-end — walk `text-editor` in CI `flows` (`web/walks/text-editor-shot.mjs`) |
| S-15 | The editor has a Markdown toolbar (bold, italic, heading, list, checklist, link, code) and ⌘B/⌘I/⌘K — ⌘K is the link there, not the search; a preview from the reader's renderer beside the text, or behind a switch on a narrow screen; Esc with unsaved text asks before discarding, without changes it closes at once. *(Added with SW-2026-004, 2026-11-11.)* | `web/src/components/Editor.tsx`, `POST /api/cases/{id}/edit/preview` | yes — `test_edit` (preview); end-to-end — walk `text-editor` |
| S-16 | In the file that carries acceptance criteria (theme `criteria.file`, default `task.md`), the lines the gate could not read are named in the editor with their line and the gate's reason, before saving. *(Added with SW-2026-004, 2026-11-11.)* | `domain/criteria.py` `unreadable`, `web/src/components/Editor.tsx` | yes — `test_edit`; end-to-end — walk `text-editor` |
| S-17 | Every case may hold free Markdown notes under `notes/`, created, edited and versioned in the editor; they count for no gate. An application switches them off with `"notes": false` in theme.json; the default is on. *(Added with SW-2026-006, 2026-11-11.)* | `domain/notes.py`, `store` `sub_files`, `POST /api/cases/{id}/notes`, `web/src/screens/Case.tsx` `Notes` | yes — `test_notes`, `test_data_points` (note in a data point); end-to-end — walk `notes` in CI `flows` (`web/walks/notes-shot.mjs`) |
| S-18 | A new case is started from a visible button in the bar of the application the person is in (`theme.create`, for its roles, worded by the vocabulary's `texts.new_case`); it opens the editor with title, the value lists that ask on creation, a Markdown description with the S-15 toolbar, and files by drop or paste. The case is made in that application, never another; the files become files of the case, the description is the first thread entry and shows them as `![](name)`. The rail opens the same editor. *(Added with SW-2026-007, 2026-11-11.)* | `POST /api/cases` (JSON or multipart), `web/src/components/NewCase.tsx`, `Md.tsx` | yes — `test_new_case`; end-to-end — walk `new-case` in CI `flows` (`web/walks/new-case-shot.mjs`) |

## Public demo (ADR-016)

| # | Capability | Code | Evidence |
|---|---|---|---|
| P-01 | Every visitor gets their own sandbox, copied from a fictional world; documents hard-linked. | `demo/sandbox.py`, `demo/worlds.py` | yes — `test_demo_sessions` |
| P-02 | Cap on sandboxes (oldest go), rate limit answers 429, no unlimited AI teams without cookies. | `api/app.py` | yes — `test_demo_sessions` |
| P-03 | Helper results are prepared and played back; no model is called. | `demo/replay.py` | yes — `test_demo` |
| P-04 | Demo reset and the list of demo flows over the API. | `/api/demo/reset`, `/api/demo/ablaeufe` | **no** |

## Tools

| # | Capability | Code | Evidence |
|---|---|---|---|
| X-01 | Stock check: read a real pipeline and report what the core would make of it, writing nothing. | `cli/inventory.py` | **no** |

## Wanted, not built

Asked for by the product owner while accepting this list (2026-11-08). Not yet in the code.

| # | Wanted | From |
|---|---|---|
| W-01 | Fetching the mailbox is developed further and tested against a local IMAP server. | H-03 |
| W-02 | The outcome decision becomes an abstract, universal mechanism, not one shaped by a single application. | H-05 |
| W-03 | The house canon view is specified more precisely. | H-06 |
| W-04 | A security package: injection checked across every input surface; the security audit as a built-in function whose runs are logged. | S-03 |
| W-05 | The documentation audit as a built-in function: finds orphans, rule violations and logical gaps. | S-03 |
| W-06 | Demo reset and demo flows get their evidence. | P-04 |
| W-07 | Saved views (a named facet choice per person) and a stage facet that hides closed stages by default. | S-11 |
| W-08 | A helper at work shows the phases its skill declares (run-policy `phases`), the one reached, the tool call going on and the ones before, the time so far and the usual duration of that skill; a failed run offers "run again" to whoever may order the skill. | `test_a_running_build_shows_its_phases_what_it_does_now_and_how_long_it_usually_takes`, `test_a_failed_run_is_run_again_by_whoever_may_order_its_skill` (test_shipyard.py), `test_a_running_helper_reports_its_steps_and_phase_as_it_goes` (cockpit) |

## Findings and decisions

Decided by the product owner on 2026-11-08. Structural decisions become ADRs when they are built.

1. **A-03** — the runner lives in cockpit's plugin folder, although it imports nothing from cockpit. **E1:** it becomes `apps/runner/`.
2. **S-08** — the surface is covered only end to end, by the flow walks in CI. **E2:** the walks are the evidence; component tests for logic after DOAG.
3. **Untested:** T-07, H-03, H-05 (API), H-06 (API), P-04, X-01. **E3:** tests are written against these lines.
4. **`api/app.py` is 1,961 lines** — every endpoint in one file. **E4:** split into routers by area, behaviour and contract unchanged.
