"""
Error Handling Middleware

FastAPI exception handlers for RFC 7807 responses.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from .base import BaseError, ValidationError, InternalError
from .responses import ProblemDetail, create_problem_detail, ERROR_TYPE_BASE_URI


logger = structlog.get_logger("infrastructure.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on FastAPI app.

    Call this once during app setup.
    """
    app.add_exception_handler(BaseError, handle_base_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_base_error(request: Request, error: BaseError) -> JSONResponse:
    """Handle our custom BaseError exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Log error
    _log_error(error, request_id, request.url.path)

    # Create RFC 7807 response
    problem = create_problem_detail(
        error=error,
        instance=request.url.path,
        request_id=request_id
    )

    return JSONResponse(
        status_code=error.http_status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json"
    )


async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    """Handle Pydantic/FastAPI validation errors."""
    request_id = getattr(request.state, "request_id", None)

    # Convert to our ValidationError
    details = []
    for err in error.errors():
        loc = ".".join(str(x) for x in err["loc"])
        details.append(f"{loc}: {err['msg']}")

    detail_message = "; ".join(details)

    logger.warning(
        "validation_error",
        request_id=request_id,
        path=request.url.path,
        errors=error.errors()
    )

    problem = ProblemDetail(
        type=f"{ERROR_TYPE_BASE_URI}/validation-error",
        title="Validation Error",
        status=422,
        detail=detail_message,
        instance=request.url.path,
        error_code="E1000",
        request_id=request_id
    )

    return JSONResponse(
        status_code=422,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json"
    )


async def handle_http_exception(request: Request, error: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette/FastAPI HTTP exceptions (404, 405, etc.)."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "http_exception",
        request_id=request_id,
        path=request.url.path,
        status_code=error.status_code,
        detail=error.detail
    )

    problem = ProblemDetail(
        type=f"{ERROR_TYPE_BASE_URI}/http-{error.status_code}",
        title=_http_status_title(error.status_code),
        status=error.status_code,
        detail=error.detail,
        instance=request.url.path,
        request_id=request_id
    )

    return JSONResponse(
        status_code=error.status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json"
    )


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Log full exception for debugging
    logger.critical(
        "unexpected_error",
        request_id=request_id,
        path=request.url.path,
        error_type=type(error).__name__,
        error_message=str(error),
        exc_info=True
    )

    # Return generic error (don't leak internal details)
    problem = ProblemDetail(
        type=f"{ERROR_TYPE_BASE_URI}/internal-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred",
        instance=request.url.path,
        error_code="E5001",
        request_id=request_id
    )

    return JSONResponse(
        status_code=500,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json"
    )


def _log_error(error: BaseError, request_id: str | None, path: str) -> None:
    """Log error with appropriate level."""
    log_data = {
        "request_id": request_id,
        "path": path,
        "error_code": error.code,
        "error_message": error.message,
        "recoverable": error.recoverable,
        "context": error.context
    }

    if error.code.startswith("E5"):
        logger.critical("internal_error", **log_data)
    elif error.code.startswith("E4"):
        logger.error("adapter_error", **log_data)
    else:
        logger.warning("application_error", **log_data)


def _http_status_title(status_code: int) -> str:
    """Get title for HTTP status code."""
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable"
    }
    return titles.get(status_code, "Error")
