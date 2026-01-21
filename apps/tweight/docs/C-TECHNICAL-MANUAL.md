# tweight Technical Manual

## Overview

tweight is a Flutter mobile application that connects to a FastAPI backend for item management. This document describes the architecture, components, and implementation details sufficient to rebuild the application.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter App                          │
├─────────────────────────────────────────────────────────┤
│  Screens          │  Services         │  Widgets        │
│  - LoginScreen    │  - ApiClient      │  - TagPicker    │
│  - ItemsScreen    │  - ItemService    │                 │
│  - ItemFormScreen │                   │                 │
├─────────────────────────────────────────────────────────┤
│                    Models                               │
│                    - Item                               │
└─────────────────────────────────────────────────────────┘
                           │
                           │ HTTPS / REST
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│                    /api/v1/items                        │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
apps/tweight/
├── lib/
│   ├── main.dart                 # App entry, auto-login logic
│   ├── config.dart               # API URL configuration
│   ├── models/
│   │   └── item.dart             # Item data model
│   ├── services/
│   │   ├── api_client.dart       # HTTP client with auth
│   │   └── item_service.dart     # Item CRUD operations
│   ├── screens/
│   │   ├── login_screen.dart     # Token input screen
│   │   ├── items_screen.dart     # Main list view
│   │   └── item_form_screen.dart # Create/edit form
│   └── widgets/
│       └── tag_picker_dialog.dart # Reusable tag selection
├── docs/
│   ├── A-MARKETING.md
│   ├── B-USER-MANUAL.md
│   └── C-TECHNICAL-MANUAL.md
└── pubspec.yaml
```

---

## Data Model

### Item

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
}
```

**JSON mapping:**
- `id` ↔ `id`
- `label` ↔ `label`
- `contentType` ↔ `content_type`
- `payload` ↔ `payload`
- `tags` ↔ `tags`
- `ownerId` ↔ `owner_id`
- `createdAt` ↔ `created_at`
- `updatedAt` ↔ `updated_at`

---

## API Endpoints

Base URL: `https://api.chrisbuilds64.com`

### Authentication
All requests require `Authorization: Bearer <token>` header.

### Endpoints

| Method | Path | Description | Query Params |
|--------|------|-------------|--------------|
| GET | /api/v1/items | List all items | `search`, `tags`, `content_type` |
| GET | /api/v1/items/{id} | Get single item | - |
| POST | /api/v1/items | Create item | - |
| PUT | /api/v1/items/{id} | Update item | - |
| DELETE | /api/v1/items/{id} | Delete item | - |

### Query Parameters

- `search`: Case-insensitive substring match on label (ILIKE)
- `tags`: Comma-separated tag list, items must have ALL specified tags
- `content_type`: Filter by exact content type

### Request/Response Examples

**Create Item:**
```json
POST /api/v1/items
{
  "label": "Buy milk",
  "content_type": "task",
  "tags": ["shopping", "inbox"],
  "payload": {}
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "label": "Buy milk",
  "content_type": "task",
  "tags": ["shopping", "inbox"],
  "payload": {},
  "owner_id": "user-uuid",
  "created_at": "2026-01-21T18:30:00Z",
  "updated_at": "2026-01-21T18:30:00Z"
}
```

**List Items with filter:**
```
GET /api/v1/items?search=milk&tags=shopping
```

---

## Components

### ApiClient

Handles HTTP communication with backend.

**Responsibilities:**
- Store and attach auth token
- Make GET, POST, PUT, DELETE requests
- Parse JSON responses
- Throw `ApiException` on errors

**Key Methods:**
```dart
void setToken(String token)
void clearToken()
Future<Map<String, dynamic>> get(String path)
Future<Map<String, dynamic>> post(String path, Map<String, dynamic> data)
Future<Map<String, dynamic>> put(String path, Map<String, dynamic> data)
Future<void> delete(String path)
```

### ItemService

Business logic layer for item operations.

**Key Methods:**
```dart
Future<List<Item>> getItems({String? search, List<String>? tags})
Future<Item> getItem(String id)
Future<Item> createItem({required String label, required String contentType, List<String>? tags})
Future<Item> updateItem(String id, {String? label, String? contentType, List<String>? tags})
Future<void> deleteItem(String id)
```

### TagPickerDialog

Reusable widget for tag selection.

**Props:**
- `availableTags`: Set of all available tags
- `selectedTags`: Currently selected tags
- `title`: Dialog title

**Returns:** `List<String>?` - selected tags or null if cancelled

**Features:**
- Search/filter tags
- Alphabetical sorting
- Checkbox multi-select
- Selected tags shown as removable chips

---

## Screens

### LoginScreen

**State:**
- `_tokenController`: Text input for token
- `_loading`: Show spinner during login

**Flow:**
1. User enters token
2. Token saved to SharedPreferences
3. ApiClient configured with token
4. Navigate to ItemsScreen

### ItemsScreen

**State:**
- `_items`: List of items
- `_loading`, `_error`: Loading states
- `_searchQuery`: Current search text
- `_selectedTags`: Active tag filters
- `_availableTags`: All tags from items
- `_textViewMode`: View toggle

**Features:**
- Search with 300ms debounce
- Tag filtering (individual chips + picker dialog)
- Quick Capture (multi-line inbox)
- View toggle (Card/Text)
- Pull to refresh
- Delete with confirmation

### ItemFormScreen

**State:**
- `_labelController`: Label text
- `_tagController`: New tag input
- `_contentType`: Selected type
- `_tags`: Assigned tags
- `_availableTags`: All available tags
- `_saving`, `_error`: Save states

**Features:**
- Create or edit mode (based on `item` prop)
- Tag picker integration
- Manual tag entry
- Validation (label required)

---

## Key Patterns

### State Management
Simple `setState()` - no external state management library. KISS principle.

### Error Handling
- `ApiException` with message for API errors
- Try/catch in screens with user-friendly messages
- `mounted` check before setState after async operations

### Token Storage
`SharedPreferences` for persistent local storage.

### Search Debounce
300ms delay before API call to avoid excessive requests.

---

## Dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.0
```

---

## Building

```bash
# Development
flutter run -d <device-id>

# Release (iOS)
flutter build ios --release

# Release (Android)
flutter build apk --release
```

---

## Backend Requirements

The backend must provide:
1. REST API at `/api/v1/items`
2. Bearer token authentication
3. CRUD operations for items
4. Search parameter with ILIKE matching
5. Tags parameter with comma-separated values
6. JSON responses matching the Item model

See `/develop/backend/` for FastAPI implementation.
