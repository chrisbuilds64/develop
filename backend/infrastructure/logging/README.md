# Logging Module - Quick Start Guide

**Production-grade structured logging with structlog**

---

## ✅ What's Implemented

- ✅ **Structured logging** (JSON in production, pretty console in development)
- ✅ **Request correlation** (automatic request_id for every request)
- ✅ **FastAPI middleware** (request/response logging + duration tracking)
- ✅ **Context variables** (request_id, user_id, etc.)
- ✅ **ISO timestamps**
- ✅ **Exception formatting**
- ✅ **Environment-based config**

---

## 🚀 Quick Start

### 1. Application Startup

Logging is **already configured** in `api/main.py`. No action needed!

```python
from infrastructure.logging import setup_logging, get_logger

# Setup once (already done in main.py)
setup_logging(environment="production")

# Get logger anywhere
logger = get_logger()
```

### 2. Basic Usage

```python
from infrastructure.logging import get_logger

logger = get_logger()

# Structured logging (key-value pairs)
logger.info("user_login", user_id="123", email="user@example.com")
logger.debug("database_query", query="SELECT *", duration_ms=45.2)
logger.warning("rate_limit_exceeded", user_id="456", limit=100)
logger.error("payment_failed", order_id="789", error_code="CARD_DECLINED")

# Exception logging (includes full traceback)
try:
    risky_operation()
except Exception as e:
    logger.exception("operation_failed", operation="payment")
```

**Output (Development - Pretty Console):**
```
2026-01-13T07:52:35.903Z [info     ] user_login                    user_id=123 email=user@example.com
```

**Output (Production - JSON):**
```json
{"event": "user_login", "user_id": "123", "email": "user@example.com", "timestamp": "2026-01-13T07:52:35.903409Z", "level": "info"}
```

---

## 📋 Best Practices

### ✅ DO

**Use structured logging (key-value pairs):**
```python
logger.info("order_created", order_id=123, user_id=456, total=99.99)
```

**Use descriptive event names:**
```python
logger.info("payment_processed")  # Good
logger.info("done")               # Bad
```

**Log important business events:**
```python
logger.info("user_registered", user_id=user.id, source="web")
logger.info("order_completed", order_id=order.id, total=order.total)
```

**Include context in errors:**
```python
logger.error("database_error", table="users", operation="insert", error=str(e))
```

### ❌ DON'T

**Don't use string interpolation:**
```python
logger.info(f"User {user_id} logged in")  # ❌ Bad (not structured)
logger.info("user_logged_in", user_id=user_id)  # ✅ Good
```

**Don't log sensitive data:**
```python
logger.info("user_login", password=password)  # ❌ NEVER!
logger.info("payment", credit_card=card_number)  # ❌ NEVER!
```

**Don't over-log in hot paths:**
```python
for item in items:
    logger.debug("processing_item", item=item)  # ❌ Too much

logger.info("items_processed", count=len(items))  # ✅ Summary instead
```

---

## 🔍 Request Correlation

**Every request automatically gets a unique request_id.**

All logs during that request will include the same `request_id`.

### Example Request Flow

```bash
# Request 1
curl -H "X-Request-ID: my-custom-id" http://localhost:8000/api/v1/items
```

**Logs (all share same request_id):**
```
[info] request_started          request_id=my-custom-id method=GET path=/api/v1/items
[info] fetching_items           request_id=my-custom-id count=10
[info] request_completed        request_id=my-custom-id status_code=200 duration_ms=45.2
```

### Custom Request ID

Clients can provide their own request_id via header:

```bash
curl -H "X-Request-ID: my-trace-id" http://localhost:8000/health
```

If not provided, a UUID is generated automatically.

---

## 🎯 Advanced Usage

### Bound Logger (Persistent Context)

```python
# Bind context that persists across multiple log statements
logger = get_logger().bind(service="payment", version="2.0")

logger.info("service_started")    # Includes service=payment, version=2.0
logger.info("processing_payment") # Includes service=payment, version=2.0
```

### Context Variables (Request-Scoped)

Already handled automatically by middleware for request_id.

For user context (after authentication):

```python
import structlog

# In your auth dependency
structlog.contextvars.bind_contextvars(user_id=user.id, role=user.role)

# Now all logs in this request include user_id and role
logger.info("user_action")  # Includes user_id, role automatically
```

### Exception Logging

```python
try:
    result = process_payment(order_id)
except PaymentError as e:
    logger.exception(
        "payment_failed",
        order_id=order_id,
        error_code=e.code,
        amount=order.total
    )
    raise  # Re-raise after logging
```

