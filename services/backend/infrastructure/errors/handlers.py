"""
Error Handlers

Utility functions for error handling outside of API context.
For API errors, use middleware.py which handles RFC 7807 responses.
"""
from typing import Optional
import structlog

from .base import BaseError

logger = structlog.get_logger("infrastructure.errors")


def handle_error(
    error: BaseError,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log error with context.

    Note: For API errors, prefer raising the exception and letting
    the middleware handle it. This function is for non-API contexts
    (background jobs, CLI scripts, etc.).

    Args:
        error: The error that occurred
        request_id: Request ID for tracing
        user_id: User ID if known
    """
    log_data = {
        "error_code": error.code,
        "error_message": error.message,
        "recoverable": error.recoverable,
        "context": error.context,
    }

    if request_id:
        log_data["request_id"] = request_id

    if user_id:
        log_data["user_id"] = user_id

    # Log level based on error type
    if error.code.startswith("E5"):
        logger.critical("internal_error", **log_data)
    elif error.code.startswith("E4"):
        logger.error("adapter_error", **log_data)
    else:
        logger.warning("application_error", **log_data)
