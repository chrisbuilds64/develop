# ADR-030: Release Bundles and Maintenance Windows

**Status:** Proposed (2026-11-09). Decided by the product owner the same day (option A, a release line cut at the
cut-off); this record waits for *Accepted*. Built after the DOAG week. Requirements: REQ-004.
**Date:** 2026-11-09

---

## Context

Shipyard (ADR-027, ADR-028) takes one change from its task to production on its own: once the business has accepted it
on TEST, it goes on to PROD. That is continuous delivery, and it is right for a small team on its own system.

Most of our customers deliver differently. Production may change on maintenance days; several accepted changes go out
together; what is not accepted by a cut-off waits for the next date. The way of a change has to allow that: "accepted"
and "delivered" are two states, and a change has to be able to wait between them.

Two gaps show already with changes in parallel, before any bundling. Each change tags its own merge commit, and `main`
is one line: a later change's tag contains every earlier merge, so deploying it can carry a change that was never
accepted on that stage. And deploying an older tag after a newer one rolls the stage back without anybody noticing.

## Decision

1. **Two ways of delivery, chosen per workspace:** *continuous* (accepted on TEST, then PROD, as today) and *in step*
   (accepted on TEST, then waiting for a release).
2. **In step, a change case ends at "accepted, waiting for release"** and is assigned to a release: the next one by
   default, another one by choice.
3. **A release is a case of its own** in Shipyard, one per maintenance window, created from a calendar of windows. It
   collects its change cases and shows which are accepted and which are still missing.
4. **Option A: merges go to `main` as today; at the cut-off the release line is cut** (`release/<date>`). From then on
   `main` moves on and the release line does not. The helper checks that every pull request on the line since the last
   production release belongs to an accepted change case of this release; what must not travel, the helper prepares to
   revert on the release line, and the product owner merges the revert.
5. **The bundle is accepted as a whole on TEST** with a gate protocol (ADR-029): the items of every change it contains
   plus regression.
6. **PROD only inside the window.** The deploy service refuses a release outside its window.
7. **A hotfix is a narrow way of its own:** one change, one pull request, deployed outside the window with an
   additional approval, and entered into the calendar.
8. **The server guards every deploy, in both ways of delivery:** no tag older than the one running on the stage; and
   every pull request between the running tag and the requested one belongs to a case that has reached the stage.
9. **When the release is in production, its change cases close** with a reference to it.

## Consequences

- Shipyard shows both ways a software house delivers: continuous for our own work, in step for a customer's.
- The guard in 8 closes the two gaps for continuous delivery too, before any release case exists. Until it is built,
  only one change may be between its merge and PROD at a time (the rule for the DOAG week).
- The deploy service learns the calendar and reads more than one case per request (the bundle).
- New: the release case type, the calendar, the cut and revert helpers, the bundle protocol. Order of building: the guard
  (8), then gate protocols (ADR-029), then the release case and the calendar.

## Alternatives considered

- **B: merge only after acceptance.** `main` would hold only accepted work, and ENTW and TEST would run an integration
  line (as in GitFlow). Cleaner history, but every change is merged twice and the two lines conflict. Rejected for now.
- **Feature flags.** Everything goes out at once and is switched on later. Rejected: more than a small team needs, and
  a database change cannot be switched off.
- **Several changes in one pull request.** Rejected: a line of code no longer belongs to one task, and a check no longer
  to one feature. Bundling happens at the release, not at the commit.
