"""
Database Connection Management

Zentrale Stelle für Datenbankverbindungen und Sessions.
"""
from infrastructure.config import config
from infrastructure.logging import get_logger

logger = get_logger("infrastructure.database")


class DatabaseConnection:
    """Database connection manager"""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self._connection = None

    def connect(self):
        """Establish database connection"""
        logger.info("Connecting to database", extra={"url": self._mask_url()})
        # Implementation depends on chosen DB library (SQLAlchemy, etc.)
        pass

    def disconnect(self):
        """Close database connection"""
        logger.info("Disconnecting from database")
        pass

    def _mask_url(self) -> str:
        """Mask sensitive parts of connection URL for logging"""
        # Hide password in logs
        return self.connection_url.split("@")[-1] if "@" in self.connection_url else self.connection_url


# Singleton instance
db = DatabaseConnection(config.DATABASE_URL)
