# ADR-012: Gatehouse Synthesis — Instructions Live in the Pack, Not in the Code

**Status:** Accepted
**Date:** 2026-09-04

---

## Context

Gatehouse (UC-AG-004) gained a second model-driven stage on 2026-09-04: after the interview closes, the system reads the answers back and writes an `analysis.md`. Where the first stage (follow-up questions, ADR-011) only ever *asks*, this stage *asserts*. It tells a client something about their own organisation.

That difference matters more than it first appears. A follow-up question that misses is a wasted question — the operator moves on. A finding that misses is a claim made to a paying client about how their company works, in a written artifact they keep. The two stages share an adapter and share nothing else in terms of risk.

Two constraints collide here:

- **`develop/` is PUBLIC** (MIT, Core Principle 1). Every line of the harness is readable by anyone, competitors included.
- **The question canon is private IP.** ADR-010 already separates them: the code knows no questions, the packs carry them (`products/base-build/kit/packs/`, private).

The open question was which side of that line the *synthesis instructions* fall on — the text that tells the model what a finding may claim, what evidence it must carry, and what it must never produce.

## Decision

**The synthesis instruction text lives in the pack, in a `[synthesis]` section. The code carries only the mechanics.**

`synthesize.py` loads the section, sends it, and enforces the mechanical guarantees. It contains no sentence about what a finding may say.

The pack-side rules, as written for `short-form-en`:

- **Every finding quotes verbatim and names the question number.** A finding that cannot point at the words that produced it is dropped, not softened.
- **No score, no traffic light, no ranking.** These invite the reader to act on a number rather than on the evidence.
- **No recommendation.** Recommending is a different product stage with a different liability profile; the read-back describes what the answers contain and stops there.

The code-side guarantees, which are not negotiable per pack:

- Truncated model output raises rather than rendering. The first run of this stage hit a hard-coded `max_tokens = 1024`, cut off mid-sentence, and the page presented the torso as a finished analysis. Limit raised to 4096, and truncation now throws.
- Empty output raises. One run returned 976 output tokens and no text block, and wrote an empty analysis. The cause is still unexplained; the guard is in place regardless.
- Every call is logged at the adapter boundary as usual (ADR-011).

## Alternatives

- **Instructions as a constant in `synthesize.py`.** Simplest, and the version that first suggested itself. It publishes the exact wording of what our analysis is allowed to claim into a public repository — the evidential discipline is the differentiator, not the Python around it. It also makes the rules uniform across every pack, so a domain that needs different evidence rules cannot have them without a code change.
- **A third location — a config file next to the code.** Avoids the public-repo exposure, and creates a second private artifact to keep in sync with the pack. Two files that must agree will eventually disagree; ADR-010's one-pack rule exists to prevent exactly that.
- **Let the model decide what a finding needs.** No instruction text at all, just the answers and "summarize". Produces plausible output on the first try and fails Foundation Principle 12 by construction: plausible is not correct, and without a stated evidence rule there is nothing to validate against.
- **Ship findings with a score.** Clients ask for it, and it demonstrably sells. It also converts an evidence-bearing observation into a number that survives the loss of its evidence — the number gets quoted in a meeting three weeks later and the quote that produced it does not.

## Why the pack, specifically

**What an analysis may claim is a canon decision, not an engineering decision.** It belongs to the same authority that owns the questions, and it changes on the same clock. Putting it in the code would split one editorial decision across two repositories with two different visibilities and two different approval paths.

**It keeps the public/private line in one place.** After this decision the rule is still readable in one sentence: the harness is public and knows nothing; the pack is private and carries everything domain-specific. A reader of `develop/` can verify the mechanics and learns nothing about the method.

**It makes per-domain evidence rules possible without a release.** `short-form-en` demands a verbatim quote plus a question number. A future pack for a regulated domain may need a stricter rule. That is a pack edit, not a deployment.

## Consequences

**Benefits:**
- The evidential discipline stays private while the mechanism stays inspectable.
- Evidence rules become a per-pack property, versioned with the questions they apply to.
- The mechanical guarantees (no truncation, no empty output) hold for every pack, including packs written later by someone else.

**Trade-offs:**
- A pack can now weaken its own evidence rules. Nothing in the code enforces "quote verbatim" — that guarantee is editorial, and it is only as strong as pack review. This is the real cost of the decision and it should not be described as anything else.
- Two artifacts must be read together to know what the system will output. The code alone no longer answers "what can this claim".
- A pack without a `[synthesis]` section has no read-back stage. That is intentional (`core-de` currently has none), but it means the capability is invisible unless someone checks the pack.
- The empty-output cause remains unexplained. The guard converts a silent wrong result into a loud failure; it does not fix the underlying behaviour.

## Verification

Dry run on 2026-09-04 against a real short-form interview: three findings, one of each kind, each carrying a verbatim quote and its question number. Test suite extended — 30 green, including one test that pins the routing failure found the same day (the new `synthesis` task fell through to the default profile and silently added a second destination to the client-facing list).
