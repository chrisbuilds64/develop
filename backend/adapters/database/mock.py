"""
Mock Database Adapter

Für Tests und Entwicklung. In-Memory Storage.
"""
from typing import Optional, List, Any
import uuid

from .base import DatabaseAdapter


class MockDatabaseAdapter(DatabaseAdapter):
    """
    Mock implementation for testing.

    Speichert alles in-memory.
    """

    def __init__(self):
        self._storage: dict[str, dict] = {}

    def save(self, entity: Any) -> Any:
        """Save to in-memory storage"""
        if not hasattr(entity, "id") or not entity.id:
            entity.id = str(uuid.uuid4())

        self._storage[entity.id] = entity
        return entity

    def find_by_id(self, entity_id: str) -> Optional[Any]:
        """Find in storage"""
        return self._storage.get(entity_id)

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Any]:
        """Get all from storage"""
        items = list(self._storage.values())
        return items[offset:offset + limit]

    def update(self, entity: Any) -> Any:
        """Update in storage"""
        if entity.id in self._storage:
            self._storage[entity.id] = entity
        return entity

    def delete(self, entity_id: str) -> bool:
        """Delete from storage"""
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False

    def find_by(self, **criteria) -> List[Any]:
        """Find by criteria"""
        results = []
        for entity in self._storage.values():
            match = all(
                getattr(entity, key, None) == value
                for key, value in criteria.items()
            )
            if match:
                results.append(entity)
        return results

    def clear(self):
        """Clear all storage (for tests)"""
        self._storage.clear()
