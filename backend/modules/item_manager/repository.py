"""
Item Repository

High-level repository using DatabaseAdapter.
Abstracts database operations for Item domain.
"""
from typing import Optional, List
from datetime import datetime

from adapters.database.base import DatabaseAdapter
from .models import Item


class ItemRepository:
    """
    Repository für Item-Persistenz.

    Uses DatabaseAdapter interface - implementation injected.
    """

    def __init__(self, db_adapter: DatabaseAdapter[Item]):
        """
        Initialize repository with database adapter.

        Args:
            db_adapter: Implementation of DatabaseAdapter (PostgreSQL, Mock, etc.)
        """
        self.db = db_adapter

    def save(self, item: Item) -> Item:
        """
        Save item to database.

        Args:
            item: Item to save

        Returns:
            Saved item with ID
        """
        return self.db.save(item)

    def find_by_id(self, item_id: str) -> Optional[Item]:
        """
        Find item by ID (excludes soft-deleted).

        Args:
            item_id: Item UUID

        Returns:
            Item if found and not deleted, None otherwise
        """
        item = self.db.find_by_id(item_id)
        if item and not item.is_deleted():
            return item
        return None

    def find_all(
        self,
        owner_id: Optional[str] = None,
        content_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
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
            search: Search term for label (case-insensitive)
            include_deleted: Include soft-deleted items
            limit: Max results
            offset: Skip results

        Returns:
            List of matching items
        """
        # Build criteria for database adapter
        criteria = {}
        if owner_id:
            criteria["owner_id"] = owner_id
        if content_type:
            criteria["content_type"] = content_type
        if tags:
            criteria["tags"] = tags
        if search:
            criteria["search"] = search
        criteria["include_deleted"] = include_deleted

        # Query via adapter
        items = self.db.find_by(**criteria)

        # Apply pagination (adapter handles sorting)
        return items[offset:offset + limit]

    def update(self, item: Item) -> Item:
        """
        Update existing item.

        Args:
            item: Item with updated values

        Returns:
            Updated item
        """
        item.updated_at = datetime.utcnow()
        return self.db.update(item)

    def delete(self, item_id: str, hard: bool = False) -> bool:
        """
        Delete item.

        Args:
            item_id: Item to delete
            hard: If True, permanently delete. If False, soft-delete.

        Returns:
            True if deleted
        """
        if hard:
            return self.db.delete(item_id)
        else:
            # Soft delete: update deleted_at timestamp
            item = self.db.find_by_id(item_id)
            if not item:
                return False
            item.soft_delete()
            self.db.update(item)
            return True

    def restore(self, item_id: str) -> Optional[Item]:
        """
        Restore soft-deleted item.

        Args:
            item_id: Item UUID

        Returns:
            Restored item if found and was deleted, None otherwise
        """
        item = self.db.find_by_id(item_id)
        if item and item.is_deleted():
            item.deleted_at = None
            item.updated_at = datetime.utcnow()
            return self.db.update(item)
        return None
