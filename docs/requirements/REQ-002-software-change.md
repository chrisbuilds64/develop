# REQ-002 — Software change: our own changes as cases

**Status:** proposed 2026-11-08, waiting for the product owner. Decision E5 of 2026-11-08: a software house that
builds on casefile runs its own changes through casefile. This is that application.

**Scope:** the configuration `apps/casefile/config/softwareaenderung/` and one live workspace on production. No new
core code: the application is configuration only (ADR-015). Decision record: ADR-027.

**Evidence** means a test in `apps/casefile/tests/test_softwareaenderung.py`.

## The way of a change

The stages are the way of a change in [CONTRIBUTING.md](../../CONTRIBUTING.md), one stage per step.

| Stage | Whose move | Leaves when | Record in the case |
|---|---|---|---|
| 10 Task | product owner | the product owner confirms the task | `auftrag.md` — what and why, which requirement lines |
| 20 Build | developer | a pull request is open | `pr.md` — link, what changed, what was tested |
| 30 Checks | developer | the checks are green | `pruefung.md` — link to the check run, result |
| 40 Approval | product owner | merged, or sent back with a reason | — |
| 50 Release | developer | the tag is deployed to ENTW | `release.md` — tag, ENTW deploy |
| 60 ENTW | product owner | ENTW accepted, released to TEST | — |
| 70 TEST | product owner | TEST accepted, released to PROD | `test.md` — TEST deploy |
| 80 PROD | developer | the PROD deploy is recorded | `prod.md` — PROD deploy |
| 90 Closed | — | — | — |

## Requirements

| # | Requirement | Evidence |
|---|---|---|
| SW-01 | A change passes every stage of the way above, and only in that order. | `test_the_whole_way_from_task_to_prod` |
| SW-02 | Only the product owner confirms a task, merges and accepts a stage. | `test_a_task_moves_only_when_the_product_owner_confirms_it` |
| SW-03 | Four eyes: whoever wrote the newest version of the pull request record cannot merge it. | `test_the_author_of_the_pull_request_cannot_merge_it` |
| SW-04 | Nothing moves on without its record: no build without a task, no merge without the recorded check run. | `test_the_merge_waits_for_the_recorded_checks_and_can_send_the_change_back` |
| SW-05 | A change sent back from approval carries the reason. | same test |
| SW-06 | A developer may be a person or an agent; while the change is built, whose move it is names the developers, at each gate the product owner. | `test_whose_move_names_the_agent_while_it_builds_and_the_owner_at_each_gate` |
| SW-07 | Every stage, action and record has its word in German and English. | `test_both_languages_name_every_stage_action_and_file` |
| SW-08 | A new change is numbered within its year: `SW-2026-001`. | configuration (`theme.create`), numbering covered by REQ-001 C-08 |
| SW-09 | The live workspace sits in its own folder, apart from content. | operations, not a test |

## Not in this version

- Pull request and check results are recorded by hand. A webhook from the code host comes later.
- No helper builds or deploys from the case. The developer records what was done; the helper only answers questions.
