# ADR-003: API-Only Database Access

**Status:** Accepted
**Date:** 2026-04-22
**Provenance:** Migrated from archived `chrisbuilds64/sdlc` (there ADR-002), 2026-07-19.

---

## Context

The system has multiple potential consumers of the Oracle database: a Python API, ORDS for APEX-specific REST endpoints, future mobile clients, web frontends, and test scripts. The question is whether consumers should connect to Oracle directly or through a defined interface layer.

## Decision

The Python API is the only application-level interface to Oracle. No consumer application connects to the database directly. The only exception is ORDS, which is an infrastructure-level component serving APEX and REST endpoints — this exception is explicit and governed by ADR-004.

## Consequences

**Benefits:**
- Every database operation is traceable through the API layer. Auditing is straightforward.
- Schema changes can be made without hunting for all consumers that might be affected. There is exactly one place to update.
- The API layer enforces consistent authentication, authorization, and validation. No consumer can bypass these by going to the database directly.
- Testing is simplified: mock the API, not the database.

**Trade-offs:**
- Additional network hop for all database operations through the API.
- The Python API becomes a critical path. Its availability directly affects all consumers.
- Some simple queries require an API endpoint where a direct query would be faster to implement.

These trade-offs are accepted. The maintainability and auditability gains over the lifetime of the system outweigh the initial convenience cost of direct access.
