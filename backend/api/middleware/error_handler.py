"""
Global Error Handler Middleware

Fängt alle Exceptions und wandelt sie in strukturierte HTTP Responses.
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from infrastructure.errors.base import BaseError
from infrastructure.errors.handlers import handle_error
from infrastructure.logging import get_logger

logger = get_logger("api.middleware.error_handler")


async def error_handler_middleware(request: Request, call_next):
    """Middleware that catches all exceptions and returns structured responses"""
    try:
        return await call_next(request)
    except BaseError as e:
        # Bekannter Error - strukturiert behandeln
        handle_error(e, request_id=getattr(request.state, "request_id", None))
        return JSONResponse(
            status_code=e.http_status,
            content={
                "error": e.code,
                "message": e.message if e.recoverable else "An error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    except Exception as e:
        # Unbekannter Error - als Internal Error behandeln
        logger.critical("Unexpected error", extra={"error": str(e)})
        return JSONResponse(
            status_code=500,
            content={
                "error": "E5001",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )
