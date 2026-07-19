---
id: ADR-001
title: Skill Review Graph — Graph Topology and State Design
status: ACCEPTED
date: 2026-05-31
context: LangGraph Step 02 — Italy Workshop 2026-06-19
deciders: Chris (Human Authority), Axel
---

# ADR-001: Skill Review Graph — Graph Topology and State Design

## Decision

Parallel fan-out topology. Axel and Atlas review the same proposal independently and simultaneously. Human gate after both reviews complete. No synthesis node.

## Context

Step 02 of the LangGraph multi-agent system. Goal: two agents (Axel = Claude, Atlas = GPT-4o) evaluate the same input proposal from different perspectives. Chris reviews both outputs and makes a decision.

Constraints:
- KISS — single output, no unnecessary nodes
- Demo-able at Italy Workshop (medium complexity, visible in terminal)
- Must be clearly different from Step 01 (dialogue loop) — Step 02 is a review system, not a conversation

## Alternatives Considered

**Option A — Sequential (Axel → Atlas → Chris)**
Axel reviews first, Atlas sees Axel's review before writing its own.
Rejected: anchoring effect. Atlas's review would be influenced by Axel's framing. Independent perspectives are the point.

**Option B — Parallel fan-out (chosen)**
Axel and Atlas review simultaneously, no visibility into each other's output.
Accepted: genuine independence. Both agents work from the same proposal, surface different concerns.

**Option C — Iterative debate (Axel ↔ Atlas, multiple rounds)**
Agents see each other's reviews and respond, Chris intervenes.
Deferred: higher complexity, harder to demo cleanly, better suited for Step 03+.

## Graph Design

```
         ┌──────────────┐
         │   proposal   │  (input)
         └──────┬───────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
  [axel_review]    [atlas_review]    (parallel, independent)
  Claude Sonnet    GPT-4o
       │                 │
       └────────┬────────┘
                ▼
        [human_gate]               (interrupt — Chris reviews both)
                │
                ▼
          [final_output]           (proposal + both reviews + Chris decision)
```

## State Schema

```python
class ReviewState(TypedDict):
    proposal: str           # input: the thing being reviewed
    axel_review: str        # Axel's assessment
    atlas_review: str       # Atlas's assessment
    human_decision: str     # Chris: "approved" | revision instruction
    final_output: str       # assembled output
```

## What Is Given Up

- No cross-pollination between agents — they cannot build on each other's observations in v1
- No synthesis node — Chris gets raw reviews, not a consolidated recommendation
- No iteration — if Chris sends back for revision, the loop is not yet implemented (Step 03+)

## Consequences

- Simpler to implement than Step 03+ (no inter-agent communication)
- Demonstrates parallel fan-out + human gate as architectural pattern (Italy Workshop intent)
- `final_output` is the artifact: proposal + two independent reviews + human decision in one document
- Revision loop and agent cross-pollination are explicitly deferred — not forgotten

## Reference

Canon: `canon/software/principles.md` — Principle 6 (Human-in-the-Loop Is Architecture, Not Overhead)
Implementation target: `develop/experiments/langgraph/02_skill_review_graph.py`
