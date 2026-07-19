# ADR-002: Monorepo Structure

**Status:** Accepted
**Date:** 2026-04-22
**Provenance:** Migrated from archived `chrisbuilds64/sdlc` (there ADR-001), 2026-07-19.

---

## Context

This project covers multiple distinct layers: server provisioning, database schema and migrations, a REST API, an ORDS configuration, APEX application exports, and client applications. These layers have different deployment cadences and different toolchains.

The question is whether to manage them as separate repositories or as a single monorepo.

## Decision

We use a monorepo with a clear top-level directory structure separating `infra/`, `services/`, `apps/`, and `shared/`.

## Consequences

**Benefits:**
- A single clone gives a complete picture of the system. No context switching between repos.
- Cross-cutting changes (e.g., updating an API contract that affects both the Python API and a client app) happen in one commit.
- The `shared/openapi.yaml` API contract is directly accessible to all consumers without a separate package registry.
- CI/CD pipelines can trigger selectively based on changed paths.

**Trade-offs:**
- Larger repository as the project grows.
- Contributors need discipline to only modify their relevant layer — enforced by directory conventions and code review.
- Build times increase if path-based CI filtering is not implemented correctly.

This trade-off is acceptable for a reference stack of this scale. The clarity benefit outweighs the complexity cost.
