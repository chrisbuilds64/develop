# REQ-002 — Shipyard: our own software changes as cases

**Status:** proposed 2026-11-08, waiting for the product owner. Decision E5 of 2026-11-08: a software house that
builds on casefile runs its own changes through casefile. This is that application: **Shipyard**, where our software is built and
launched, beside PressRoom, where our content is.

**Scope:** the configuration `apps/casefile/config/shipyard/` and one live workspace on production. No new
core code: the application is configuration only (ADR-015). Decision record: ADR-027.

**Evidence** means a test in `apps/casefile/tests/test_shipyard.py`, unless the row names another.

## The way of a change

The stages are the way of a change in [CONTRIBUTING.md](../../CONTRIBUTING.md), one stage per step.

| Stage | Whose move | Leaves when | Record in the case |
|---|---|---|---|
| 10 Task | product owner | the product owner confirms the task | `task.md` — what and why, which requirement lines |
| 20 Build | developer | a pull request is open | `pr.md` — link, what changed, what was tested |
| 30 Checks | developer | the checks are green | `checks.md` — link to the check run, result |
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
| SW-08 | *(proposed, ADR-032 decision 10)* A repository is a data point on a git connector; it names its main branch and its required checks. | — |
| SW-09 | *(proposed, decision 11)* With several repositories bound, a case names its repository at creation; with one, it is preset. | — |
| SW-10 | *(proposed, decision 11)* A change across repositories is a case with one part per repository; the parent closes when every part is closed. | — |
| SW-11 | *(proposed, decision 12)* A helper works in a working tree of the case's repository that the runner prepared; no helper instruction names a path. | — |
| SW-12 | *(proposed, decision 13)* The merge gate reads the required checks of the case's repository. | — |
| SW-13 | *(proposed, decision 14)* A deploy goes through the stage's target data point and its command. | — |
| SW-08 | A new change is numbered within its year: `SW-2026-001`. | configuration (`theme.create`), numbering covered by REQ-001 C-08 |
| SW-09 | The live workspace sits in its own folder, apart from content. | operations, not a test |
| SW-10 | Each gate orders the helper's next stretch: the confirmed task the build, the pull request the checks, the merge and each acceptance the release (ADR-028). | `test_each_gate_orders_the_helper_for_the_next_stretch` |
| SW-11 | Red checks send the change back to the build, with what failed. | `test_red_checks_send_the_change_back_to_the_build_with_what_failed` |
| SW-12 | A helper makes its moves through the core, as its agent and never as a person. | `apps/casefile/tests/test_cli_step.py` |
| SW-13 | A secret reaches only the skill whose policy names it; an agent's runs are billed to the person it belongs to. | `apps/cockpit/tests/test_runner_secrets.py` |
| SW-14 | A deploy happens only when the case stands in the stage that deploys it, only for a tag on `main`, and never above the requesting space's stage; the outcome goes back to the case. | `infra/pressroom/tests/test_requests.py` |

## Not in this version

- No webhook from the code host: the checks helper waits for the checks itself.
- Code-writing runs share the runner's user (ADR-028, *trust boundary*); a user and sandbox of their own come with the
  security package (REQ-001 W-04).
