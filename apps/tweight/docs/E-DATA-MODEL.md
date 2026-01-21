# tweight Data Model

## Overview

tweight uses a simple, flexible data model centered around the **Item** entity. Items can represent notes, tasks, links, or any other content type.

---

## Entity: Item

### Schema

```
┌─────────────────────────────────────────────┐
│                   Item                      │
├─────────────────────────────────────────────┤
│ id          UUID        PRIMARY KEY         │
│ label       VARCHAR     NOT NULL            │
│ content_type VARCHAR    NOT NULL            │
│ tags        TEXT[]      DEFAULT []          │
│ payload     JSONB       DEFAULT {}          │
│ owner_id    UUID        NOT NULL (FK→User)  │
│ created_at  TIMESTAMP   NOT NULL            │
│ updated_at  TIMESTAMP   NOT NULL            │
└─────────────────────────────────────────────┘
```

### Field Descriptions

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | Primary Key, Auto-generated | Unique identifier |
| label | string | Required, Max 1000 chars | Main text/title of the item |
| content_type | string | Required | Category: note, task, link, other |
| tags | string[] | Optional, Default [] | List of lowercase tags |
| payload | JSON | Optional, Default {} | Flexible additional data |
| owner_id | UUID | Required, Foreign Key | Reference to user/owner |
| created_at | datetime | Auto-set on create | Creation timestamp (UTC) |
| updated_at | datetime | Auto-set on update | Last modification (UTC) |

---

## Tags

Tags are simple strings with the following conventions:

### Rules
- **Lowercase**: All tags are normalized to lowercase
- **Trimmed**: Leading/trailing whitespace removed
- **No duplicates**: Each tag appears once per item
- **Array storage**: Stored as PostgreSQL TEXT[] or JSON array

### Reserved Tags

| Tag | Meaning |
|-----|---------|
| inbox | Items captured via Quick Capture, awaiting processing |

### Query Behavior
- Filter by single tag: Items containing that tag
- Filter by multiple tags: Items containing ALL specified tags (AND logic)
- Tags are matched exactly (case-insensitive due to normalization)

---

## Content Types

Predefined categories for items:

| Type | Description | Use Case |
|------|-------------|----------|
| note | General text | Thoughts, ideas, notes |
| task | Actionable item | To-dos, reminders |
| link | URL/reference | Bookmarks, resources |
| other | Catch-all | Anything else |

Content type is informational - no special behavior attached.

---

## Payload

The payload field stores arbitrary JSON data for extensibility.

### Current Usage
Not actively used by the Flutter app (default: `{}`).

### Future Use Cases
- Link items: `{"url": "https://...", "title": "..."}`
- Task items: `{"due_date": "2026-02-01", "priority": "high"}`
- Note items: `{"body": "Extended content..."}`

### Constraints
- Must be valid JSON object
- Maximum size: ~1MB (practical limit)
- Queryable via PostgreSQL JSONB operators

---

## Ownership

### Multi-Tenancy
- Each item belongs to exactly one owner (owner_id)
- Users can only see/modify their own items
- owner_id is set automatically from auth token

### Authorization
- Token identifies user
- All queries filtered by owner_id
- No cross-user access possible

---

## Indexes

Recommended indexes for performance:

```sql
-- Primary key (auto)
CREATE INDEX idx_items_pkey ON items(id);

-- Owner lookup (most common)
CREATE INDEX idx_items_owner ON items(owner_id);

-- Tag filtering
CREATE INDEX idx_items_tags ON items USING GIN(tags);

-- Label search
CREATE INDEX idx_items_label_trgm ON items USING GIN(label gin_trgm_ops);

-- Combined owner + created (list view)
CREATE INDEX idx_items_owner_created ON items(owner_id, created_at DESC);
```

---

## Timestamps

### Behavior
- `created_at`: Set once on INSERT, never modified
- `updated_at`: Updated on every UPDATE

### Format
- Stored as UTC
- Returned as ISO 8601: `2026-01-21T18:30:00Z`
- Client should handle timezone conversion

---

## Database: PostgreSQL

### Table Definition

```sql
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label VARCHAR(1000) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    tags TEXT[] DEFAULT '{}',
    payload JSONB DEFAULT '{}',
    owner_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

---

## Flutter Model

```dart
class Item {
  final String id;
  final String label;
  final String contentType;
  final Map<String, dynamic> payload;
  final List<String> tags;
  final String ownerId;
  final DateTime createdAt;
  final DateTime updatedAt;

  Item({
    required this.id,
    required this.label,
    required this.contentType,
    required this.payload,
    required this.tags,
    required this.ownerId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Item.fromJson(Map<String, dynamic> json) {
    return Item(
      id: json['id'],
      label: json['label'],
      contentType: json['content_type'],
      payload: json['payload'] ?? {},
      tags: List<String>.from(json['tags'] ?? []),
      ownerId: json['owner_id'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'label': label,
      'content_type': contentType,
      'payload': payload,
      'tags': tags,
      'owner_id': ownerId,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
```

---

## Migration Path

### Adding Fields
1. Add column with DEFAULT value
2. Update backend model
3. Update Flutter model
4. Deploy backend first, then app

### Removing Fields
1. Stop using field in app
2. Deploy app
3. Remove from backend
4. Drop column (optional, can keep for history)
