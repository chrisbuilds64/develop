# REQ-002: tweight App (Flutter)

**Status:** Draft
**Created:** 2026-01-20
**Author:** Christian + Claude
**Compliance:** [REQ-000 Infrastructure Standards](REQ-000-Infrastructure-Standards.md)

---

## 1. Overview

### 1.1 Purpose

Build a simple Todo/Item management app using Flutter that connects to our backend API. This is the first frontend app in the chrisbuilds64 ecosystem, serving as:
- API integration test client
- Reference implementation for future apps
- Proof of concept for the full stack

### 1.2 Scope

**In Scope:**
- User authentication (token-based, mock for now)
- Item CRUD operations (Create, Read, Update, Delete)
- Basic UI for item management

**Out of Scope (for this version):**
- Offline-first / local storage
- Real auth provider (Clerk)
- Complex UI/UX
- Multiple platforms (start with iOS/Android)

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | User can enter a token to authenticate | Must |
| FR-02 | User can view list of their items | Must |
| FR-03 | User can create a new item | Must |
| FR-04 | User can edit an existing item | Must |
| FR-05 | User can delete an item | Must |
| FR-06 | User can logout (clear token) | Must |
| FR-07 | App shows loading states | Should |
| FR-08 | App shows error messages (from API) | Must |

### 2.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-01 | KISS - Simple, minimal code | Must |
| NFR-02 | Works with production API (api.chrisbuilds64.com) | Must |
| NFR-03 | Configurable API base URL | Should |
| NFR-04 | No external state management (start simple) | Must |

---

## 3. Architecture

### 3.1 Project Structure

```
develop/apps/tweight/
├── lib/
│   ├── main.dart              # Entry point
│   ├── config.dart            # API URL configuration
│   ├── models/
│   │   └── item.dart          # Item data model
│   ├── services/
│   │   ├── api_client.dart    # HTTP client with auth
│   │   └── item_service.dart  # Item API operations
│   └── screens/
│       ├── login_screen.dart  # Token input
│       ├── items_screen.dart  # Item list
│       └── item_form_screen.dart # Create/Edit item
├── pubspec.yaml
└── README.md
```

### 3.2 Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Screen    │ --> │   Service   │ --> │  API Client │
│  (UI/State) │ <-- │  (Business) │ <-- │   (HTTP)    │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ Backend API     │
                                    │ (api.chris..com)│
                                    └─────────────────┘
```

---

## 4. API Integration

### 4.1 Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Connection test |
| GET | `/api/v1/items` | List items |
| POST | `/api/v1/items` | Create item |
| GET | `/api/v1/items/{id}` | Get item |
| PUT | `/api/v1/items/{id}` | Update item |
| DELETE | `/api/v1/items/{id}` | Delete item |

### 4.2 Authentication

All `/api/v1/*` endpoints require:
```
Authorization: Bearer <token>
```

**Test Tokens (Mock Auth):**
- `test-chris` → mock-user-chris-123
- `test-lars` → mock-user-lars-456
- `test-lily` → mock-user-lily-789

### 4.3 Item Model

```dart
class Item {
  final String id;
  final String ownerId;
  final String label;
  final String contentType;
  final Map<String, dynamic>? payload;
  final List<String> tags;
  final DateTime createdAt;
  final DateTime? updatedAt;
}
```

---

## 5. Screens

### 5.1 Login Screen

**Purpose:** Enter token to authenticate

**Elements:**
- Text field for token
- Login button
- "Use test-chris" quick button (dev convenience)
- Error message display

**Flow:**
1. User enters token
2. Tap Login
3. App stores token locally
4. Navigate to Items Screen

### 5.2 Items Screen

**Purpose:** View and manage items

**Elements:**
- App bar with logout button
- List of items (label, content_type, created_at)
- FAB to create new item
- Swipe to delete (or delete button)
- Tap to edit

**Flow:**
1. On load: Fetch items from API
2. Display list or empty state
3. Pull to refresh
4. Tap item → Edit screen
5. FAB → Create screen

### 5.3 Item Form Screen

**Purpose:** Create or edit an item

**Elements:**
- Label text field
- Content type dropdown (note, task, link, etc.)
- Payload JSON field (optional, simple text for now)
- Tags chips (optional, v2)
- Save button
- Cancel button

**Flow:**
1. If editing: Pre-fill fields
2. User modifies fields
3. Tap Save → API call
4. Success → Navigate back, refresh list
5. Error → Show message

---

## 6. Dependencies

### 6.1 Flutter Packages

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0              # HTTP client
  shared_preferences: ^2.2.0 # Token storage
```

**No additional packages needed for v1.** Keep it simple.

---

## 7. Configuration

### 7.1 API Base URL

```dart
// lib/config.dart
class Config {
  static const String apiBaseUrl = 'https://api.chrisbuilds64.com';

  // For local development:
  // static const String apiBaseUrl = 'http://localhost:8000';
}
```

---

## 8. Implementation Plan

### Phase 1: Setup
1. Create Flutter project in `develop/apps/tweight/`
2. Add dependencies (http, shared_preferences)
3. Create config.dart with API URL

### Phase 2: API Client
4. Create api_client.dart with token handling
5. Create item.dart model
6. Create item_service.dart with CRUD operations

### Phase 3: Screens
7. Create login_screen.dart
8. Create items_screen.dart
9. Create item_form_screen.dart

### Phase 4: Integration
10. Wire up navigation
11. Test with production API
12. Fix issues, polish

---

## 9. Test Scenarios

| Scenario | Expected |
|----------|----------|
| Login with valid token | Navigate to items list |
| Login with empty token | Show error |
| List items (has items) | Show items list |
| List items (empty) | Show empty state |
| Create item | Item appears in list |
| Edit item | Changes saved |
| Delete item | Item removed from list |
| API error | Show error message |
| Logout | Return to login, clear token |

---

## 10. Open Questions

- [ ] Should we use Provider/Riverpod for state? (Recommendation: No, keep simple first)
- [ ] Payload field: JSON editor or simple text? (Recommendation: Simple text first)
- [ ] Tags: Implement in v1 or defer? (Recommendation: Defer to v2)

---

## 11. Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Author | Claude | 2026-01-20 | Draft |
| Review | Christian | - | Pending |
