# chrisbuilds64/develop

Backend for the chrisbuilds64 project. Building in public.

## Status

**Version:** 1.0 (Production-Ready Foundation)
**Stack:** Python 3.11 + FastAPI + PostgreSQL + Docker

## What's Implemented

- **Item Manager Module** - Generic CRUD with JSONB payload, tags, soft-delete
- **Clean Architecture** - API → Modules → Adapters → Infrastructure
- **PostgreSQL Adapter** - With Alembic migrations
- **Logging** - structlog with JSON output
- **Error Handling** - RFC 7807 Problem Details standard
- **Docker Setup** - Multi-stage build, docker-compose

## Quick Start

```bash
# Clone
git clone https://github.com/chrisbuilds64/develop.git
cd develop

# Start with Docker
docker-compose up -d

# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## Project Structure

```
develop/
├── backend/
│   ├── api/              # FastAPI routes + schemas
│   ├── modules/          # Business logic (item_manager)
│   ├── adapters/         # Database, Auth, AI interfaces
│   ├── infrastructure/   # Logging, Errors, Config
│   └── migrations/       # Alembic
├── architecture/         # Design docs
└── docker-compose.yml
```

## API Endpoints

```
POST   /api/v1/items      # Create item
GET    /api/v1/items      # List items (filter: tags, content_type)
GET    /api/v1/items/{id} # Get item
PUT    /api/v1/items/{id} # Update item
DELETE /api/v1/items/{id} # Soft-delete item
```

## Building in Public

This is part of the [chrisbuilds64](https://github.com/chrisbuilds64) journey.

Follow along:
- [Substack](https://chriscodes64.substack.com)
- [LinkedIn](https://linkedin.com/in/chrisbuilds64)
- [TikTok](https://tiktok.com/@chrisbuilds64)

## License

MIT
