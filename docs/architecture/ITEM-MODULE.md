# Item Module Architecture

**Version:** 1.1
**Status:** Approved
**Date:** January 12, 2026 (translated to English 2026-07-19, content unchanged)

---

## 1. Vision

Abstract base for all data-holding applications. An "Item" represents any form of structured information.

**Goal:** A generic system that maps specialized managers (YouTube links, address book, task lists) with minimal extensions.

---

## 2. Core Model

### Item

```
Item
├── id: UUID
├── owner_id: string              # Owner (user ID)
├── label: string                 # Display name for lists
├── content_type: string          # "text/plain", "media/youtube", "app/address"
├── payload: JSONB                # Type-specific data
├── tags: string[]                # Simple tag list
├── created_at: timestamp
├── updated_at: timestamp
└── deleted_at: timestamp         # Soft delete
```

Note: the design targeted JSONB; the current migration implements generic `sa.JSON()` columns. See `docs/adr/ADR-009-postgresql-generic-item-model.md`.

### Payload Examples

**YouTube link:**
```json
{
  "url": "https://youtube.com/watch?v=xxx",
  "video_id": "xxx",
  "title": "Workout Video",
  "thumbnail_url": "https://..."
}
```

**Address:**
```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "email": "max@example.com",
  "photo_base64": "..."
}
```

---

## 3. Design Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Payload | Hybrid: core fields normalized, rest in JSON | Query performance on core, flexibility for type data |
| Tags | Simple string array | KISS, hierarchy later if needed |
| Soft delete | Yes, via deleted_at | Recovery option, audit trail |
| Multi-tenancy | owner_id per item | User isolation, sharing later |

---

## 4. API (Phase 1)

```
POST   /items                    # Create
GET    /items                    # List (filter: tags, content_type)
GET    /items/{id}               # Get
PUT    /items/{id}               # Update
DELETE /items/{id}               # Soft delete
```

---

## 5. Roadmap (Design for Extension)

### Prepared but NOT built:

| Feature | Extension Point | When |
|---------|-----------------|------|
| **Relations** | `item_relations` table, relation_type enum | When hierarchical structures are needed |
| **Assignments** | `item_assignments` table | When task management is needed |
| **Config module** | Layout hints, type registry | When the frontend needs dynamic layouts |
| **Hierarchical tags** | Tag table with parent_id | When simple tags no longer suffice |
| **Team sharing** | Workspace/team concept | When multi-user collaboration is needed |

### Relations (planned)
```
ItemRelation
├── source_id → target_id
├── relation_type: "parent" | "link" | "reference"
└── position: integer (ordering)
```

### Assignments (planned)
```
ItemAssignment
├── item_id, assignee_id
├── due_date, reminder_at
└── status: "pending" | "completed"
```

### Config module (planned)
- Type registry: schema per content_type
- Layout hints: frontend rendering per type
- Validation: payload validation per type

### Offline sync (planned, mobile)
```
Mobile App Architecture:
├── UI Layer
├── Local Repository (SQLite/Hive)
│   └── Sync Queue (pending changes)
├── Sync Service
│   ├── Conflict Resolution
│   └── Background Sync
└── API Client → Backend

Sync strategy:
- Store items locally (device SQLite)
- Queue changes while offline
- Auto-sync on connection
- Conflict resolution via updated_at (last write wins)
- Optional: merge for complex cases
```

**Important:** Mobile apps must work offline. Sync is not a nice-to-have.

---

## 6. Implementation Phase 1

**Scope:**
- Item CRUD with payload
- Simple tags (string array)
- Filter by tags, content_type
- Soft delete

**Not in Phase 1:**
- Relations
- Assignments
- Config module
- Hierarchical tags

---

**Status:** Phase 1 implemented (2026-01-12)
