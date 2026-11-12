# ADR-035: Going Back, and Resuming Where the Case Stood

**Status:** Accepted (2026-11-12, Chris). Requirements: REQ-001 T-14 to T-19. Built as SW-2026-030.
**Date:** 2026-11-12

---

## Context

A case moves forward through its stages, and each gate is passed once. In real work somebody notices late that an
earlier piece needs a change. The first PressRoom piece that ran through the application showed it on its first day:
the text was approved, the images were made, and then the author wanted to change the text.

Today the core offers three ways back, and none of them fits:

- `take_back` returns a case exactly one stage, and only into the viewer's own stage.
- `undo` takes back the viewer's own newest move, while nothing has happened since.
- `correct` and `reopen` are for a decision that is sealed for good and for a case that is closed.

Going back further is done by hand, and coming forward again means passing every gate once more, also the gates whose
subject did not change. An approved image is approved again although nobody touched it. That teaches people to
approve without looking.

The same holds for our own software changes: until a change is in production, a late finding in the task should not
cost the checks and approvals that still hold.

## Decision

1. **A case can go back to any stage it has stood in, until it is final.** One step, `go_back`, with the target stage
   and a reason. The case stands there again, the thread says who took it back, from where, and why. A helper never
   goes back on its own; a case does not go back while a helper is at work on it.

2. **What is final is the application's to say.** A stage carries `final: true` (PressRoom: published; Shipyard:
   production). A case that has reached a final stage does not go back; there the existing `correct` and `reopen`
   apply. The core names no stage.

3. **A case knows how far it has come.** The furthest stage it has stood in, in the configured order, is its mark.
   It is read from the thread, where every move is recorded, and stored nowhere else.

4. **A passed gate records what it covered.** When a gate is passed, the step notes the deliverables the gate asked
   for, each with its version and a fingerprint of its content. The gate holds while those deliverables are unchanged.
   A new version of one of them, or a changed file, and the gate no longer holds. Nothing is deleted: the earlier
   approval stays in the thread and in the protocol as what it was.

5. **Work that was redone is approved again; work that was not is not.** In the stage a case went back to, the gate
   is passed again like the first time, protocol included (a new version, ADR-029). In every later stage whose gate
   still holds, the case may pass without a new approval: a step `resume` takes it forward, one stage or several, up
   to the first stage whose gate does not hold, and never beyond its mark.

6. **Resuming is offered, never automatic.** Whether an image still fits a changed text is a judgement, and the
   core cannot make it. The person who stands at a stage whose gate holds sees both moves: resume, or do the stage's
   work again (which ends the gate's hold by producing a new version). The core checks only what it can check: that
   the approved deliverables are unchanged.

7. **No mandatory stage is skipped.** `resume` passes only gates that were passed before and still hold. A stage the
   case never stood in is entered by its own gate, like always.

8. **Who may go back** is one function, as with `take_over` (REQ-001 T-10): for now every person of the application,
   later a rule of rights in that one place.

## Prior art

- **Stale approvals on a code host.** GitHub can dismiss a pull request's approvals when new commits are pushed. That
  is decision 4 for one kind of gate and one kind of deliverable. We use the same idea for every gate and keep the
  reverse too: an approval whose subject did not change stays.
- **Incremental builds and CI caches.** A build step runs again only when its inputs changed, keyed by a hash of
  them. Decision 4's fingerprint is that key; decision 5 is "do not rebuild what is up to date", applied to approvals.
- **Process engines (Camunda, Flowable).** Process instance modification moves a running instance to an earlier
  activity. It is an operator's tool, it does not know which later decisions still hold, and it is not offered to the
  person doing the work. We take the capability and add the rule that makes it safe to hand to that person.
- **Issue trackers.** A workflow may allow a transition back. Coming forward again repeats every transition; nothing
  remembers what was already approved.

What we use: the thread as the record of moves, the protocols of ADR-029, the versioned deliverables. What is new:
the mark, the gate's record of what it covered, and `resume`.

## Consequences

- A late change costs the work it changes and nothing else.
- A gate's approval means "this version", visibly. That is a stricter statement than today's.
- Every gate step computes fingerprints of a few files. For large deliverables (video) the fingerprint is the file's
  size and modification time, not its content.
- The surface needs two new moves and one new line: "was here before: <stage>".
- Open: helpers that run on entering a stage (`auto`) do not run on `resume`. A deploy stage is never resumed into;
  for Shipyard the stages that deploy are entered by their own gate every time.
