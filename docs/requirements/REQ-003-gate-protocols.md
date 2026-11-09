# REQ-003 — Gate protocols: what a person checked before a gate opened

**Status:** proposed 2026-11-09, waiting for the product owner. High priority. Decision record: ADR-029.

**Scope:** the core (`apps/casefile/casefile/`), the surface (`apps/casefile/web/`), the configuration of Shipyard
(`config/shipyard/`) and of the database change file (`config/aenderungsakte/`).

**Evidence** means a test that fails when the line breaks. None is written yet: every line below is a requirement
before its build, and its test comes with it.

## The protocol

| # | Requirement | Evidence |
|---|---|---|
| GP-01 | A gate protocol is a deliverable of the case, written only through the core, under the case lock, atomically. | planned |
| GP-02 | Its standing items come from a template in the application's configuration; a workspace may have its own in its tree. Whether a person may replace the template or only add items is a right of their role in the workspace. | planned |
| GP-03 | A helper may draft case items from the task; each item records where it came from (template, helper, person). | planned |
| GP-04 | Before the first verdict, the person who holds the gate may strike an item (with a reason) or add one. | planned |
| GP-05 | Each item is a question with a type and a criterion: yes/no, a number (equal, range, limit), a choice, or text/file/link as evidence. An answer that misses the criterion fails the item. | planned |
| GP-06 | Nothing is preset: an item without a verdict is open, and a verdict is refused unless the person gave it. | planned |
| GP-07 | Not applicable needs a reason; failed needs what was seen. Evidence may be a note, a file in the case or a link. | planned |
| GP-08 | Who may answer is a role on the question. An objective question may be answered for good by an agent in its role; a judgement question has a person's role by default, where an agent may only observe and attach evidence. The gate is opened only by the role that holds it. | planned |

## The gate

| # | Requirement | Evidence |
|---|---|---|
| GP-09 | An action that names a protocol is offered only when every must-item passed or is not applicable with a reason. | planned |
| GP-10 | A failed must-item offers the way back instead, and the failed item is the reason of that step. | planned |
| GP-11 | A completed protocol is sealed with the person and the time, and a readable record is compiled beside it. | planned |
| GP-12 | A case sent back and deployed again gets a new protocol version; the earlier one stays readable. | planned |
| GP-13 | Each item is a must-item or a should-item. A failed should-item does not block the gate; it is shown at the decision and stays in the sealed record. | planned |

## Shipyard

| # | Requirement | Evidence |
|---|---|---|
| GP-20 | ENTW is accepted with an installation check, held by a developer: tag and commit on the stage, services active, migrations run, logs without new errors. | planned |
| GP-21 | TEST is accepted with a business acceptance, held by the role `acceptance`, never by the change's developer; its case items are the instructions for this change. With us the role is held by the product owner in personal union or by a peer (Akhil). | planned |
| GP-22 | PROD is closed with a production check, held by a developer: the installation check's items plus the way back. | planned |
| GP-24 | The approval (merge) is given with a code review protocol, held by the product owner or a peer, never by the change's author: scope matches the task, a test for every requirement line, no secrets or internal names, architecture boundaries hold. The checks helper observes what it can (diff against the task, new tests, guards); the reviewer decides. | planned |
| GP-23 | The verify helper fills observations for the items it can check and decides none. | planned |

## The database change file

| # | Requirement | Evidence |
|---|---|---|
| GP-30 | Before a deploy the core records the invalid objects of the target schema as the baseline. | planned |
| GP-31 | After the deploy, "no new invalid objects against the baseline" is a standing must-item, observed by the core with the query and its result as evidence; compile errors of the changed objects are listed with it. | planned |
| GP-32 | A new invalid object fails the item, and the gate offers the way back, not the next stage. | planned |
| GP-33 | A data change states before its deploy how many rows it will change (from the analysis). After the deploy "rows changed = rows predicted" is a standing must-item, observed by the core with the query and the counts as evidence. | planned |
| GP-34 | A change may name reference data: chosen rows with their expected values after the deploy (the case's own examples, e.g. one open and one closed order). After the deploy the core reads those rows and compares them field by field; every difference is evidence on a must-item. | planned |

## Not in this version

Signatures beyond the person's login; protocols that run across several cases; timing and scheduling of tests.
