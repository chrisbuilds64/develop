# REQ-005 — Worklist: open items as cases

**Status:** proposed 2026-11-09, waiting for the product owner. Decision record: ADR-031.

**Scope:** the configuration `apps/casefile/config/worklist/`, the core concepts it needs (dependencies between cases,
personal workspaces, remote access), the move of `control/context/todo.json`, and `todo.py` as a client. Not in scope:
the Context Loop's session handling.

**Evidence** means a test in `apps/casefile/tests/test_worklist.py`, unless the row names another.

## The way of an item

| Stage | Meaning | Leaves when |
|---|---|---|
| 10 Backlog | recorded, not planned | someone plans it |
| 20 Next | planned, not started | someone starts it |
| 30 Doing | in work | done, or it has to wait |
| 40 Waiting | waits for a person or another case | the reason is gone |
| 90 Done | closed, with the date | — |

## Requirements

### The item

| # | Requirement | Evidence |
|---|---|---|
| WL-01 | An item is a case with title, cluster, priority, assignee, due date (optional), origin (kind + reference), created, changed and closed dates. | `test_an_item_carries_the_fields_of_todo_json` |
| WL-02 | Cluster, priority, people, statuses and origin kinds are value lists of the workspace; a value not in its list is refused. | `test_a_value_outside_its_list_is_refused` |
| WL-03 | An item keeps its id across the move: cluster prefix and number (`SYS-147`); a new item gets the next number of its cluster. | `test_ids_survive_and_continue_per_cluster` |
| WL-04 | Any file may be added to an item; none is required. | `test_any_file_may_be_added_none_is_required` |
| WL-05 | Every member of the workspace may move an item to any stage; reaching Done sets the closing date, leaving it clears it. | `test_any_member_moves_and_done_sets_the_date` |

### Dependencies (core)

| # | Requirement | Evidence |
|---|---|---|
| DP-01 | A case may wait for other cases, also in other workspaces; the reference names workspace and case. | `test_a_case_waits_for_cases_in_other_workspaces` (core) |
| DP-02 | A waiting case shows what it waits for, in the viewer's words, and whether each is closed. | same test |
| DP-03 | When the last case it waits for closes, the waiting case is marked as released; it does not move by itself. | `test_closing_the_last_dependency_releases_but_does_not_move` |
| DP-04 | A reference to a case that does not exist, or that the person may not see, is refused when it is set. | `test_a_dependency_must_exist_and_be_visible` |
| DP-05 | A circle of dependencies is refused. | `test_a_circle_is_refused` |

### Privacy and hand-off

| # | Requirement | Evidence |
|---|---|---|
| PV-01 | Every person has a personal worklist in a team folder of their own; no other person and no agent of another person is a member. | operations (`pressroom-env`), registry test |
| PV-02 | A shared worklist is a workspace with named members; its items are visible to them and only to them. | registry test |
| PV-03 | *Delegate:* an item is created in another person's worklist with origin and link; in mine it closes with a reference to the new one. | `test_delegate_creates_there_and_closes_here` |
| PV-04 | *Share:* an item moves into a shared worklist the person is a member of; its id stays. | `test_share_moves_the_item_and_keeps_its_id` |
| PV-05 | The surface shows a person their own items and those of the shared worklists they belong to, in one list, each marked with its workspace. | surface test |

### One interface

| # | Requirement | Evidence |
|---|---|---|
| IF-01 | The core's API is reachable from outside the server with a personal token. | `test_api_accepts_a_valid_token_and_refuses_others` |
| IF-02 | A token belongs to one person or one agent, names its workspaces and whether it may write, expires, and can be revoked at once. | same test |
| IF-03 | Every write through a token is journaled with the token's owner. | `test_writes_are_journaled_with_the_token_owner` |
| IF-04 | `todo.py` keeps its commands (`list`, `show`, `add`, `set`, `done`, `check`) and calls the API; the skills `/todo`, `/todo-add`, `/todo-done` work unchanged. | `control` test of `todo.py` against ENTW |

### The move

| # | Requirement | Evidence |
|---|---|---|
| MV-01 | All items of `todo.json` move once, with ids, dates, dependencies and origins; a count and a field-by-field comparison prove it. | migration report in the case |
| MV-02 | After the move `todo.json` is archived read-only and `todo.py` refuses to write it. | `control` test |
| MV-03 | Items assigned to Akhil move into his worklist, the rest into Chris's; agents' items stay with the person they belong to (ADR-020). | migration report |

### The entry to casefile

| # | Requirement | Evidence |
|---|---|---|
| EX-01 | A demo world "Worklist" shows every core concept on items: case, stage, whose move, value list, document, gate, hand-off, dependency. | demo build test |
| EX-02 | A one-page explanation (German and English) maps each concept onto the worklist and names, for each other application, what it adds: words, required documents, gates. | review by the product owner |
| EX-03 | Every stage, action and field has its word in German and English. | `test_both_languages_name_every_stage_action_and_field` |

## The parts, one case each

1. Core: dependencies between cases (DP) — together with ADR-030 or before it, see open question O-2.
2. Configuration `worklist` and the demo world (WL, EX-01, EX-03).
3. Personal and shared workspaces, delegate and share, the combined view (PV).
4. Remote access with personal tokens (IF-01 to IF-03).
5. `todo.py` as a client, the move, the cut-over (IF-04, MV).
6. Akhil's worklist and the shared one (closes SYS-123).
7. The explanation page (EX-02).

## Open questions for the product owner

- **O-1 Privacy:** personal workspace per person (proposed) or one shared list with a filter?
- **O-2 Dependencies:** built here first, or as part of the release bundles (ADR-030)?
- **O-3 Ids:** keep cluster prefixes (proposed) or move to year numbering like `SW-2026-001`?
- **O-4 Tokens:** who issues them — the person on the account page (proposed), or only the administrator?
- **O-5 Agents' items:** today Axel holds most items. Do they stay in Chris's worklist with Axel as assignee
  (proposed), or does Axel get a worklist of his own?
