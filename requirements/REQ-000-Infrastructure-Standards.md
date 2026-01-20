# REQ-000: Infrastructure Standards

**Status:** Approved (Reverse-documented from implementation)
**Created:** 2026-01-20
**Implemented:** 2026-01-13/14

---

## 1. Purpose

This document defines mandatory infrastructure standards that ALL modules and adapters must follow. These are non-negotiable foundations for consistency, debuggability, and maintainability.

---

## 2. Mandatory Standards

### 2.1 Error Handling

**Every module MUST use the centralized error system.**

| Requirement | Implementation |
|-------------|----------------|
| Use `BaseError` hierarchy | `infrastructure.errors.base` |
| Use defined error codes | `infrastructure.errors.codes.ErrorCodes` |
| Return RFC 7807 responses | `infrastructure.errors.responses.ProblemDetail` |
| Never raise raw `Exception` | Always use typed errors |

**Error Code Ranges:**

```
E1xxx - Validation Errors (400)
E2xxx - NotFound Errors (404)
E3xxx - Auth Errors (401/403)
E4xxx - Adapter/External Errors (502)
E5xxx - Internal Errors (500)
```

**Usage:**

```python
from infrastructure.errors.base import ValidationError, NotFoundError, AuthError
from infrastructure.errors.codes import ErrorCodes

# Correct
raise NotFoundError(
    message="Item not found",
    code=ErrorCodes.ITEM_NOT_FOUND,
    context={"item_id": item_id}
)

# Wrong - never do this
raise Exception("Item not found")
```

**Location:** `backend/infrastructure/errors/`

---

### 2.2 Logging

**Every module MUST use structured logging via structlog.**

| Requirement | Implementation |
|-------------|----------------|
| Use `get_logger()` | `infrastructure.logging.get_logger` |
| Structured key-value logging | `logger.info("event", key=value)` |
| No string interpolation | Never `f"User {id}"` |
| No sensitive data | Never log passwords, tokens, PII |

**Usage:**

```python
from infrastructure.logging import get_logger

logger = get_logger()

# Correct
logger.info("item_created", item_id=item.id, owner_id=owner_id)
logger.error("database_error", operation="insert", error=str(e))

# Wrong
logger.info(f"Created item {item.id}")  # No structured data
logger.info("login", password=pw)        # Sensitive data!
```

**Log Levels:**

| Level | Use Case |
|-------|----------|
| DEBUG | Development details, not in prod |
| INFO | Business events (default) |
| WARNING | Unexpected but handled |
| ERROR | Needs attention |
| CRITICAL | System failure |

**Location:** `backend/infrastructure/logging/`
**Documentation:** `backend/infrastructure/logging/README.md`

---

## 3. Module Checklist

Before implementing any new module, verify:

- [ ] Uses `BaseError` subclasses for all errors
- [ ] Uses `ErrorCodes` constants (or adds new ones)
- [ ] Uses `get_logger()` for all logging
- [ ] Uses structured logging (key-value pairs)
- [ ] No sensitive data in logs
- [ ] No raw `Exception` raises

---

## 4. Architecture Location

```
backend/
├── infrastructure/          # Mandatory foundations
│   ├── errors/              # Error handling (RFC 7807)
│   │   ├── base.py          # BaseError hierarchy
│   │   ├── codes.py         # ErrorCodes constants
│   │   ├── responses.py     # ProblemDetail (RFC 7807)
│   │   ├── handlers.py      # Error handlers
│   │   └── middleware.py    # FastAPI middleware
│   ├── logging/             # Structured logging
│   │   ├── __init__.py      # get_logger(), setup_logging()
│   │   ├── config.py        # Environment-based config
│   │   ├── context.py       # Request correlation
│   │   ├── middleware.py    # FastAPI middleware
│   │   └── README.md        # Usage guide
│   └── config.py            # Environment config
├── adapters/                # External integrations (use infrastructure)
├── modules/                 # Business logic (use infrastructure)
└── api/                     # Routes (use infrastructure)
```

---

## 5. Adding New Error Codes

When a module needs a new error code:

1. Add to `infrastructure/errors/codes.py`
2. Follow the range convention (E1xxx-E5xxx)
3. Use descriptive constant name

```python
# In codes.py
class ErrorCodes:
    # === Auth (E3xxx) ===
    INVALID_TOKEN = "E3001"
    TOKEN_EXPIRED = "E3002"
    # Add new:
    SESSION_INVALID = "E3005"
```

---

## 6. Integration with FastAPI

**Middleware is already configured in `api/main.py`:**

- `LoggingMiddleware` - Request correlation, timing
- `error_handler_middleware` - Converts errors to RFC 7807

**New routes automatically benefit from both.**

---

## 7. References

| Document | Location |
|----------|----------|
| Logging README | `backend/infrastructure/logging/README.md` |
| Error Base Classes | `backend/infrastructure/errors/base.py` |
| RFC 7807 Responses | `backend/infrastructure/errors/responses.py` |

---

## 8. Compliance

All requirements documents (REQ-001, REQ-002, etc.) MUST reference this document and ensure compliance with these standards.

---

**Last Updated:** 2026-01-20
