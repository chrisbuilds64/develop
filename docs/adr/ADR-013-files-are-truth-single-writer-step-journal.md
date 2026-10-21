# ADR-013: Files Are the Truth, One Writer, Steps Through a Journal

**Status:** Accepted (Chris, 2026-10-21)
**Date:** 2026-10-21

---

## Context

The case pipeline stores every case as a folder: the stage folder it sits in is its status, `meta.json` describes it, `review.md` is an append-only thread, deliverables are versioned files, and agent runs are order files in `_runs/`. Several tools write into this tree, a web surface reads it, and people sync it to their laptops.

In the previous surface, "Approve" appended a review entry but did not move the case. Approval and move were two separate acts the user had to know about. The redesign makes every step one button. That needs a step that cannot end half-done.

## Decision

1. **The folders stay the source of truth.** Anything else (caches, indexes) must be rebuildable from them.
2. **One writer.** A core service owns all writes. The existing tools become a library inside it; their command lines stay as thin wrappers, so the web surface, the agent runner and a terminal take the same code path.
3. **A step is a journaled, idempotent transaction:** per-case lock in the core process → check precondition (expected stage, required deliverables, rights) → write `_steps/<id>.json` with `intent` → append the review entry carrying the step id → move the folder → mark the journal `done`. The same step id twice is a no-op. On start-up the core completes every journal left in `intent`.
4. **Manual changes are accepted.** A folder moved by hand or a file dropped through sync is taken as the new state and recorded as a "detected" entry.
5. **Whose turn** is one pure function `turn(case)` returning an ordered list (actor, action, label, reason, blockers, since). Surface, CLI and agents call the same function.

## Alternatives

- **Locks and ETags on the sync server (WebDAV LOCK, If-Match, webhooks):** depends on server features whose behaviour on shared group folders is unverified, and does not stop sync clients from writing conflicting copies.
- **A database as the source of truth:** loses the property that a customer can take their cases away as plain folders, and adds a store that must be backed up separately.

## Consequences

- A step can be reasoned about and tested in isolation (double click, stale precondition, crash after the entry, manual move).
- The thread remains the audit trail; nothing happens off-thread.
- A database index can be added later without changing the contract.
