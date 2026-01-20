"""
Auth Exceptions

Authentication-specific errors using infrastructure error system.
Compliant with REQ-000 Infrastructure Standards.
"""
from infrastructure.errors.base import AuthError
from infrastructure.errors.codes import ErrorCodes


class AuthenticationError(AuthError):
    """
    Token verification failed.

    Raised when:
    - Token is missing
    - Token is invalid
    - Token is expired
    - Token format is wrong
    """
    code = ErrorCodes.INVALID_TOKEN
    message = "Authentication failed"
    http_status = 401
    recoverable = True


class TokenExpiredError(AuthError):
    """Token has expired."""
    code = ErrorCodes.TOKEN_EXPIRED
    message = "Token has expired"
    http_status = 401
    recoverable = True


class InsufficientPermissionsError(AuthError):
    """User lacks required permissions."""
    code = ErrorCodes.INSUFFICIENT_PERMISSIONS
    message = "Insufficient permissions"
    http_status = 403
    recoverable = True
