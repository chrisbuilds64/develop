# ADR-020: Agents Belong to the Person, Templates to the Organisation

**Status:** Accepted (Chris, 2026-10-25) · supersedes ADR-019 points 1, 2 and 4 (agents and sessions as workspace components)
**Date:** 2026-10-25

---

## Context

ADR-019 hung agents and sessions on the workspace. Working with it on ENTW, Chris cut the levels along an office:
the person is the boss, the workspace is their desk with its filing cabinets and drives, the application is the
business system they work a case in, and the agents are their team — available wherever they are, not screwed to
one desk. Concept: `control/planning/2026-10-25_zielbild-benutzer-workspace-anwendung-agenten.md`.

## Decision

1. **Organisation, account, agent.** The organisation keeps *templates* — the job profile: signature, default
   rights, engine and model (today the folders under `control/shared-context/agents/` with an `agent.json`). A person
   *hires* agents from templates into their account; the hired agent has its own memory (working notes) and sessions.
   Two people's Atlas share the role, not what each learns about their boss.
2. **Authority is delegated.** An agent acts on its person's behalf and never beyond them: what a session may do is
   the intersection of what the person may do there, what the agent's profile allows, and what the skill allows.
   A hired agent can be narrower than its template, never wider. Billing stays with the person.
3. **Sessions belong to person and agent, and carry their place** (workspace, application, item) instead of living
   in a workspace. Per account and stage.
4. **The log goes to the person's own folder**, a sink they configure (`logs_dir` on the account, `{stage}` allowed);
   the default is in the account. Chris' ENTW logs go to the notes worktree (`context/session-logs/cockpit/`) and so
   travel with his agents' memory on the notes branch to `control` — the keyboard sees them after the merge.
5. **One side panel, everywhere.** The shell offers the person's agents on every page, including inside the mounted
   applications; the panel passes the current place to the session.

## Consequences

- `agents` and `sessions` leave the workspace components; `pipeline` stays until the workspace becomes a list of
  sources and sinks that applications bind to (next step, with casefile).
- Memory location is part of the hired agent (`memory`, `{stage}` allowed), so Chris' agents keep learning on the
  notes branch while another person's agent learns in their account.
- Words: *organisation* for the firm, *account* (Konto) for the person.
