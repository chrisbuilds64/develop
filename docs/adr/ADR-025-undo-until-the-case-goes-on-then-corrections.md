# ADR-025: Undo Until the Case Goes On, Then Corrections

**Status:** Accepted (Chris, 2026-11-08). Proposed in the design hand-back, requests 1 and 2. The points under
*Open* stay open.
**Date:** 2026-11-05

---

## Context

The redesign confirms a step with one key ("Confirm and carry out", Enter). One key makes a slip easy: the wrong
amount approved, the right case sent to the wrong stage. Noticed a minute later, the clerk should be able to take it
back without ceremony. Noticed after the next person has acted on it, the decision has become a fact others relied on;
insurance work then needs the original to stay visible and the change to stand beside it with a reason.

ADR-013 makes a step whole or not at all and the thread append-only. Neither rule changes here. What is new is a step
that takes an earlier one back, and an entry that corrects one.

## Decision

1. **Undo is a step** (`undo`, built in). It takes back the viewer's newest move on the case while the case has not
   gone on: no entry after it by anybody, the case still where the move put it, no helper ordered by it, nothing sent
   or written beyond the move (a hand-off to another application, a rated quote, a composed document, a date or link
   in `meta.json`). The case returns to where it was; the thread gets an entry with status `undone` and
   `Corrects: <the decision's entry>`; the first step's journal reads `undone`, so it no longer counts as done (four
   eyes, the rhythm). Nothing is deleted. Only the person who made the move can undo it, and an undo is not undone.
2. **After that, a correction** (`correct`, built in). A decision entry (one a step wrote, with a move or an amount)
   gets a correction beside it: status `correction`, `Corrects: <entry>`, the reason (required) and, where it changes
   one, the corrected amount. The case does not move; the original entry stands unchanged. A person may correct a
   decision when they may act in the stage it was taken in, or as operator. An agent may not.
3. **One new attribute in the thread**, `Corrects`, written like `Resolves`. Older readers ignore it. The case view
   derives `corrected_by` on each entry and offers `undo_step` / `undo_word` while an undo is possible.
4. **The surface's "sealed"** is exactly the point where `undo_step` goes empty: from then on the case offers
   "Open a correction".

## Open

- **Holding outgoing steps.** A step that sends something at once (ordering an assessment hands an order to the
  assessor's application) is never undoable under rule 1. The design's original wish was to hold such a step and
  carry it out only when the next one begins, or after a grace period (say 30 s, the length of the undo toast). That
  needs a deferred part of `_complete` and a timer in the core; left for a later decision.
- **Four eyes on corrections.** A correction of a four-eyes decision does not itself require a second person yet.
- **Corrections in the settlement flow.** A corrected amount is recorded; it does not yet change what a later stage
  reads as the amount to pay.

## Alternatives

- **Delete the entry and move back.** Breaks the append-only thread and leaves no trace of a decision others may
  have seen.
- **A time window instead of "until the case goes on".** Simpler to explain, but wrong both ways: too short for a
  quiet case, too long for one the next person picked up a second later.

## Consequences

- One key stays safe to press: the newest slip is one undo away.
- The audit trail stays complete: every decision, its undoing and its corrections are in the thread, in order.
- `Journal.status` gains `undone`; `Entry` gains `corrects` and the derived `corrected_by`.
