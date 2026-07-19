"""
Request Logger Middleware

Loggt alle eingehenden Requests und ausgehenden Responses.
"""
import time
import uuid

from fastapi import Request

from infrastructure.logging import get_logger

logger = get_logger("api.middleware.request_logger")


async def request_logger_middleware(request: Request, call_next):
    """Middleware that logs all requests and responses"""
    # Request ID generieren
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    # Start Zeit
    start_time = time.time()

    # Request loggen
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None
        }
    )

    # Request verarbeiten
    response = await call_next(request)

    # Response Zeit
    process_time = time.time() - start_time

    # Response loggen
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2)
        }
    )

    # Request ID im Response Header
    response.headers["X-Request-ID"] = request_id

    return response
