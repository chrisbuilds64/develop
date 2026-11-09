# ADR-031: The Worklist — casefile's Simplest Application

**Status:** Accepted (2026-11-09, product owner). Requirements: REQ-005. Built on the workspace model of ADR-032, as its
first application.
**Date:** 2026-11-09

---

## Context

Our open items live in `control/context/todo.json`: a schema, value lists, a single writer (`todo.py`), skills on top.
It works, but only where `control` is checked out. Every new environment — the server's runner, a Cowork session, a
phone, a second person — needs a copy or a way of its own to the file. Akhil cannot work in it at all (SYS-123).

Looked at from above, an open item is a case: something to be done that passes through stages, is somebody's move, has
a due date and an origin, and may carry documents. Cluster, priority and people are value lists. casefile already
carries all of this (ADR-013, ADR-015). The worklist is therefore not a new tool but the most abstract application
casefile can have: cases without a domain vocabulary, without required documents, with open gates.

That makes it useful a second time. We keep failing to explain casefile in a sentence; every existing application
(claims, assessments, PressRoom, Shipyard) brings a domain that hides the principle. The worklist has none.

Two requirements come from the product owner (2026-11-09):

- **My items are mine.** On the server a person sees their own items only, and may hand one on or share it.
- **One source, every environment.** The list is reached from every environment through one interface; tools such as
  the Context Loop become consumers of it instead of carrying their own copy.

## Decision

1. **The worklist is a casefile application** (`config/worklist/`), configuration only (ADR-015). Stages are the
   statuses of today's list: Backlog, Next, Doing, Waiting, Done. Every member who may write an item may move it; there
   are no required documents, and any file may be added to an item.
2. **Privacy is a data point** (ADR-032). Every person has a private data point — a team folder only they can open. A
   team has a shared one. The worklist instance binds its slot "items" to the private data points of its members and to
   the shared one; each person sees what the store lets them read. Hiding in the surface is never the protection.
3. **Handing on moves an item between data points.** *Delegate* creates it in the other person's private data point,
   with origin and a link, and closes it in mine with a reference. *Share* moves it into the shared data point; its id
   stays. The surface shows "mine" and "shared with me" in one list.
4. **An item knows who created it and whose move it is.** Creator and assignee are separate fields. An item an agent
   records for a person lies in that person's data point, with the agent as creator; the assignee may be the agent or
   the person.
5. **Dependencies between cases are a core concept**, not a field of this application, and they are built here first:
   a case may wait for other cases, also in other application instances; it shows what it waits for and is released when
   they close. Release bundles (ADR-030) use the same mechanism afterwards.
6. **One interface for every environment.** The core's API is reachable from outside the server with a personal token.
   A person issues their own tokens on the account page; a token names the instances it may use and whether it may
   write. `todo.py` keeps its commands and becomes a thin client of that API (ADR-013), so the skills keep working.
7. **One hard cut-over.** The items move once, with their ids — cluster prefix and number, `SYS-147` stays `SYS-147` —
   so session logs and decisions keep pointing right. Afterwards `todo.json` is archived read-only; there is never a
   second source.
8. **The worklist is the entry to casefile.** Its demo world and a one-page explanation map each casefile concept onto
   an item: case, stage, whose move, value list, document, gate, hand-off, dependency, data point. Every other
   application is then "the worklist plus a domain's words, required documents and gates". In one sentence: *casefile
   is a worklist whose items carry documents and are checked at gates.*

## Consequences

- Akhil gets a private data point and shares one with Chris; SYS-123 is answered by this.
- The Context Loop is not part of this decision (its session handling is looked at separately). It gains a fixed
  anchor: one address for open items, whatever the environment.
- Remote access widens the attack surface of the core: tokens need scopes, expiry and revocation, and every write
  through them is journaled with the token's owner.
- The worklist is the first application on the ADR-032 model, so it carries the first slot bindings, the first instance
  over several data points and the first data-point rights. Whatever does not hold shows here first, on a small case.
- Until the cut-over, `todo.json` stays the only source; nothing is written into both.

## Alternatives considered

- **One shared list, filtered by assignee.** Rejected: the files stay readable in the team folder and to agents — a
  view, not privacy.
- **A personal workspace per person** (the first draft of this record). Superseded by ADR-032: privacy belongs to the
  data point, and a workspace holds several people and applications.
- **Keep `todo.json` and add a board on top** (CL-26). Keeps the list bound to one checkout.
- **GitHub Issues or a Nextcloud board** (SYS-123). A second source beside ours, outside the canon and the journal.
