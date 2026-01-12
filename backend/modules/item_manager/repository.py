"""
Item Repository
"""
from typing import Optional, List
from datetime import datetime

from .models import Item


class ItemRepository:
    """
    Repository für Item-Persistenz.

    In-Memory für PoC, später austauschbar gegen DB-Adapter.
    """

    def __init__(self):
        self._storage: dict[str, Item] = {}

    def save(self, item: Item) -> Item:
        """Save item"""
        import uuid
        if not item.id:
            item.id = str(uuid.uuid4())
        self._storage[item.id] = item
        return item

    def find_by_id(self, item_id: str) -> Optional[Item]:
        """Find item by ID (excludes soft-deleted)"""
        item = self._storage.get(item_id)
        if item and not item.is_deleted():
            return item
        return None

    def find_all(
        self,
        owner_id: Optional[str] = None,
        content_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Item]:
        """
        Find items with filters.

        Args:
            owner_id: Filter by owner
            content_type: Filter by type
            tags: Filter by tags (any match)
            include_deleted: Include soft-deleted items
            limit: Max results
            offset: Skip results
        """
        results = []

        for item in self._storage.values():
            # Skip deleted unless requested
            if not include_deleted and item.is_deleted():
                continue

            # Filter by owner
            if owner_id and item.owner_id != owner_id:
                continue

            # Filter by content_type
            if content_type and item.content_type != content_type:
                continue

            # Filter by tags (any match)
            if tags:
                if not any(tag in item.tags for tag in tags):
                    continue

            results.append(item)

        # Sort by created_at descending
        results.sort(key=lambda x: x.created_at or datetime.min, reverse=True)

        return results[offset:offset + limit]

    def update(self, item: Item) -> Item:
        """Update item"""
        item.updated_at = datetime.utcnow()
        self._storage[item.id] = item
        return item

    def delete(self, item_id: str, hard: bool = False) -> bool:
        """
        Delete item.

        Args:
            item_id: Item to delete
            hard: If True, permanently delete. If False, soft-delete.
        """
        item = self._storage.get(item_id)
        if not item:
            return False

        if hard:
            del self._storage[item_id]
        else:
            item.soft_delete()
            self._storage[item_id] = item

        return True

    def restore(self, item_id: str) -> Optional[Item]:
        """Restore soft-deleted item"""
        item = self._storage.get(item_id)
        if item and item.is_deleted():
            item.deleted_at = None
            item.updated_at = datetime.utcnow()
            return item
        return None

    def clear(self):
        """Clear storage (for tests)"""
        self._storage.clear()
