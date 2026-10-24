# ADR-019: Agents and Sessions Belong to the Workspace

**Status:** Accepted as proof of concept (Chris, 2026-10-24); the rights matrix follows in an architecture review
**Date:** 2026-10-24

---

## Context

After ADR-018 the account carried identity and billing, and the plan was to hang agent signatures on the
account too. Chris, 24.10.: a workspace should say where its agents and its session logs live — its own
directories or shared ones — so that one can open a conversation with an agent from the cockpit, define
task-specific agents with their own skills and rights, and start and end a session with a button.

## Decision

1. **A workspace has components.** `pipeline`, `agents`, `sessions` — each a path, own or `shared`, and
   `writable: false` where the server reads but does not commit (a git checkout). `root`/`write_root` remain
   the pipeline's spelling. A registry-level `defaults` gives every workspace of a stage the same `agents`.
   `sessions` defaults to `<registry dir>/sessions/<id>/`, server-local, never in a synced team folder.
2. **An agent is a folder with `agent.json`.** Identity (signature), memory (working notes), the skills it may
   run, its tool ceiling, web, extra writable paths, and who may choose it. A folder without `agent.json` is no
   agent — the same directory holds humans' signatures and instances that run elsewhere.
3. **Rights are an intersection.** A run gets what run-policy.json grants the skill and what the agent allows.
   A conversation gets the agent's ceiling.
4. **A session is one agent, one workspace, one person, one topic.** A change of agent is a new session.
   Parallel sessions are normal; the same key twice is a warning. One message at a time, because the
   conversation is a chain of `--resume`.
5. **The runner executes sessions.** Messages and the closing turn are orders in the session store's queue;
   the runner bills them to the person, gives the session a HOME that lasts until its end (Claude Code keeps
   the transcript there), and builds the context from the agent's own folder plus the shared manifest. The
   closing turn writes the log; the lease is released; the agent's next session starts from that log.

## Consequences

- The account shrinks to identity and billing; SYS-70 changes accordingly.
- An agent in a shared `agents` directory carries what it learns into every workspace that points there;
  an own directory keeps it local. Configuration decides, not code.
- Logs of cockpit sessions live in the workspace's store, not in `control/context/session-logs/`, until the
  server can commit to `control`.
- Skill orders do not yet name an agent; that needs a field in each pipeline's run.schema.json.
- Atlas runs on GPT. An Atlas in the cockpit would be Claude with Atlas' signature; `engine` keeps the place
  for another engine, and Atlas is not offered until that is decided.
