"""
Database Adapter Interface

Basis-Interface für alle Database-Provider.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Any, TypeVar, Generic

T = TypeVar("T")


class DatabaseAdapter(ABC, Generic[T]):
    """
    Abstract base class for database adapters.

    Implementierungen: PostgreSQL, SQLite, Mock
    """

    @abstractmethod
    def save(self, entity: T) -> T:
        """
        Save entity to database.

        Args:
            entity: Entity to save

        Returns:
            Saved entity with ID
        """
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]:
        """
        Find entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Find all entities with pagination.

        Args:
            limit: Max results
            offset: Skip results

        Returns:
            List of entities
        """
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update existing entity.

        Args:
            entity: Entity with updated values

        Returns:
            Updated entity
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    def find_by(self, **criteria) -> List[T]:
        """
        Find entities by criteria.

        Args:
            **criteria: Field=value pairs

        Returns:
            List of matching entities
        """
        pass
