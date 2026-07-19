"""
FastAPI Logging Middleware

Request/response logging with correlation IDs and duration tracking.
"""
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Features:
    - Generates or extracts request_id from X-Request-ID header
    - Binds request context (method, path, client_ip) to all logs
    - Measures request duration
    - Logs request start and completion
    - Adds X-Request-ID to response headers
    - Handles exceptions with detailed logging
    - Cleans up context after request

    Usage:
        >>> from fastapi import FastAPI
        >>> from infrastructure.logging.middleware import LoggingMiddleware
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(LoggingMiddleware)
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and add logging context.

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response object with X-Request-ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Bind request-scoped context variables
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Start timer
        start_time = time.perf_counter()

        # Log request start
        logger.info(
            "request_started",
            query_params=dict(request.query_params) if request.query_params else None,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log successful completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log exception with details
            logger.exception(
                "request_failed",
                duration_ms=round(duration_ms, 2),
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )

            # Re-raise to let FastAPI's exception handlers deal with it
            raise

        finally:
            # Clear context after request (prevent leaks)
            structlog.contextvars.clear_contextvars()
