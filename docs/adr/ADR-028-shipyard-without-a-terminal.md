# ADR-028: Shipyard Without a Terminal

**Status:** Accepted (2026-11-09, product owner): agent on the server, merge on the code host, deploys only with
the gate.
**Date:** 2026-11-09

---

## Context

ADR-027 made our own software changes cases. Every developer move was still made by hand: when an agent wrote the code,
a person sat at a terminal with it, and the agent pushed, recorded and deployed from there. For a developer who lets
the agent program, the case should be the only place they work: write the task, confirm, merge, accept. Everything in
between is the agent's, ordered from the case and reported back to it.

Two facts of the server shape the answer. The runner has no privileges (`NoNewPrivileges`) and must not get any. And
a deploy restarts the stage's runner — a run that deploys its own stage would end itself.

## Decision

1. **Each gate orders the next stretch.** Confirming the task orders `shipyard-build`; the pull request orders
   `shipyard-checks`; the merge and each acceptance order `shipyard-release`. Red checks send the change back to the
   build with what failed, and stop after the third time. The stages and the gates are those of ADR-027, unchanged.
2. **A helper makes its moves through the core**, with `python -m casefile.cli.step`. The tool acts as the run's agent
   and refuses any person: a gate held by a person can only be passed by that person, in the surface.
3. **The agent has its own identity on the code host** — a GitHub App. It pushes branches and opens pull requests under
   that name, never under the product owner's. It cannot push to `main` (branch protection) and has no right to the CI
   workflows. **The product owner merges on the code host, with their own account**; the case records the same person.
4. **The agent works in a checkout of its own** on the server, never in the deployed code.
5. **A secret reaches only the skill whose policy names it** (`secrets` in `run-policy.json`, files in the runner's
   secrets directory; an executable one mints a token per run). A content run never sees the code host's token.
6. **Deploys are requests.** `shipyard-release` tags the merge commit once and asks for each stage by writing a request
   into a spool. A root service, woken by a path unit, believes nothing the request says about the gate: it reads the
   case in the space's tree and deploys only if the case stands in the stage that `"deploys"` that stage
   (`stages.json`), only a tag whose commit is on `main`, and only to the requesting space's stage or below — a trial
   on ENTW never reaches production. The outcome goes back to the case as an order for `shipyard-verify`, which files
   the record and makes the developer's move; a refused or failed deploy becomes a note for the product owner.
7. **An agent's runs are billed to the person it belongs to** (`bill_to` on the agent's account, ADR-020).

## Consequences

- Between the task and PROD the developer needs the surface and the code host's pull request page, nothing else.
- What reaches PROD has passed two independent hands of the product owner: the merge on the code host and the
  acceptance in the case. The server checks both (tag on `main`, case in the stage).
- **Trust boundary, stated plainly:** helper runs execute as the runner's user, and a run that may run tests may run
  code. A run could therefore write into the trees the runner can write, including moving a case by hand. That cannot
  put unmerged code on a stage (the tag must be on `main`), but it could bring a merged change to the next stage
  before its acceptance. Closing this needs code-writing runs under a user of their own, in a sandbox without the
  content trees and the accounts; it is part of the security package (REQ-001 W-04).
- **Root runs nothing the runner can write.** The deploy service is root and the stages' checkouts belong to the runner,
  so the service runs a root-owned copy of the tool, installed by an administrator; it asks the code host whether a tag
  is on `main` through a bare mirror of its own; and a deploy fetches from the configured repository, not from a
  checkout's remote. Found on installation (2026-11-09), before the service took its first request.
- **A deploy never ends the run that asked for it.** When the request comes from a run on the runner of the very stage
  it deploys, the service waits until that run has ended (at most 20 minutes, and the result says how long). Found in
  the first trial (2026-11-09): the ENTW release run was cut off by its own ENTW deploy.
- The deploy service hard-wires one name of the application, the reporting skill `shipyard-verify`.

## Alternatives considered

- **A sudo rule for the runner.** Not possible under `NoNewPrivileges`, and it would leave the gate check to the agent.
- **The agent pushes under the product owner's token.** Rejected: the pull request would carry the person's name, and
  the four eyes would be a claim.
- **The runner on the product owner's computer.** Faster to set up; rejected because it runs only while that computer
  is on, and the code host's token would live on a personal machine.
