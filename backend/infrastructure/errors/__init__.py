"""
Error Infrastructure

Exception hierarchy, error codes, and RFC 7807 responses.
"""
from .base import (
    BaseError,
    ValidationError,
    NotFoundError,
    AuthError,
    AdapterError,
    InternalError
)
from .codes import ErrorCodes
from .responses import ProblemDetail, create_problem_detail
from .middleware import register_exception_handlers

__all__ = [
    # Exceptions
    "BaseError",
    "ValidationError",
    "NotFoundError",
    "AuthError",
    "AdapterError",
    "InternalError",
    # Codes
    "ErrorCodes",
    # RFC 7807
    "ProblemDetail",
    "create_problem_detail",
    # FastAPI integration
    "register_exception_handlers"
]
