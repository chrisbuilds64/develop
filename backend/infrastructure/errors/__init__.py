"""
Error Infrastructure

Zentrale Error-Hierarchie und Handling.
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

__all__ = [
    "BaseError",
    "ValidationError",
    "NotFoundError",
    "AuthError",
    "AdapterError",
    "InternalError",
    "ErrorCodes"
]
