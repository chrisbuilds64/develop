"""
Logging Context Management

Provides typed access to context variables (request_id, user_id, etc.)
"""
from contextvars import ContextVar
from typing import Optional


# Request-scoped context variables
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.

    Returns:
        Request ID string or None if not set

    Example:
        >>> request_id = get_request_id()
        >>> if request_id:
        ...     print(f"Current request: {request_id}")
    """
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """
    Set request ID for current context.

    Args:
        request_id: Request ID string (typically UUID)

    Example:
        >>> set_request_id("req-abc-123")
    """
    request_id_var.set(request_id)


def get_user_id() -> Optional[str]:
    """
    Get current user ID from context.

    Returns:
        User ID string or None if not authenticated

    Example:
        >>> user_id = get_user_id()
        >>> if user_id:
        ...     print(f"Authenticated user: {user_id}")
    """
    return user_id_var.get()


def set_user_id(user_id: str) -> None:
    """
    Set user ID for current context.

    Typically called after authentication in a dependency.

    Args:
        user_id: User ID string

    Example:
        >>> # In auth dependency
        >>> set_user_id("user-456")
        >>>
        >>> # Now all logs will include user_id
        >>> logger.info("user_action")  # Includes user_id=user-456
    """
    user_id_var.set(user_id)


def clear_context() -> None:
    """
    Clear all context variables.

    Typically called at the end of a request to prevent leaks.
    Note: LoggingMiddleware already handles this automatically.

    Example:
        >>> clear_context()
    """
    request_id_var.set(None)
    user_id_var.set(None)
