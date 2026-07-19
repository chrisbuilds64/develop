# ADR-009: PostgreSQL with a Generic Item Model (JSON Payload)

**Status:** Accepted
**Date:** 2026-07-19 (reconstructed)
**Provenance:** Reconstruction. The data model was decided implicitly with the first migration (2026-01-13); never recorded. Reconstructed from code evidence (`migrations/versions/2026_01_13_1400-001_create_items_table.py`, `modules/item_manager/models.py`) during the 2026-07-19 repo consolidation.

---

## Context

The Item API (UC-BE-001) must store heterogeneous user content — links, media references, app-specific records — without a fixed schema per content type. The questions: which database, and typed tables versus a generic entity?

## Decision

- **PostgreSQL 16** as the one database (SQLAlchemy + Alembic migrations, dedicated instance per environment per ADR-004).
- **One generic `items` table:** every record is an Item with `owner_id`, `label`, a MIME-like `content_type` (e.g. `media/youtube`, `app/address`), a schemaless `payload` JSON column, and a `tags` JSON list.
- **Soft delete** via `deleted_at` timestamp; indexes on `owner_id`, `content_type`, `deleted_at`.

## Alternatives

- **Typed table per content type:** full relational integrity and typed queries, but a schema migration for every new content type — wrong trade-off while content types are still being discovered.
- **Document database (e.g. MongoDB):** natural fit for schemaless payloads, but adds a second infrastructure component and gives up SQL, transactions, and the existing operational knowledge for one flexible column.

## Why this design

- New content types cost zero migrations: clients define a `content_type` and payload shape, the table absorbs it.
- Relational ground where it matters (ownership, timestamps, indexes, transactions) plus schema flexibility where it matters (payload).
- One database technology across all environments keeps the operations surface small.

## Consequences

**Benefits:**
- The Item API is one CRUD surface for all current and future content types.
- Standard PostgreSQL tooling (backups, psql, migrations) covers everything.

**Trade-offs:**
- Payload contents are invisible to the schema: no constraints, no typed columns, validation lives in application code.
- The migration uses generic `sa.JSON()`, which maps to PostgreSQL `JSON` — **not** `JSONB`. No binary storage, no GIN indexing, no efficient containment queries on payload. Acceptable at current data volume; switching to JSONB is a known, low-risk migration candidate if payload queries ever become a requirement.
- Reporting across payloads of one content type requires JSON extraction in queries rather than plain column access.
