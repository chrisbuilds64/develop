"""
RFC 7807 Problem Details Response

Standard format for HTTP API error responses.
https://datatracker.ietf.org/doc/html/rfc7807
"""
from typing import Optional, Any
from pydantic import BaseModel, Field

from .base import BaseError


class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Details for HTTP APIs.

    Standard error response format used by Google, Microsoft, etc.
    """
    type: str = Field(
        description="URI reference identifying the problem type"
    )
    title: str = Field(
        description="Short, human-readable summary of the problem"
    )
    status: int = Field(
        description="HTTP status code"
    )
    detail: Optional[str] = Field(
        default=None,
        description="Human-readable explanation specific to this occurrence"
    )
    instance: Optional[str] = Field(
        default=None,
        description="URI reference identifying the specific occurrence"
    )
    # Extensions (RFC 7807 allows additional members)
    error_code: Optional[str] = Field(
        default=None,
        description="Application-specific error code (e.g., E2001)"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracing"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "https://api.chrisbuilds64.com/errors/item-not-found",
                "title": "Item Not Found",
                "status": 404,
                "detail": "Item with ID abc-123 does not exist",
                "instance": "/api/v1/items/abc-123",
                "error_code": "E2001",
                "request_id": "req-xyz-789"
            }
        }
    }


# Base URI for error types (can be configured)
ERROR_TYPE_BASE_URI = "https://api.chrisbuilds64.com/errors"


def create_problem_detail(
    error: BaseError,
    instance: Optional[str] = None,
    request_id: Optional[str] = None
) -> ProblemDetail:
    """
    Create RFC 7807 ProblemDetail from BaseError.

    Args:
        error: Application error
        instance: Request path that caused the error
        request_id: Request ID for tracing

    Returns:
        ProblemDetail response
    """
    # Create type URI from error code
    error_slug = _error_code_to_slug(error.code)
    type_uri = f"{ERROR_TYPE_BASE_URI}/{error_slug}"

    # For non-recoverable errors, hide internal details
    detail = error.message if error.recoverable else "An internal error occurred"

    return ProblemDetail(
        type=type_uri,
        title=_get_error_title(error),
        status=error.http_status,
        detail=detail,
        instance=instance,
        error_code=error.code,
        request_id=request_id
    )


def _error_code_to_slug(code: str) -> str:
    """Convert error code to URL-friendly slug."""
    # E2001 -> e2001
    return code.lower()


def _get_error_title(error: BaseError) -> str:
    """Get human-readable title for error type."""
    # Map error categories to titles
    titles = {
        "E1": "Validation Error",
        "E2": "Resource Not Found",
        "E3": "Authentication Error",
        "E4": "External Service Error",
        "E5": "Internal Server Error"
    }

    prefix = error.code[:2]
    return titles.get(prefix, "Error")
