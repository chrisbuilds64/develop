# Project Brief: Oracle World (services/oracle)

**Status:** Accepted
**Date:** 2026-07-19 (reconstructed)
**Owner:** Christian
**Provenance:** Reconstruction. The Oracle world was built in the archived `sdlc` repo (spring 2026) without a brief; extracted into this repo 2026-07-19. This brief reconstructs the problem definition from the existing implementation.

---

## Business problem

The backend world (PostgreSQL, FastAPI) demonstrates the modern stack, but workshops, conference sessions, and enterprise-facing content need the enterprise database counterpart: a realistic Oracle environment showing that lifecycle discipline (versioned migrations, releases, repeatable objects) applies to the database layer, not just application code. Without it, the teaching claim "production discipline is stack-independent" has no Oracle-side evidence.

The underlying need is teachable proof, not a production database: a complete, resettable order-management world (tables, seed data, PL/SQL packages for orders, invoicing, inventory) that participants and demos can run against.

## Acceptance criterion (testable)

From a clean machine with Docker and repo access, following `SETUP.md` alone: Oracle 23ai Free container up, Liquibase deploy applied, and the order-management test schema queryable with seeded data plus working PL/SQL packages. No undocumented manual steps.

## Unvalidated assumption (riskiest)

That workshop participants can clear Oracle's own hurdles unaided: container-registry login, auth token creation, and license acceptance are per-user, Oracle-side steps outside our repo's control. If this assumption fails in a live setting, the fallback (pre-pulled images or a hosted instance) must exist before the first participant-run session.
