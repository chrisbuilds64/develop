"""
Structured Logging Configuration

Production-grade logging setup with structlog.
Supports JSON output (production) and pretty console (development).
"""
import sys
import logging
from typing import Literal

import structlog
from .processors import (
    mask_sensitive_data,
    add_app_context,
    censor_sql_passwords,
)
from .handlers import setup_async_handlers, stop_async_handlers


def setup_logging(
    environment: Literal["development", "production"] = "production",
    log_level: str = "INFO",
    enable_async: bool = True,
    enable_file_logging: bool = False
) -> None:
    """
    Configure structlog for production use.

    Args:
        environment: "development" or "production"
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_async: Enable async logging with QueueHandler (default: True)
        enable_file_logging: Enable file logging with rotation (default: False)

    Examples:
        >>> # Production setup (JSON output, async)
        >>> setup_logging(environment="production", log_level="INFO")

        >>> # Development setup (pretty console, async)
        >>> setup_logging(environment="development", log_level="DEBUG")

        >>> # With file logging
        >>> setup_logging(environment="production", enable_file_logging=True)
    """
    # Setup async handlers if enabled
    if enable_async:
        setup_async_handlers(
            environment=environment,
            log_level=log_level,
            enable_file_logging=enable_file_logging
        )
    else:
        # Fallback to basic config (blocking I/O)
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )

    # Quiet uvicorn access logs (we handle request logging via middleware)
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False

    # Shared processors (used in both environments)
    shared_processors = [
        # Merge context variables (request_id, user_id, etc.)
        structlog.contextvars.merge_contextvars,

        # Add application context
        add_app_context,

        # Add logger name
        structlog.stdlib.add_logger_name,

        # Add log level
        structlog.stdlib.add_log_level,

        # Support positional arguments
        structlog.stdlib.PositionalArgumentsFormatter(),

        # Add ISO 8601 timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # Add stack info if available
        structlog.processors.StackInfoRenderer(),

        # Format exception info
        structlog.processors.format_exc_info,

        # Security: Mask sensitive data (passwords, tokens, etc.)
        mask_sensitive_data,

        # Security: Censor passwords in SQL connection strings
        censor_sql_passwords,
    ]

    if environment == "production":
        # JSON output for production (log aggregators)
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_environment() -> Literal["development", "production"]:
    """
    Get current environment from environment variable.

    Returns:
        "development" or "production"

    Environment Variables:
        ENVIRONMENT: "development" or "production" (default: "development")
    """
    import os
    env = os.getenv("ENVIRONMENT", "development")

    if env not in ["development", "production"]:
        # Fallback to development for safety
        return "development"

    return env  # type: ignore


def get_log_level() -> str:
    """
    Get log level from environment variable.

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Environment Variables:
        LOG_LEVEL: Log level (default: "INFO")
    """
    import os
    return os.getenv("LOG_LEVEL", "INFO").upper()
