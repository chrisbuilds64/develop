# ADR-031: The Worklist — casefile's Simplest Application

**Status:** Proposed (2026-11-09), waiting for the product owner. Requirements: REQ-005.
**Date:** 2026-11-09

---

## Context

Our open items live in `control/context/todo.json`: a schema, value lists, a single writer (`todo.py`), skills on top.
It works, but only where `control` is checked out. Every new environment — the server's runner, a Cowork session, a
phone, a second person — needs a copy or a way of its own to the file. Akhil cannot work in it at all (SYS-123).

Looked at from above, an open item is a case: something to be done that passes through stages, is somebody's move, has
a due date and an origin, and may carry documents. Cluster, priority and people are value lists. casefile already
carries all of this (ADR-013, ADR-015, ADR-018). The worklist is therefore not a new tool but the most abstract
application casefile can have: cases without a domain vocabulary, without required documents, with open gates.

That makes it useful a second time. We keep failing to explain casefile in a sentence; every existing application
(claims, assessments, PressRoom, Shipyard) brings a domain that hides the principle. The worklist has none.

Two requirements come from the product owner (2026-11-09):

- **My items are mine.** On the server a person sees their own items only, and may hand one on or share it.
- **One source, every environment.** The list is reached from every environment through one interface; tools such as
  the Context Loop become consumers of it instead of carrying their own copy.

## Decision

1. **The worklist is a casefile application** (`config/worklist/`), configuration only (ADR-015). Stages are the
   statuses of today's list: Backlog, Next, Doing, Waiting, Done. Every member may move an item; there are no
   required documents, and any file may be added to an item.
2. **Privacy is a workspace, not a filter.** Every person has a personal worklist workspace in a team folder of their
   own, which no one else is a member of. A filter in the surface would hide items while the files stay readable in
   Nextcloud and to every agent of the workspace; it is not protection.
3. **Handing on is the existing hand-off** (ADR-023). *Delegate* creates the item in the other person's worklist and
   closes it in mine with a link. *Share* moves it into a shared worklist (a team's workspace) whose members see it.
   The surface shows a person "mine" and "shared with me" together.
4. **Dependencies between cases are a core concept**, not a field of this application: a case may wait for other
   cases, also in other workspaces; it shows what it waits for and is released when they close. Release bundles
   (ADR-030) need the same thing.
5. **One interface for every environment.** The core's API is reachable from outside the server with a personal token
   per person or agent. `todo.py` keeps its commands and becomes a thin client of that API (ADR-013: command lines are
   thin wrappers), so the skills keep working unchanged.
6. **One hard cut-over.** The items move once, with their ids (`SYS-147` stays `SYS-147`, so session logs and
   decisions keep pointing right). Afterwards `todo.json` is archived read-only; there is never a second source.
7. **The worklist is the entry to casefile.** Its demo world and a one-page explanation map each casefile concept onto
   an item: case, stage, whose move, value list, document, gate, hand-off. Every other application is then "the
   worklist plus a domain's words, required documents and gates".

## Consequences

- Akhil gets a worklist of his own and a shared one with Chris; SYS-123 is answered by this.
- The Context Loop is not part of this decision (its session handling is looked at separately). It gains a fixed
  anchor: one address for open items, whatever the environment.
- Remote access widens the attack surface of the core: tokens need scopes (which workspaces, read or write), expiry
  and revocation, and every write through them is journaled with the token's owner.
- A personal workspace per person is one team folder per person and stage. That is cheap in Nextcloud, but the
  registry grows with the number of people.
- Until the cut-over, `todo.json` stays the only source; nothing is written into both.

## Alternatives considered

- **One shared worklist, filtered by assignee.** Simplest to build; rejected because the files stay visible in the team
  folder and to agents — a view, not privacy.
- **Keep `todo.json` and add a board on top** (CL-26). Keeps the list bound to one checkout; does not reach the server,
  a second person or a phone.
- **GitHub Issues or a Nextcloud board** (SYS-123). Fast for Akhil, but a second source beside ours, outside the
  canon and the journal, and public in the case of issues on `develop`.
