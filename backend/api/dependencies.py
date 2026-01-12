"""
Dependency Injection - Adapter Wiring

Hier werden Module mit ihren Adaptern verbunden.
"""
from infrastructure.config import config


def get_database_adapter():
    """Returns appropriate database adapter based on environment"""
    if config.ENV == "test":
        from adapters.database.mock import MockDatabaseAdapter
        return MockDatabaseAdapter()

    from adapters.database.postgres import PostgresAdapter
    return PostgresAdapter(config.DATABASE_URL)


def get_auth_adapter():
    """Returns appropriate auth adapter based on environment"""
    if config.ENV == "test":
        from adapters.auth.mock import MockAuthAdapter
        return MockAuthAdapter()

    from adapters.auth.clerk import ClerkAdapter
    return ClerkAdapter(config.CLERK_SECRET_KEY)
