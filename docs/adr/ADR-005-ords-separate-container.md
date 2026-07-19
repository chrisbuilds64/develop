# ADR-005: ORDS as a Separate Container

**Status:** Accepted
**Date:** 2026-04-22
**Provenance:** Migrated from archived `chrisbuilds64/sdlc` (there ADR-004), 2026-07-19.

---

## Context

Oracle REST Data Services (ORDS) provides two functions in this stack: it serves APEX applications (the APEX static file server and the PL/SQL Gateway) and it can expose REST endpoints defined directly in the database via REST-enabled SQL. 

ORDS could run embedded inside the Oracle container or as a standalone container. Additionally, ADR-002 establishes that the Python API is the only application-level database interface. ORDS appears to contradict this principle.

## Decision

ORDS runs as its own dedicated container, independent of the Oracle container.

ORDS is treated as an infrastructure-level component, not an application-level consumer. It is the delivery mechanism for APEX applications and for Oracle-native REST endpoints. This is a deliberate, bounded exception to ADR-002, acknowledged and documented here.

Application code (the Python API and all clients) does not route through ORDS for general data access. ORDS handles only APEX serving and Oracle-native REST patterns.

## Consequences

**Benefits:**
- ORDS can be restarted, updated, or scaled independently of the Oracle database.
- APEX applications are served without coupling the database container to HTTP concerns.
- The separation makes the ORDS configuration visible and version-controlled in `services/ords/`.
- Oracle-native REST endpoints (useful for APEX integration patterns) remain available without compromising the API-only principle for application code.

**Trade-offs:**
- One additional container to manage and monitor.
- The exception to ADR-002 requires discipline to keep bounded. Over time, there is a risk of routing general application logic through ORDS rather than the Python API. This must be actively prevented in code review.

The exception is acceptable because ORDS serves a fundamentally different purpose from application-level data access. Its role is infrastructure, not application logic.
