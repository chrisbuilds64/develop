"""
Dependency Injection - Adapter Wiring

Hier werden Module mit ihren Adaptern verbunden.
"""
from sqlalchemy.orm import Session
from fastapi import Depends

from infrastructure.config import config
from infrastructure.database_sqlalchemy import get_db
from modules.item_manager.repository import ItemRepository
from adapters.database.base import DatabaseAdapter
from modules.item_manager.models import Item


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


def get_auth_adapter():
    """Returns appropriate auth adapter based on environment"""
    if config.ENV == "test":
        from adapters.auth.mock import MockAuthAdapter
        return MockAuthAdapter()

    from adapters.auth.clerk import ClerkAdapter
    return ClerkAdapter(config.CLERK_SECRET_KEY)
