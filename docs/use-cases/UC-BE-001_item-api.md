# UC-BE-001: Item API

**Created:** January 2026
**Last Updated:** 2026-04-15
**Status:** DEPLOYED (Phase 6)
**Owner:** Christian
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19. Prior revision history remains in the control repo.

---

## 1. Business Understanding

**Problem:**
Central API for item management (collections, items, metadata) as the backbone for multiple frontends.

**Stakeholders:**
- Chris (developer, user)
- Future frontends (web, mobile, CLI)

**Success criteria:**
- CRUD operations for items functional
- Clean architecture (module-based)
- API documented (OpenAPI)

**Scope:**
- IN: Items, collections, basic auth
- OUT: Media processing, search/RAG (separate use cases)

---

## 2. Data Understanding

**Available data:**
- Items: title, description, metadata (JSON)
- Collections: name, items[], owner

**Data quality:**
- New database, we define the schema
- No legacy migration needed

**Gaps:**
- Media storage strategy still open (S3 vs. local)

---

## 3. Data Preparation

**Schema:**
- [x] Item model defined
- [x] Collection model defined
- [ ] User/auth model

**Pipeline:**
- PostgreSQL as primary store
- Pydantic for validation

---

## 4. Modeling

**Approach:**
FastAPI + SQLAlchemy + PostgreSQL

**Rationale:**
- FastAPI: async, auto-OpenAPI, type hints
- SQLAlchemy: mature ORM, migrations via Alembic
- PostgreSQL: JSONB for flexible metadata

**Alternatives rejected:**
- Django: overkill for API-only
- MongoDB: relational fits better for collections/items

---

## 5. Evaluation

**Metrics:**
- Technical: response < 100ms, test coverage > 80%
- Business: API usable by frontend team

**Acceptance criteria:**
- [ ] All CRUD endpoints working
- [ ] Auth implemented
- [ ] OpenAPI spec complete
- [ ] Docker deployment works

**Test plan:**
- pytest for unit tests
- Manual testing via Swagger UI

---

## 6. Deployment

**Integration:**
Docker Compose (dev), later K8s or Railway

**Rollout:**
Dev → Staging → Production (when frontend ready)

**Monitoring:**
- Health endpoint
- Structured logging
- (Later: Prometheus metrics)

**Rollback:**
Docker image versioning, DB migrations reversible

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Jan 2026 | FastAPI over Django | API-only, lighter weight |
| Jan 2026 | PostgreSQL over MongoDB | Relational structure fits |

See also `docs/adr/ADR-009-postgresql-generic-item-model.md`. Note: the JSONB intent recorded above was implemented as generic `sa.JSON()` columns; the gap is documented in ADR-009.

---

## Status Updates

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| Jan 2026 | Modeling | In Progress | Basic structure done |
| 2026-04-15 | Deployment | DEPLOYED | Running in production |

---

## Related

- Code: `services/backend/`
- Decisions: `docs/adr/`
