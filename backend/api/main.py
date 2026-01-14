"""
FastAPI Entry Point
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.logging import setup_logging, get_logger, get_environment
from infrastructure.logging.middleware import LoggingMiddleware
from infrastructure.errors import register_exception_handlers
from api.routes import items

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

# Add middleware (order matters - last added = first executed)
app.add_middleware(LoggingMiddleware)

# Register exception handlers (RFC 7807 error responses)
register_exception_handlers(app)

# Register routes
app.include_router(items.router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.debug("health_check_called")
    return {"status": "ok"}
