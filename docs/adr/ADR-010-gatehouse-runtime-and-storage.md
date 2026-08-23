# ADR-010: Gatehouse Runtime and Storage

**Status:** Accepted
**Date:** 2026-08-22

---

## Context

Gatehouse (UC-AG-004) runs on client hardware, not on ChrisBuilds64 infrastructure. That single fact drives the decision: whatever it needs to run, someone has to install it inside a client network, often on Windows, often under an IT department that has to approve every piece of it.

The client sites we expect are small and mid-sized manufacturers and software firms. Docker is common but not universal. Node.js is usually absent and its introduction is a conversation. A database server is a project, not a prerequisite.

The competing pull is developer convenience: a modern frontend framework and a real database would make the build faster and the result prettier.

## Decision

**Python 3.11+ with FastAPI, a single process, files on disk, and no frontend build step.**

Three constraints hold for the lifetime of the product:

1. **No database.** All state lives in files in the instance directory, under the client's version control.
2. **No build tooling at install time.** Prebuilt wheels are fine; anything that needs a compiler, system libraries, or a service on the host is not. This is what rules out database drivers, not the wheel format.
3. **No frontend build.** Server-rendered HTML with plain JavaScript where needed. No bundler, no transpiler, no `node_modules`.

The instance directory layout is part of the contract, not an implementation detail. Version control at the client is a delivery item: either an existing system is used or Git is set up together with the client during the engagement.

## Alternatives

- **Flutter Web** (as used for PressRoom, UC-FE-002): a build toolchain, a large artifact, and a Python server underneath regardless. Two languages for a tool whose selling point is that it installs without a stack.
- **React or similar with a bundler:** same objection, plus a Node.js dependency inside the client network.
- **SQLite or PostgreSQL:** convenient queries, at the cost of a state store that is opaque to the client, not diffable, and not naturally versioned. For a governance product, the audit trail is the product.
- **Hosted SaaS operated by ChrisBuilds64:** removes the installation problem entirely and creates a worse one. Client content would leave the client network by design, which contradicts the premise we are selling.

## Why this combination

- **Files are the audit trail.** A canon is only a canon if its history can be read. A directory of text files under version control gives diffs, blame, and review for free. A database gives none of that without building it.
- **Packaging stays open.** With no database, no compile step, and no frontend build, the same code can later ship as a container or as a single executable. That choice can be deferred until a real client is scheduled. Adding a database now would close it permanently.
- **The stack matches the operator.** One engineer maintains this. FastAPI is already in the repository and in the operator's hands (ADR-007). An unfamiliar stack raises the cost of every future change.
- **The client can leave.** When the engagement ends, the client keeps a directory of readable files. Nothing is locked in a format only Gatehouse can open.

## Consequences

**Benefits:**
- Installation is copying files and starting one process.
- The canon is portable, diffable, and survives the product.
- Packaging decisions stay reversible.

**Trade-offs:**
- The UI will look plain. Accepted: this is an instrument, not a consumer product, and the first version exists to prove the method rather than to impress.
- File storage gives no queries. If reporting across many runs is needed later, it has to be built or a read-only index added alongside the files, never in place of them.
- Concurrent writes are unsafe. Single-user operation is a scope boundary (UC-AG-004), not an oversight. Multi-user requires revisiting this decision.
- Python must be present or bundled. This is the one remaining installation dependency and it is what packaging will have to solve.
