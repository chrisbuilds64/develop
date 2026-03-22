"""
FastAPI Entry Point
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from infrastructure.logging import setup_logging, get_logger, get_environment
from infrastructure.logging.middleware import LoggingMiddleware
from infrastructure.errors import register_exception_handlers
from api.rate_limit import limiter
from api.routes import items, accosite

# Setup logging on startup
environment = get_environment()
setup_logging(environment=environment, log_level=os.getenv("LOG_LEVEL", "INFO"))

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("application_startup", environment=environment, version="0.1.0")
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="ChrisBuilds64 API",
    version="0.1.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware (order matters - last added = first executed)
app.add_middleware(LoggingMiddleware)

# Register exception handlers (RFC 7807 error responses)
register_exception_handlers(app)

# Register routes
app.include_router(items.router, prefix="/api/v1")
app.include_router(accosite.router, prefix="/api/v1")


# Serve frontend apps (static files)
# Docker: /apps (mounted volume), Local: ../apps (relative to backend/)
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
apps_dir = "/apps" if os.path.exists("/apps") else os.path.join(os.path.dirname(_backend_dir), "apps")
if os.path.exists(apps_dir):
    for app_name in os.listdir(apps_dir):
        app_path = os.path.join(apps_dir, app_name)
        if os.path.isdir(app_path):
            app.mount(f"/app/{app_name}", StaticFiles(directory=app_path, html=True), name=app_name)


@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.debug("health_check_called")
    return {"status": "ok"}
