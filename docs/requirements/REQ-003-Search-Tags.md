# REQ-003: Search & Tags Feature

**Status:** Draft
**Created:** 2026-01-21
**Author:** Christian + Claude
**Compliance:** [REQ-000 Infrastructure Standards](REQ-000-Infrastructure-Standards.md)

---

## 1. Overview

### 1.1 Purpose

Extend Item API with text search capability and improve tag handling in both backend and Flutter app.

### 1.2 Scope

- Backend: Add search parameter for label text search
- Flutter: Search bar UI
- Flutter: Tag filter UI
- Flutter: Tag management in Create/Edit forms

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Search items by label (case-insensitive, partial match) | Must |
| FR-02 | Combine search with existing filters (tags, content_type) | Must |
| FR-03 | Flutter: Display search bar on items list | Must |
| FR-04 | Flutter: Display tag filter chips | Must |
| FR-05 | Flutter: Add/remove tags in item form | Must |
| FR-06 | Flutter: Show tags on item list entries | Should |
| FR-07 | Debounce search input (300ms) | Should |

### 2.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-01 | Search response < 200ms for up to 1000 items | Should |
| NFR-02 | RFC 7807 compliant error responses | Must |

---

## 3. API Design

### 3.1 Search Parameter

**Endpoint:** `GET /api/v1/items`

**New Query Parameter:**
```
search: Optional[str] - Search term for label (case-insensitive LIKE)
```

**Example Requests:**
```bash
# Search by text
GET /api/v1/items?search=weight

# Search + tag filter
GET /api/v1/items?search=weight&tags=health,fitness

# All filters combined
GET /api/v1/items?search=weight&tags=health&content_type=note
```

### 3.2 Implementation

**Backend (PostgreSQL):**
```sql
SELECT * FROM items
WHERE owner_id = :owner_id
  AND deleted_at IS NULL
  AND label ILIKE '%' || :search || '%'
  AND tags @> ARRAY[:tags]
```

---

## 4. Flutter UI Design

### 4.1 Items Screen

```
┌─────────────────────────────────────┐
│ [🔍 Search items...              ]  │  ← Search bar
├─────────────────────────────────────┤
│ [health] [fitness] [x clear all]    │  ← Active tag filters
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Weight Entry                    │ │
│ │ health, fitness      12:30     │ │  ← Tags shown
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Gym Session                     │ │
│ │ fitness              Yesterday │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 4.2 Item Form (Create/Edit)

```
┌─────────────────────────────────────┐
│ Label                               │
│ [Weight Entry                    ]  │
├─────────────────────────────────────┤
│ Tags                                │
│ [health] [fitness] [+ Add tag]      │  ← Chip input
├─────────────────────────────────────┤
│ Content Type                        │
│ [note                        ▼]     │
├─────────────────────────────────────┤
│           [Save]                    │
└─────────────────────────────────────┘
```

---

## 5. Implementation Tasks

### 5.1 Backend

- [ ] Add `search` query parameter to `GET /items`
- [ ] Implement ILIKE search in repository
- [ ] Test search + filter combination

### 5.2 Flutter

- [ ] Add search bar to items screen
- [ ] Add tag filter chips below search
- [ ] Show tags on item list entries
- [ ] Add tag input to item form
- [ ] Debounce search input
- [ ] Update ItemService with search parameter

---

## 6. Test Cases

| ID | Test | Expected |
|----|------|----------|
| TC-01 | Search "weight" | Returns items with "weight" in label |
| TC-02 | Search "WEIGHT" | Same result (case-insensitive) |
| TC-03 | Search + tag filter | Returns intersection |
| TC-04 | Empty search | Returns all items (no filter) |
| TC-05 | No results | Returns empty list, not error |

---

## 7. Dependencies

- Existing: Item API with tags support
- Existing: Flutter tweight app

---

**Approved:** Pending
**Implementation Start:** 2026-01-21
