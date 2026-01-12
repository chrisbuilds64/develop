"""
Item Manager Service

Business Logic für Items.
"""
from typing import Optional, List
from datetime import datetime

from infrastructure.logging import get_logger
from .models import Item
from .repository import ItemRepository
from .exceptions import ItemNotFoundError, ItemValidationError

logger = get_logger("modules.item_manager")


class ItemManager:
    """
    Item Management Service.

    Handles all item-related business logic.
    """

    def __init__(self, repository: ItemRepository):
        self.repository = repository

    def create(self, title: str, content: str, owner_id: str, metadata: Optional[dict] = None) -> Item:
        """
        Create a new item.

        Args:
            title: Item title
            content: Item content
            owner_id: Owner user ID
            metadata: Optional metadata

        Returns:
            Created item

        Raises:
            ItemValidationError: If validation fails
        """
        logger.info("Creating item", extra={"title": title, "owner_id": owner_id})

        # Validation
        if not title or not title.strip():
            raise ItemValidationError(message="Title is required")

        if not content:
            raise ItemValidationError(message="Content is required")

        # Create item
        item = Item(
            title=title.strip(),
            content=content,
            owner_id=owner_id,
            metadata=metadata
        )

        # Save
        saved_item = self.repository.save(item)
        logger.info("Item created", extra={"item_id": saved_item.id})

        return saved_item

    def get(self, item_id: str) -> Item:
        """
        Get item by ID.

        Args:
            item_id: Item identifier

        Returns:
            Item

        Raises:
            ItemNotFoundError: If item not found
        """
        logger.debug("Getting item", extra={"item_id": item_id})

        item = self.repository.find_by_id(item_id)
        if not item:
            raise ItemNotFoundError(context={"item_id": item_id})

        return item

    def list(self, owner_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Item]:
        """
        List items.

        Args:
            owner_id: Filter by owner (optional)
            limit: Max results
            offset: Skip results

        Returns:
            List of items
        """
        logger.debug("Listing items", extra={"owner_id": owner_id, "limit": limit, "offset": offset})

        if owner_id:
            return self.repository.find_by_owner(owner_id)

        return self.repository.find_all(limit=limit, offset=offset)

    def update(self, item_id: str, title: Optional[str] = None, content: Optional[str] = None, metadata: Optional[dict] = None) -> Item:
        """
        Update an item.

        Args:
            item_id: Item to update
            title: New title (optional)
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            Updated item

        Raises:
            ItemNotFoundError: If item not found
            ItemValidationError: If validation fails
        """
        logger.info("Updating item", extra={"item_id": item_id})

        # Get existing
        item = self.get(item_id)

        # Update fields
        if title is not None:
            if not title.strip():
                raise ItemValidationError(message="Title cannot be empty")
            item.title = title.strip()

        if content is not None:
            item.content = content

        if metadata is not None:
            item.metadata = metadata

        item.updated_at = datetime.utcnow()

        # Save
        updated_item = self.repository.update(item)
        logger.info("Item updated", extra={"item_id": item_id})

        return updated_item

    def delete(self, item_id: str) -> bool:
        """
        Delete an item.

        Args:
            item_id: Item to delete

        Returns:
            True if deleted

        Raises:
            ItemNotFoundError: If item not found
        """
        logger.info("Deleting item", extra={"item_id": item_id})

        # Verify exists
        self.get(item_id)

        # Delete
        result = self.repository.delete(item_id)
        logger.info("Item deleted", extra={"item_id": item_id})

        return result
