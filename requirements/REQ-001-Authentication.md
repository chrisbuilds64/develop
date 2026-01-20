# REQ-001: Authentication Service

**Status:** Draft
**Created:** 2026-01-20
**Author:** Christian + Claude
**Compliance:** [REQ-000 Infrastructure Standards](REQ-000-Infrastructure-Standards.md)

---

## 1. Overview

### 1.1 Purpose

Implement a pluggable authentication service following the adapter pattern. The service provides a unified API for user authentication while supporting multiple backend providers (Mock for testing, Clerk for production, future: SuperTokens).

### 1.2 Scope

- JWT token verification
- User identity extraction (user_id, email, name)
- FastAPI dependency injection for protected routes
- Environment-based provider selection
- Test user support for development

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Verify JWT tokens and extract user identity | Must |
| FR-02 | Support Bearer token authentication header | Must |
| FR-03 | Return standardized user info (user_id, email, name) | Must |
| FR-04 | Auto-select provider based on ENV variable | Must |
| FR-05 | Provide FastAPI dependency for protected routes | Must |
| FR-06 | Support Mock adapter for testing without external services | Must |
| FR-07 | Support Clerk adapter for production | Must |
| FR-08 | Return proper HTTP 401 for invalid/missing tokens | Must |
| FR-09 | Support future providers (SuperTokens, Auth0) | Should |

### 2.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-01 | No external API calls in test/development mode | Must |
| NFR-02 | Provider switching without code changes | Must |
| NFR-03 | Secrets only in environment variables | Must |
| NFR-04 | RFC 7807 compliant error responses | Must |

---

## 3. Architecture

### 3.1 Adapter Pattern

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Routes                    │
│              (get_current_user dependency)           │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                  AuthService                         │
│            (Unified API Interface)                   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│               AuthProvider (ABC)                     │
│         verify_token(token) → UserInfo              │
└─────────────────────┬───────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│MockAdapter│  │ClerkAdapter│  │ Future... │
│  (Test)   │  │  (Prod)    │  │           │
└───────────┘  └───────────┘  └───────────┘
```

### 3.2 Directory Structure

```
backend/
├── adapters/
│   └── auth/
│       ├── __init__.py
│       ├── base.py           # AuthProvider ABC + UserInfo model
│       ├── mock_adapter.py   # Mock implementation
│       ├── clerk_adapter.py  # Clerk implementation
│       └── exceptions.py     # AuthenticationError
├── api/
│   └── dependencies/
│       └── auth.py           # get_current_user dependency
```

### 3.3 Provider Selection

```python
ENV variable → Provider
─────────────────────────
"test"        → MockAuthAdapter
"development" → MockAuthAdapter
"local"       → MockAuthAdapter
"production"  → ClerkAdapter
"staging"     → ClerkAdapter
```

---

## 4. Test Users (Mock Adapter)

| Token | User ID | Email | Name |
|-------|---------|-------|------|
| `test-chris` | `mock-user-chris-123` | `chris@test.com` | Chris (Mock) |
| `test-lars` | `mock-user-lars-456` | `lars@test.com` | Lars (Mock) |
| `test-lily` | `mock-user-lily-789` | `lily@test.com` | Lily (Mock) |

**Token Format:** Any token starting with `test-` or `mock-` is accepted. User is determined by name in token (chris/lars/lily).

---

## 5. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENV` | Yes | Environment: test/development/local/production/staging |
| `CLERK_SECRET_KEY` | Prod only | Clerk backend secret key |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Prod only | Clerk public key (for clients) |

---

## 6. API Contract

### 6.1 AuthProvider Interface

```python
class AuthProvider(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> UserInfo:
        """
        Verify token and return user info.

        Args:
            token: JWT token (without "Bearer " prefix)

        Returns:
            UserInfo with user_id, email, name

        Raises:
            AuthenticationError: Invalid or expired token
        """
        pass

@dataclass
class UserInfo:
    user_id: str
    email: str
    name: str
```

### 6.2 FastAPI Dependency

```python
def get_current_user(
    authorization: str = Header(...)
) -> UserInfo:
    """
    Extract and verify Bearer token from Authorization header.

    Returns:
        UserInfo for authenticated user

    Raises:
        HTTPException 401: Missing or invalid token
    """
```

### 6.3 Error Response (RFC 7807)

```json
{
  "type": "https://api.chrisbuilds64.com/errors/authentication-failed",
  "title": "Authentication Failed",
  "status": 401,
  "detail": "Invalid or expired token",
  "instance": "/api/v1/items"
}
```

---

## 7. Implementation Plan

### Phase 1: Core Infrastructure
1. Create `adapters/auth/` directory structure
2. Implement `AuthProvider` ABC and `UserInfo` model
3. Implement `AuthenticationError` exception
4. Implement `MockAuthAdapter` with test users

### Phase 2: FastAPI Integration
5. Create `get_current_user` dependency
6. Integrate with RFC 7807 error handling
7. Add auth to existing routes (optional per route)

### Phase 3: Clerk Integration
8. Implement `ClerkAdapter` with JWT verification
9. Add Clerk SDK dependency
10. Test with real Clerk tokens

### Phase 4: Testing
11. Unit tests for MockAdapter
12. Unit tests for ClerkAdapter (mocked SDK)
13. Integration tests for protected routes

---

## 8. Dependencies

### New Dependencies (requirements.txt)

```
# Phase 1-2: None (Mock only)

# Phase 3: Clerk
clerk-backend-api>=0.1.0
PyJWT>=2.8.0
```

---

## 9. Migration Notes

### From Hardcoded owner_id

Current state:
```python
# api/routes/items.py
owner_id = "demo-user"  # TODO: Replace with auth
```

After implementation:
```python
@router.get("/items")
def list_items(current_user: UserInfo = Depends(get_current_user)):
    items = item_service.list_items(owner_id=current_user.user_id)
```

---

## 10. Reference

### Existing Implementation (Archive)

Previous implementation available at:
```
archive/2026-01-08-pre-restructure/develop/core/auth/
├── base.py           # AuthProvider ABC
├── clerk_adapter.py  # Clerk implementation
├── mock_adapter.py   # Mock implementation
├── middleware.py     # FastAPI integration
└── login_handler.py  # User mapping
```

### Clerk Credentials (Test Environment)

```
CLERK_SECRET_KEY=sk_test_reM1dE57Mgu0QleqC1ZBjonz09YvUBAZtFGITLVMVJ
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_c21vb3RoLWxpb25maXNoLTg1LmNsZXJrLmFjY291bnRzLmRldiQ
```

---

## 11. Open Questions

- [ ] Should we auto-create users in our database on first auth?
- [ ] Do we need refresh token handling?
- [ ] Should Mock adapter validate token format strictly?

---

## 12. Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Author | Claude | 2026-01-20 | Draft |
| Review | Christian | - | Pending |
