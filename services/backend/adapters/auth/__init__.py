"""
Auth Adapter Module

Pluggable authentication with multiple providers.
"""
from .base import AuthProvider, UserInfo
from .exceptions import AuthenticationError, TokenExpiredError, InsufficientPermissionsError
from .mock_adapter import MockAuthAdapter

__all__ = [
    "AuthProvider",
    "UserInfo",
    "AuthenticationError",
    "TokenExpiredError",
    "InsufficientPermissionsError",
    "MockAuthAdapter",
]
