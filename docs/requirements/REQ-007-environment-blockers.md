# REQ-007 — Environment blockers and operations

**Status:** proposed 2026-11-11. Decision record: ADR-034.

**Scope:** the owner of a blocker on every thread entry that stops a case, the core role `operations`, its automatic
first attempt, the resume of the interrupted step, and the operations instance. Shipyard and PressRoom are the first
applications to configure it.

**Evidence** means a test in `apps/casefile/tests/test_operations.py`, unless the row names another. Tests are
named when the rows are built.

## Requirements

### The blocker

| # | Requirement | Evidence |
|---|---|---|
| OP-01 | A thread entry that stops a case carries its owner: case, person or environment. The core records it and does not guess it. | |
| OP-02 | No surface shows the owner as a code or field name. The person reads in everyday language what stopped the case and who is taking care of it. | walk |

### Operations

| # | Requirement | Evidence |
|---|---|---|
| OP-03 | Operations is a helper role of the core, configured per instance in the run policy with its own skill and its own rights. | |
| OP-04 | Operations never changes the case's documents or code, never moves a case through a gate, never sends it back, merges, deploys or deletes data. | |
| OP-05 | An environment blocker orders operations once without a person. An instance can switch this off. Further attempts are a button for the person whose turn it is. | |
| OP-06 | When operations has restored the environment, it orders the interrupted skill again for the same case and answers the blocker entry in everyday language. | |
| OP-07 | What operations cannot clear becomes a case in the tenant's operations instance. The blocked case waits for it and runs its interrupted step again when that case closes. | |
| OP-08 | A fault that has recurred as often as the instance sets also opens an improvement case naming the cause. | |
| OP-09 | A fix made outside the application can be recorded afterwards as an operations case. | |
