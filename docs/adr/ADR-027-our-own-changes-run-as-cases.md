# ADR-027: Our Own Software Changes Run as Cases

**Status:** Accepted (2026-11-09, product owner). Decision E5 of 2026-11-08.
**Date:** 2026-11-08

---

## Context

casefile carries claims, assessments and content: a case moves through stages, people hold the gates, agents do
the drafting, every move is recorded. Our own software did not run that way. Changes went through pull requests and
checks (CONTRIBUTING.md), but the way of a change — task, build, checks, approval, release, ENTW, TEST, PROD — was a
convention in a document, not a record anyone could open.

A software house that sells this mechanism has to show it works for its own work. And most of our code is written by
an agent, so the place where a person approves the agent's work has to be explicit (software principles 2 and 6).

## Decision

1. **A software change is a case** in its own application, **Shipyard** (`shipyard`), configured like any other domain
   (ADR-015). No new core code.
2. **The stages are the way of a change in CONTRIBUTING.md**, one stage per step, each leaving only with its record:
   task (`task.md`), pull request (`pr.md`), checks (`checks.md`), release (`release.md`), TEST (`test.md`),
   PROD (`prod.md`). The case claims nothing it does not link.
3. **The product owner holds every gate:** confirms the task, merges, accepts ENTW and TEST. The merge is four eyes:
   whoever wrote the pull request record cannot merge it.
4. **A developer may be a person or an agent.** The agent's moves are recorded under its own name, never under the
   person who approves them.
5. **The live workspace is on production, in its own folder** (`shipyard`), apart from PressRoom's content. It holds our real
   changes from 2026-11-08 on; nothing in it is prepared.
6. **Records are written by hand for now.** The developer records the pull request, the check run and each deploy as
   a file in the case. A webhook from the code host comes later and changes who writes the record, not the way.

## Consequences

- The cleanup of November 2026 (requirements, splitting the API, the runner as its own application) is the first set
  of cases. It shows the mechanism on our own work, with real dates.
- The product owner's time per change is the gates: confirming the task, the merge, two acceptances.
- An agent writing into the live workspace does so through the core (steps), like every other writer. Two cores
  writing one synced folder rely on turns alternating; the case lock does not reach across the sync.
- The configuration is public in this repository; the workspace's content is not.

## Alternatives considered

- **A prepared sample world** like the change file for database changes. Rejected: it would show the mechanism, not
  that we use it.
- **Inside the content workspace.** Rejected: mixes content and software in one tree, one set of people, one backup.
