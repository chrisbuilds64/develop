# ADR-007: Backend as Modular Monolith

**Status:** Accepted
**Date:** 2026-07-19 (reconstructed)
**Provenance:** Reconstruction. The decision was made implicitly in early 2026 when the backend was built; it was never recorded. This document reconstructs it from code evidence (`services/backend/api/main.py`, `modules/`, `adapters/`) during the 2026-07-19 repo consolidation.

---

## Context

The backend serves multiple concerns: item management, auth, static frontend apps, and planned modules (ki_prompter, workflow_manager). The structural question: one deployable service or one service per concern?

Operating reality: one engineer, one production host, one PostgreSQL instance.

## Decision

One FastAPI application as a modular monolith:

- **One deployable** (`prod-backend` container) serving the API and mounting the frontend apps as static files.
- **Internal module boundaries** under `modules/` (item_manager, authenticator, ki_prompter, workflow_manager) — each with its own models, service, repository.
- **Ports and adapters** under `adapters/` (database, auth): modules depend on abstract interfaces, wiring happens in `api/dependencies.py`.

## Alternatives

- **Service per module (microservices):** independent scaling and deployment, at the cost of network boundaries, per-service pipelines, and distributed debugging.
- **Unstructured monolith:** everything in one flat app package — fastest to start, no extraction path later.

## Why the modular monolith

- At single-operator, single-host scale, microservices add operational surface (N containers, N pipelines, inter-service auth) with no payoff — there is nothing to scale independently.
- The module + adapter structure preserves the extraction path: a module that outgrows the monolith can be lifted out along its existing interface without redesign.
- One process simplifies the deploy story: one image, one compose service, one health endpoint behind Caddy (see ADR-006).

## Consequences

**Benefits:**
- One build, one deploy, one log stream. Operational overhead matches team size.
- Module boundaries are enforced by convention and dependency injection, reviewable in one repo.

**Trade-offs:**
- Boundaries by convention can erode silently — nothing technically prevents a cross-module import. Code review is the guard.
- A failure in one module can take down the whole process.
- Scaling is all-or-nothing until a module is extracted.