**Output includes full traceback automatically.**

---

## 🔧 Configuration

### Environment Variables

```bash
# Environment (changes log format)
ENVIRONMENT=production  # JSON output
ENVIRONMENT=development # Pretty console (default)

# Log level
LOG_LEVEL=INFO   # Default
LOG_LEVEL=DEBUG  # More verbose
LOG_LEVEL=ERROR  # Only errors
```

### Docker

Already configured in `docker-compose.yml`:

```yaml
environment:
  - ENVIRONMENT=development
  - LOG_LEVEL=INFO
```

---

## 📊 Log Levels

Use the appropriate level:

- **DEBUG** - Detailed info for debugging (not in production)
- **INFO** - Important business events (default in production)
- **WARNING** - Something unexpected but handled
- **ERROR** - Errors that need attention
- **CRITICAL** - System is in critical state

```python
logger.debug("cache_miss", key="user:123")           # Development only
logger.info("order_created", order_id=123)           # Important events
logger.warning("retry_attempt", attempt=3, max=5)    # Unusual but handled
logger.error("api_call_failed", service="stripe")    # Needs attention
```

---

## 🧪 Testing Logs

### View Logs (Docker)

```bash
# Follow logs
docker-compose logs -f backend

# Last 50 lines
docker-compose logs --tail=50 backend

# Search for request_id
docker-compose logs backend | grep "request_id=abc-123"
```

### Test Request Correlation

```bash
# Send request with custom ID
curl -H "X-Request-ID: test-123" http://localhost:8000/health

# Check logs (should see test-123 in all logs for that request)
docker-compose logs --tail=10 backend | grep "test-123"
```

---

## 📝 Examples from Codebase

### main.py (Startup)

```python
from infrastructure.logging import setup_logging, get_logger

# Setup once
setup_logging(environment="production")

logger = get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="1.0")
    yield
    logger.info("application_shutdown")
```

### Route Handler

```python
from infrastructure.logging import get_logger

logger = get_logger()

@router.post("/items")
async def create_item(item: ItemCreate):
    logger.info("creating_item", content_type=item.content_type)

    try:
        result = await item_manager.create(item)
        logger.info("item_created", item_id=result.id)
        return result
    except Exception as e:
        logger.exception("item_creation_failed", error=str(e))
        raise
```

### Repository

```python
from infrastructure.logging import get_logger

logger = get_logger()

class ItemRepository:
    async def get_by_id(self, item_id: int):
        logger.debug("fetching_item", item_id=item_id)

        item = await self.db.get(item_id)

        if not item:
            logger.warning("item_not_found", item_id=item_id)
            return None

        logger.debug("item_fetched", item_id=item_id)
        return item
```

---

## 🚨 Common Issues

### Issue: Logs not appearing

**Solution:** Check log level
```bash
# Set to DEBUG temporarily
export LOG_LEVEL=DEBUG
docker-compose restart backend
```

### Issue: Request ID not in logs

**Solution:** Make sure middleware is registered
```python
# In main.py
app.add_middleware(LoggingMiddleware)
```

### Issue: Logs are unreadable

**Solution:** Check ENVIRONMENT variable
```bash
# Development = pretty console
export ENVIRONMENT=development

# Production = JSON
export ENVIRONMENT=production
```

---

## 🔮 Future Extensions

**Already planned (not implemented yet):**

- [ ] OpenTelemetry integration (trace correlation)
- [ ] Datadog trace correlation
- [ ] Sentry error tracking
- [ ] Async logging (QueueHandler for performance)
- [ ] Multiple handlers (file rotation, remote logging)
- [ ] Sensitive data filtering (auto-mask passwords, tokens)

---

## 📚 Resources

- **structlog docs:** https://www.structlog.org/
- **Planning doc:** `/control/planning/LOGGING-MODULE-PLAN.md`
- **Test script:** `test_logging.py`

---

## ✅ Quick Checklist

When writing code, remember:

- [ ] Use `logger.info("event_name", key=value)` (structured)
- [ ] Use descriptive event names
- [ ] Don't log sensitive data (passwords, tokens, PII)
- [ ] Use appropriate log level (DEBUG/INFO/WARNING/ERROR)
- [ ] Include relevant context (user_id, order_id, etc.)
- [ ] Use `logger.exception()` for caught exceptions

---

**Questions? Check the planning doc or ask Chris!**

---

**Last Updated:** 13. Januar 2026
**Status:** ✅ Phase 1 + Phase 2 Complete
