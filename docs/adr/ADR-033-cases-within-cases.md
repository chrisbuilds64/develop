# ADR-033: Cases Within Cases

**Status:** Accepted (2026-11-10, product owner). Requirements: REQ-006.
**Date:** 2026-11-10

---

## Context

A case can already wait for other cases (ADR-031 decision 5, `waitsFor`), and a delegation links the new case to the
one it came from. What it cannot do is *consist of* other cases.

The product owner's example (2026-11-10): a party is one item; food, music and invitations are items under it, each
delegated to somebody else; food may again be split into shopping and cooking — or stay one item that holds the
shopping list, the recipe and the steps as its documents. How fine somebody splits is their choice, at every level.

The same shape shows in software delivery: ADR-030 decision 3 has a release case that "collects its change cases"; a
release may consist of sub-projects, and those of modules that are installed one by one. And in claims a main claim
may hold partial claims. Each application would otherwise grow its own way of collecting cases.

## Decision

1. **A case may be part of one other case.** The reference is written like a dependency (`PTY-1`, or
   `instance:CASE` for a case of another connected instance) and kept in `meta.json` under `partOf`. One parent at
   most: the cases form a tree. A case that must also respect another branch *waits for* it (`waitsFor`); the two
   relations stay separate.
2. **Only the part names its parent.** The parent's files never list its parts; they are found by asking which cases
   name it. One writer per case (ADR-013) stays true: adding or moving a part never writes the parent.
3. **One step sets it:** `part_of` (`to`: a reference, or empty to detach), journaled, a thread entry in the part and
   none written into the parent. Moving a part to another parent is the same step. A circle is refused, as are a
   parent that does not exist and one the person may not see.
4. **No levels and no types for the tree.** A part is a case like any other, of the same application or another one.
   There is no "epic", "story" or "task" in the core; an application may give its levels words if it wants. Whether
   something becomes a part or stays a document inside a case is the person's choice.
5. **The parent shows its parts:** each readable part with its title, stage, assignee and whether it is closed, and
   the count of parts closed against all. Parts in data points the viewer cannot read are counted, not shown.
6. **Closing a parent with open parts is allowed by default.** A stage may require it instead: the configuration names
   the condition `parts_closed` on a move or as an item of a gate protocol (ADR-029), and the core evaluates it like a
   required document. Gates, protocols and rules apply at every level, because every level is a case.
7. **Delegation keeps the tree.** When a part is delegated (ADR-032 data points, step `delegate`), the new case in the
   other person's data point becomes the part; the closed one keeps its reference as today.
8. **Releases use this relation.** ADR-030's release case collects its change cases as parts; a release of a larger
   delivery is itself a part of it. ADR-030 is adjusted before it is accepted; it gets no collection of its own.
9. **The surface:** a card shows the parent it belongs to and, for a parent, its progress (`3/5`). The case view lists
   the parts and offers "add a part" (a new case with `partOf` set) and "make part of …". Facets (ADR-032 era,
   `domain/facets.py`) get the parent as a filter of kind `case`, so a board can show one branch.

## Consequences

- One new meta key, one step, one resolver shared with `waitsFor` (`depends.resolver_for`; after ADR-032 the
  workspace's bindings). Finding the parts of a case uses the store's per-request index (the `MultiStore` index
  of 2026-11-10), so a parent costs one pass over the instance, not one lookup per part.
- Parts across instances are found only in instances the parent's instance is connected to; a part in an unconnected
  instance is not shown, as with dependencies.
- The worklist gets its party; Shipyard gets its release without a type of its own; claims can hold partial claims.

## Alternatives considered

- **A project as an entity of its own.** Rejected: a project is a case with parts; a second kind of thing would need its
  own stages, rights, thread and surface.
- **Several parents (a net).** Rejected: progress and closing conditions become ambiguous. Labels (value lists) and
  dependencies cover the cross-cutting views.
- **The parent lists its parts.** Rejected: two writers for one relation, and a delegated part in another data point
  would have to write into a parent it may not reach.
- **Fixed levels (epic, story, task).** Rejected: the depth belongs to the person and the matter, not to the core.

## Prior art

Parent–child work items (Jira sub-tasks, Azure Boards hierarchy, GitHub sub-issues) store the parent on the child, as
here; we differ in having no levels and in letting a part live in another application instance.
