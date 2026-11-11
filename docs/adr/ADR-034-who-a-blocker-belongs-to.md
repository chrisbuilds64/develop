# ADR-034: Who a Blocker Belongs To

**Status:** Proposed (2026-11-11). Requirements: REQ-007 (proposed). Build after acceptance.
**Date:** 2026-11-11

---

## Context

A case stops when something is in its way. Today the model knows two ways out:

- **The case is at fault.** A helper or a person sends it back (`checks_red`, `send_back`), and the helper that built
  it fixes it.
- **A person must act.** The case waits in a stage whose turn is a person: an approval, a decision, an answer to an
  open question.

There is a third kind, and the model does not know it: **the environment is at fault.** The case is fine and no
person needs to decide anything, but something it depends on is broken. Examples from the first week of Shipyard:

- The code host's CI machines could not resolve the package mirrors. Every browser check failed while installing the
  browser, before it tested anything. The checks helper saw this correctly and stopped with an open question. The
  product owner could neither rerun the CI jobs nor do anything else from the case.
- A helper build could not run its walk because the browser was missing on the runner host.
- A deploy interrupted a running helper on the same stage.

Every one of these was solved in a terminal, by someone who knew where to look. That is the exact situation the
product is meant to remove (ADR-028: Shipyard without a terminal). PressRoom has the same kind of fault: an image
service that is down, a file sync that hangs, an expired key.

Sending such a case back to its builder is wrong, because the builder cannot fix a mirror outage. Leaving it with the
person is wrong too, because the person sees a red case and has no means to act. A plain "retry" button helps only
with transient faults, and it teaches nothing: the same outage comes back and is retried again by hand.

## Decision

1. **A blocker has an owner: the case, a person, or the environment.** A helper that stops says which one it is. The
   stop is a thread entry with status `open` (as today) and a new field `blocker`: `case`, `person` or
   `environment`. The core does not guess the owner. The helper says it and the entry records it.

2. **The environment is everything the case does not own.** That covers the code host and its CI, the runners, the
   servers and their stages, the data connectors, keys and tokens, and outside services. The test is simple: if no
   change to the case's own documents or code can remove the blocker, it belongs to the environment.

3. **Operations is a role of the core, not of an application.** It is a helper with its own skill and its own entry in
   the run policy, configured per instance like every other helper. It sees more than a case helper:
   - the runs and their logs;
   - the state of the runners and stages;
   - the checks of the case's repository (ADR-032 decision 13);
   - the health of the connectors;
   - earlier operations cases.

   It may do more than a case helper, but only what restores the environment, and the run policy names each right. In
   Shipyard, for example, it may rerun failed CI jobs, restart a runner, and read the logs of a stage.

4. **What operations never does.** It never changes the case's documents or code. It never moves a case through a
   gate, never sends a case back, and never merges, deploys or deletes data. Its job ends where the case's own work
   begins.

5. **An environment blocker starts operations.** When a helper records an environment blocker, the core orders the
   operations helper for that case once, without a person pressing anything. A step that needs no decision runs by
   itself. If that attempt does not clear the blocker, the case shows the person a button such as "Have operations
   look again", in the application's words. An instance can switch the automatic first attempt off. A blocker set
   by a person in the case starts operations the same way.

6. **When the environment is restored, the interrupted step runs again.** Operations orders the same skill again for
   the same case, the step that stopped. It writes one entry in the case, in everyday language: what was wrong, what
   it did, and that the step is running again. The open blocker entry is answered by it.

7. **What operations cannot fix becomes an operations case.** Some faults need a person or take longer, such as a key
   only an owner can renew or a server that is down. Operations then:
   - opens a case in the operations instance of the tenant;
   - writes there what is wrong and who can fix it;
   - makes the blocked case wait for it (`waitsFor`, ADR-031 decision 5).

   The person sees in the blocked case: "Waiting for operations: <title>". When the operations case closes, the
   interrupted step runs again by itself.

8. **A recurring fault becomes a finding.** Operations reads the earlier operations cases before it acts. If the same
   fault has come back three times, the number set by the instance, operations does not only retry. It also opens an
   improvement case that names the cause. For the CI outage above, that means: the browser is installed from the
   package mirrors on every run instead of being cached.

9. **The terminal stays the emergency path, and it leaves a trace.** A person who fixes the environment outside the
   application records it afterwards as an operations case, the same way a change built outside is recorded with
   `record_done`. A fix that happens in a terminal and is never recorded is the gap this decision closes.

10. **Words for people without the background.** No surface shows `blocker: environment`, a run id or a job name to
    the person. The case says, for example: "The checks could not run because the test machine was not reachable.
    Operations is taking care of it." Details stay one click away for whoever wants them.

## Consequences

- **The core gets:**
  - one field on the thread entry (`blocker`);
  - one role in the run policy (`operations`);
  - one automatic order: an environment blocker starts operations once;
  - one resume step: operations orders the interrupted skill again.
- **Every helper skill learns to name the owner of a stop.** Today they describe it in prose. The checks helper of
  2026-11-11 already did exactly that.
- **Each tenant gets an operations instance**, a casefile application like the worklist, whose cases are the faults
  operations could not clear and the improvements it proposed.
- **Applications only configure.** They set which operations skill, which rights and which words. Shipyard and
  PressRoom share the role. A third application gets it by configuring it.

## Alternatives considered

- **A retry button per stage.** Rejected as the answer, kept as a fallback. It solves the transient case and hides
  everything else: nobody learns why the case stopped, and the same outage is retried by hand forever. Shipyard's
  `retry_checks` stays as the person's own means.
- **Give the case helpers the operations rights.** Rejected: a helper that builds code and may also restart runners
  and rerun checks can make its own red checks green without fixing anything. The separation is the protection.
- **Automatic retries in the runner, without a helper.** Partly kept: a run that ends in an environment blocker may be
  retried once by the runner after a pause, before operations is ordered (open question below). A blind retry loop
  alone is rejected for the same reason as the button.

## Open for the build

- Does the runner retry once by itself before operations is ordered, or does operations always decide?
- How far does operations see across instances of one tenant? It needs runs and logs, but not the content of other
  cases.
- Where does the operations instance live, and who besides the product owner sees it?
- The rights of operations per application: Shipyard needs the code host, PressRoom needs the file sync and the
  image service.
