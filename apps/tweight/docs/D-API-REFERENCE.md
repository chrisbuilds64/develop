# tweight API Reference

## Base URL

```
Production: https://api.chrisbuilds64.com
```

## Authentication

All endpoints require Bearer token authentication:

```
Authorization: Bearer <token>
```

Tokens are issued per user. Each token identifies the owner, and items are scoped to the token owner.

---

## Endpoints

### List Items

```
GET /api/v1/items
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| search | string | Case-insensitive substring search on label |
| tags | string | Comma-separated list of tags (AND logic) |
| content_type | string | Filter by exact content type |

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "label": "Example item",
      "content_type": "note",
      "tags": ["inbox", "idea"],
      "payload": {},
      "owner_id": "user-uuid",
      "created_at": "2026-01-21T18:30:00Z",
      "updated_at": "2026-01-21T18:30:00Z"
    }
  ]
}
```

**Examples:**
```bash
# All items
curl -H "Authorization: Bearer $TOKEN" \
  https://api.chrisbuilds64.com/api/v1/items

# Search
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.chrisbuilds64.com/api/v1/items?search=milk"

# Filter by tags
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.chrisbuilds64.com/api/v1/items?tags=inbox,urgent"

# Combined
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.chrisbuilds64.com/api/v1/items?search=buy&tags=shopping"
```

---

### Get Item

```
GET /api/v1/items/{id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | Item ID |

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "label": "Example item",
  "content_type": "note",
  "tags": ["inbox"],
  "payload": {},
  "owner_id": "user-uuid",
  "created_at": "2026-01-21T18:30:00Z",
  "updated_at": "2026-01-21T18:30:00Z"
}
```

**Errors:**
- `404`: Item not found or not owned by user

---

### Create Item

```
POST /api/v1/items
```

**Request Body:**
```json
{
  "label": "Buy groceries",
  "content_type": "task",
  "tags": ["shopping", "inbox"],
  "payload": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| label | string | Yes | Item title/text |
| content_type | string | Yes | Type: note, task, link, other |
| tags | string[] | No | List of tags (default: []) |
| payload | object | No | Additional data (default: {}) |

**Response:** Created item (same as Get Item)

**Status:** `201 Created`

---

### Update Item

```
PUT /api/v1/items/{id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | Item ID |

**Request Body:**
```json
{
  "label": "Updated label",
  "content_type": "note",
  "tags": ["processed"]
}
```

All fields are optional - only provided fields are updated.

**Response:** Updated item

**Errors:**
- `404`: Item not found or not owned by user

---

### Delete Item

```
DELETE /api/v1/items/{id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | Item ID |

**Response:** `204 No Content`

**Errors:**
- `404`: Item not found or not owned by user

---

## Error Responses

Errors follow RFC 7807 Problem Details format:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Item not found",
  "instance": "/api/v1/items/invalid-uuid"
}
```

### Common Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Data Types

### Item

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| label | string | Main text/title |
| content_type | string | Category: note, task, link, other |
| tags | string[] | List of lowercase tags |
| payload | object | Flexible additional data |
| owner_id | UUID | User who owns this item |
| created_at | ISO 8601 | Creation timestamp |
| updated_at | ISO 8601 | Last update timestamp |

### Content Types

| Value | Intended Use |
|-------|--------------|
| note | General notes, thoughts |
| task | Actionable items |
| link | URLs, references |
| other | Anything else |

---

## Rate Limits

Currently no rate limits enforced. Subject to change.

---

## CORS

API allows requests from:
- `http://localhost:*`
- Production domains

---

## Versioning

API version is in the URL path: `/api/v1/`

Breaking changes will use a new version number.
