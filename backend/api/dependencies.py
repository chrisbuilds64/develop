"""
Dependency Injection - Adapter Wiring

Hier werden Module mit ihren Adaptern verbunden.
Compliant with REQ-000 Infrastructure Standards.
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Depends, Header

from infrastructure.config import config
from infrastructure.database_sqlalchemy import get_db
from infrastructure.logging import get_logger
from modules.item_manager.repository import ItemRepository
from adapters.database.base import DatabaseAdapter
from adapters.auth import AuthProvider, UserInfo, MockAuthAdapter, AuthenticationError
from modules.item_manager.models import Item

logger = get_logger()


def get_database_adapter(db: Session = Depends(get_db)) -> DatabaseAdapter[Item]:
    """
    Returns appropriate database adapter based on environment.

    Args:
        db: SQLAlchemy session (injected by FastAPI)

    Returns:
        DatabaseAdapter implementation
    """
    if config.ENV == "test":
        from adapters.database.mock import MockDatabaseAdapter
        return MockDatabaseAdapter()

    # Production: Use PostgreSQL adapter
    from adapters.database.postgresql import PostgreSQLAdapter
    return PostgreSQLAdapter(db)


def get_item_repository(
    db_adapter: DatabaseAdapter[Item] = Depends(get_database_adapter)
) -> ItemRepository:
    """
    Returns ItemRepository with injected database adapter.

    Args:
        db_adapter: Database adapter implementation (injected)

    Returns:
        ItemRepository instance
    """
    return ItemRepository(db_adapter)


def get_auth_provider() -> AuthProvider:
    """
    Returns appropriate auth provider based on environment.

    ENV in (test, development, local) → MockAuthAdapter
    ENV in (production, staging) → ClerkAdapter (future)
    """
    if config.ENV in ("test", "development", "local"):
        logger.debug("auth_provider_selected", provider="mock", env=config.ENV)
        return MockAuthAdapter()

    # Future: Clerk implementation
    # from adapters.auth.clerk_adapter import ClerkAdapter
    # return ClerkAdapter()

    # For now, default to mock in all environments
    logger.warning("auth_provider_fallback", env=config.ENV, fallback="mock")
    return MockAuthAdapter()


# Global auth provider instance (lazy loaded)
_auth_provider: Optional[AuthProvider] = None


def _get_auth_provider() -> AuthProvider:
    """Get or create auth provider singleton."""
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = get_auth_provider()
    return _auth_provider


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> UserInfo:
    """
    FastAPI dependency to extract and verify current user from token.

    Usage:
        @router.get("/items")
        def list_items(current_user: UserInfo = Depends(get_current_user)):
            ...

    Args:
        authorization: Authorization header (Bearer token)

    Returns:
        UserInfo for authenticated user

    Raises:
        AuthenticationError: If token is missing or invalid
    """
    logger.debug("auth_verify_start")

    # Check for Authorization header
    if not authorization:
        logger.warning("auth_failed", reason="missing_header")
        raise AuthenticationError(
            message="Authorization header is required",
            context={"reason": "missing_header"}
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("auth_failed", reason="invalid_format")
        raise AuthenticationError(
            message="Invalid authorization format. Use: Bearer <token>",
            context={"reason": "invalid_format"}
        )

    token = parts[1]

    # Verify token with auth provider
    auth_provider = _get_auth_provider()
    user_info = auth_provider.verify_token(token)

    logger.info("auth_success", user_id=user_info.user_id)
    return user_info
