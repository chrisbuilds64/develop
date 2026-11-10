# REQ-006 — Cases within cases

**Status:** accepted 2026-11-10 (product owner). Decision record: ADR-033.

**Scope:** the core relation `partOf` for every application, its step, its view and its gate condition; the worklist
as the first application to use it. Not in scope: the release case of ADR-030 (it builds on this).

**Evidence** means a test in `apps/casefile/tests/test_case_tree.py`, unless the row names another.

## Requirements

### The relation

| # | Requirement | Evidence |
|---|---|---|
| CT-01 | A case may be part of one other case, of the same or a connected application instance; the reference is kept in the part only. | `test_a_case_is_part_of_one_case_and_only_the_part_says_so` |
| CT-02 | The step `part_of` sets, moves or removes the parent; it is journaled and stands in the part's thread. The parent's files are not written. | `test_part_of_is_a_journaled_step_that_never_writes_the_parent` |
| CT-03 | A parent that does not exist, that the person may not see, or that would close a circle is refused. | `test_a_parent_must_exist_be_visible_and_not_close_a_circle` |
| CT-04 | The depth of the tree is not limited and has no levels or types in the core. | `test_a_tree_has_any_depth_and_no_levels` |

### The view

| # | Requirement | Evidence |
|---|---|---|
| CT-05 | A case shows its parts the viewer may read — title, stage, assignee, closed or not — and the count closed against all; parts the viewer may not read are counted only. | `test_a_parent_shows_its_readable_parts_and_counts_the_rest` |
| CT-06 | A card shows the parent it belongs to and, for a parent, its progress. | `test_a_card_carries_its_parent_and_progress` |
| CT-07 | A new case can be started as a part of a given case. | `test_a_new_case_can_start_as_a_part` |
| CT-08 | The parent is a filter on board and table, so one branch can be shown alone. | `test_the_parent_is_a_facet` (test_facets.py) |

### Closing and gates

| # | Requirement | Evidence |
|---|---|---|
| CT-09 | Without configuration a parent may close while parts are open. | `test_a_parent_closes_with_open_parts_by_default` |
| CT-10 | A stage may require `parts_closed` for a move; the move is refused with the open parts named, in the viewer's words. | `test_parts_closed_holds_a_move_and_names_the_open_parts` |
| CT-11 | `parts_closed` can be an item of a gate protocol (ADR-029) once those exist. | — (with ADR-029) |

### Delegation

| # | Requirement | Evidence |
|---|---|---|
| CT-12 | A delegated part's new case becomes the part; the delegator's closed case keeps its reference. | `test_delegating_a_part_keeps_the_tree` |

## The parts, one case each

1. Core: `partOf`, step `part_of`, resolver, checks (CT-01 – CT-04).
2. View and API: parts in the case view, parent and progress on cards, start as a part, facet (CT-05 – CT-08).
3. Condition `parts_closed` (CT-09, CT-10), delegation (CT-12).
4. Worklist: `todo.py` learns `--part-of`; ADR-030 is rewritten to use the relation.
