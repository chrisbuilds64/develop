# chrisbuilds64/develop

The development system of ChrisBuilds64 — built and run like the IT department of a company, in public.

This repository is not a single application. It is one real development system: services, infrastructure, apps, and the process documents that govern how they are built. The governing principles come from a canon-based operating model (governance before capability, explicit architecture decisions, human gates); this repo is where that model meets running code.

## Structure

```
develop/
├── docs/
│   ├── adr/              # Architecture Decision Records (one home for all)
│   ├── requirements/     # REQ-000.. with lifecycle Draft → Approved
│   ├── runbooks/         # Server setup + troubleshooting
│   └── architecture/     # Design docs
├── infra/
│   └── ansible/          # Server provisioning, hardening, deploy (Caddy)
├── services/
│   ├── backend/          # FastAPI service monolith (PostgreSQL, Alembic)
│   └── oracle/           # Oracle 26ai Free: Dev/Test/Prod PDBs, Liquibase
├── apps/                 # Example applications (Flutter, web)
│   ├── pressroom/        # Editorial pipeline desktop app
│   ├── feldorakel/       # Small FastAPI + LLM web example
│   └── tweight/          # Mobile example (real device deploy)
├── experiments/          # LangGraph multi-agent, agent specs
└── shared/               # Shared components (as needed)
```

**Environment rule:** every area runs the same three-instance structure — Development, Test, Production — via configuration (backend ENV, Oracle PDBs, Ansible inventories). See `docs/adr/`.

## Backend (services/backend)

**Stack:** Python 3.11 + FastAPI + PostgreSQL + Docker

- **Item Manager Module** - Generic CRUD with JSONB payload, tags, soft-delete
- **Search & Filter** - Full-text search (`?search=`) + tag filtering (`?tags=`)
- **Authentication** - Bearer token auth with MockAuth adapter (Clerk-ready)
- **Ownership** - Items scoped to authenticated user
- **Clean Architecture** - API → Modules → Adapters → Infrastructure
- **Logging** - structlog with JSON output
- **Error Handling** - RFC 7807 Problem Details standard

### Quick Start

```bash
git clone https://github.com/chrisbuilds64/develop.git
cd develop

docker-compose up -d

# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### API Endpoints

**Authentication:** All endpoints require `Authorization: Bearer <token>` header.

> **⚠️ Auth is a mock.** MockAuth is a development adapter: static tokens, no real identity verification, no security. It exists so the ownership model is Clerk-ready (v2). Any deployment running MockAuth must be treated as unprotected — do not put sensitive data behind it.

**Test tokens (MockAuth):**
- `test-chris` → user chris
- `test-lars` → user lars
- `test-lily` → user lily

```
POST   /api/v1/items              # Create item
GET    /api/v1/items              # List items
GET    /api/v1/items?search=foo   # Full-text search
GET    /api/v1/items?tags=a,b     # Filter by tags
GET    /api/v1/items/{id}         # Get item
PUT    /api/v1/items/{id}         # Update item
DELETE /api/v1/items/{id}         # Soft-delete item
```

## Building in Public

This is part of the [chrisbuilds64](https://github.com/chrisbuilds64) journey.

Follow along:
- [Substack](https://chrisbuilds64.substack.com)
- [LinkedIn](https://linkedin.com/in/chrisbuilds64)
- [TikTok](https://tiktok.com/@chrisbuilds64)

## License

MIT — see [LICENSE](LICENSE).
