"""
Error Handlers

Zentrale Fehlerbehandlung und Logging.
"""
from typing import Optional

from infrastructure.logging import get_logger
from .base import BaseError

logger = get_logger("infrastructure.errors")


def handle_error(
    error: BaseError,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Zentrale Error-Behandlung.

    - Loggt den Error mit Context
    - Kann erweitert werden für Alerting, Metrics, etc.

    Args:
        error: Der aufgetretene Error
        request_id: Request ID für Tracing
        user_id: User ID falls bekannt
    """
    log_context = {
        "error_code": error.code,
        "error_message": error.message,
        "recoverable": error.recoverable,
        "context": error.context,
    }

    if request_id:
        log_context["request_id"] = request_id

    if user_id:
        log_context["user_id"] = user_id

    # Log Level basierend auf Error-Typ
    if error.code.startswith("E5"):
        # Internal Errors sind kritisch
        logger.critical("Internal error occurred", extra=log_context)
    elif error.code.startswith("E4"):
        # Adapter Errors sind wichtig
        logger.error("Adapter error occurred", extra=log_context)
    else:
        # Validation, NotFound, Auth sind normal
        logger.warning("Error occurred", extra=log_context)


def create_error_response(error: BaseError, request_id: Optional[str] = None) -> dict:
    """
    Erstellt strukturierte Error Response für API.

    Args:
        error: Der aufgetretene Error
        request_id: Request ID für Tracing

    Returns:
        Dict für JSON Response
    """
    response = {
        "error": error.code,
        "message": error.message if error.recoverable else "An error occurred",
    }

    if request_id:
        response["request_id"] = request_id

    return response
