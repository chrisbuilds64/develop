# REQ-004 — Release bundles and maintenance windows

**Status:** proposed 2026-11-09, waiting for the product owner. Built after the DOAG week. Decision record: ADR-030.

**Scope:** the configuration of Shipyard (`config/shipyard/`), the deploy service (`infra/pressroom/`), the Shipyard
helpers, the core where a release case reads its change cases.

**Evidence** means a test that fails when the line breaks. None is written yet: every line is a requirement before its
build.

## The guard (both ways of delivery)

| # | Requirement | Evidence |
|---|---|---|
| RB-01 | The deploy service refuses a tag older than the one running on the stage. | planned |
| RB-02 | The deploy service refuses a tag that contains a pull request, since the tag running on the stage, which belongs to no case that has reached the stage. | planned |
| RB-03 | Each refusal names the tag or the pull request that caused it. | planned |

## Ways of delivery

| # | Requirement | Evidence |
|---|---|---|
| RB-10 | A workspace delivers continuously or in step; the configuration says which. | planned |
| RB-11 | In step, a change case accepted on TEST goes to "accepted, waiting for release" and does not order a PROD deploy. | planned |
| RB-12 | A waiting change case is assigned to a release: the next by default, another by the product owner's choice. | planned |

## The release case

| # | Requirement | Evidence |
|---|---|---|
| RB-20 | A release is a case, one per maintenance window, created from the calendar of windows. | planned |
| RB-21 | The release case shows its change cases and which of them are accepted. | planned |
| RB-22 | At the cut-off the helper cuts the release line from `main` and lists every pull request on it since the last production release with its case. | planned |
| RB-23 | A pull request on the line without an accepted case of this release blocks the release; the helper prepares its revert on the line, and the product owner merges it. | planned |
| RB-24 | The bundle is accepted on TEST with a gate protocol: the items of each change plus regression (ADR-029). | planned |
| RB-25 | The deploy service deploys a release to PROD only inside its window. | planned |
| RB-26 | When the release is in production, its change cases close with a reference to the release. | planned |

## Hotfix

| # | Requirement | Evidence |
|---|---|---|
| RB-30 | A hotfix is one change case with one pull request that may go to PROD outside a window. | planned |
| RB-31 | A hotfix needs an approval beyond the product owner's acceptance, and it is entered into the calendar. | planned |

## Not in this version

Several releases cut at once; releases across several repositories; automatic choice of the window.
