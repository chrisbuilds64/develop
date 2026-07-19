# Database Integration

PostgreSQL + SQLAlchemy integration for ChrisBuilds64 backend.

## Architecture

```
API Layer (FastAPI)
    ↓ (Depends)
ItemRepository
    ↓ (uses)
DatabaseAdapter Interface
    ↓ (implements)
PostgreSQLAdapter (SQLAlchemy)
    ↓ (uses)
SQLAlchemy ORM Models
    ↓
PostgreSQL Database
```

## Key Components

### 1. Database Adapter Interface
**File:** `adapters/database/base.py`

Abstract interface for all database operations:
- `save()`, `find_by_id()`, `find_all()`, `update()`, `delete()`, `find_by()`
- Generic type support: `DatabaseAdapter[T]`
- Implementation-agnostic

### 2. PostgreSQL Adapter
**File:** `adapters/database/postgresql.py`

SQLAlchemy-based implementation:
- Converts between domain models (Item) and ORM models (ItemModel)
- Handles session management
- Implements all DatabaseAdapter methods

### 3. ORM Models
**File:** `adapters/database/models.py`

SQLAlchemy models for database tables:
- `ItemModel` - Maps to `items` table
- Separate from domain models (`modules/item_manager/models.py`)

### 4. Migrations
**Tool:** Alembic
**Config:** `alembic.ini`
**Migrations:** `migrations/versions/`

Schema versioning and migrations.

## Setup

### 1. Install Dependencies
```bash
cd develop/backend
pip install -r requirements.txt
```

### 2. Configure Database
Set `DATABASE_URL` in environment or `.env`:

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/chrisbuilds64

# SQLite (development)
DATABASE_URL=sqlite:///./dev.db
```

### 3. Run Migrations
```bash
cd develop/backend
alembic upgrade head
```

### 4. Start API
```bash
cd develop/backend
uvicorn api.main:app --reload
```

## Switching Implementations

The architecture allows easy switching between database implementations:

### Use PostgreSQL (Production)
```python
# In api/dependencies.py
from adapters.database.postgresql import PostgreSQLAdapter
return PostgreSQLAdapter(db)
```

### Use Mock (Testing)
```python
# In api/dependencies.py
from adapters.database.mock import MockDatabaseAdapter
return MockDatabaseAdapter()
```

### Add New Implementation (e.g., MongoDB)
1. Create `adapters/database/mongodb.py`
2. Implement `DatabaseAdapter` interface
3. Update `api/dependencies.py` to inject it

**No changes needed to:**
- ItemRepository
- Domain models
- API routes
- Business logic

## Files Changed

**New Files:**
- `requirements.txt` - Python dependencies
- `infrastructure/database_sqlalchemy.py` - SQLAlchemy setup
- `adapters/database/models.py` - ORM models
- `adapters/database/postgresql.py` - PostgreSQL adapter
- `alembic.ini` - Alembic config
- `migrations/env.py` - Migration environment
- `migrations/versions/2026_01_13_1400-001_create_items_table.py` - Initial migration

**Updated Files:**
- `modules/item_manager/repository.py` - Uses DatabaseAdapter
- `api/dependencies.py` - Dependency injection
- `api/routes/items.py` - Injects ItemRepository
- `adapters/database/__init__.py` - Export all adapters

## Principles Applied

**Backend Excellence (Core Principle #1):**
- Clean interface abstraction (DatabaseAdapter)
- Implementation agnostic (PostgreSQL, Mock, future: MongoDB)
- Proper dependency injection
- Migrations for schema management

**Separation of Concerns:**
- Domain models (`modules/*/models.py`) - Business logic
- ORM models (`adapters/database/models.py`) - Database schema
- Adapter layer converts between them

**Extension Points:**
- Add new database: Implement DatabaseAdapter
- Add new entity: Create adapter + migration
- Switch implementation: Update dependencies only
