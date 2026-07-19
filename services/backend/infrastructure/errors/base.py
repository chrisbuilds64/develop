"""
Error Base Classes

Hierarchie für alle Application Errors.
"""
from typing import Optional


class BaseError(Exception):
    """
    Basis für alle Application Errors.

    Attributes:
        code: Error code (z.B. E1001)
        message: Human-readable message
        context: Debug-Informationen
        recoverable: Kann der User etwas tun?
        http_status: HTTP Status Code für API
    """

    code: str = "E0000"
    message: str = "An error occurred"
    http_status: int = 500
    recoverable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[dict] = None,
        recoverable: Optional[bool] = None
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.context = context or {}
        self.recoverable = recoverable if recoverable is not None else self.__class__.recoverable
        super().__init__(self.message)


class ValidationError(BaseError):
    """Input ungültig - E1xxx"""
    code = "E1000"
    message = "Validation failed"
    http_status = 400
    recoverable = True


class NotFoundError(BaseError):
    """Resource nicht gefunden - E2xxx"""
    code = "E2000"
    message = "Resource not found"
    http_status = 404
    recoverable = True


class AuthError(BaseError):
    """Authentifizierung/Autorisierung fehlgeschlagen - E3xxx"""
    code = "E3000"
    message = "Authentication failed"
    http_status = 401
    recoverable = True


class AdapterError(BaseError):
    """Externes System fehlgeschlagen - E4xxx"""
    code = "E4000"
    message = "External service error"
    http_status = 502
    recoverable = False


class InternalError(BaseError):
    """Interner Fehler - E5xxx"""
    code = "E5000"
    message = "Internal server error"
    http_status = 500
    recoverable = False
