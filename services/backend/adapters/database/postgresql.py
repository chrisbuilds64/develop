"""
PostgreSQL Database Adapter

Implementiert DatabaseAdapter Interface mit SQLAlchemy.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from .base import DatabaseAdapter
from .models import ItemModel
from modules.item_manager.models import Item


class PostgreSQLAdapter(DatabaseAdapter[Item]):
    """
    PostgreSQL implementation using SQLAlchemy.

    Converts between domain models (Item) and ORM models (ItemModel).
    """

    def __init__(self, session: Session):
        """
        Initialize with SQLAlchemy session.

        Args:
            session: SQLAlchemy session (injected)
        """
        self.session = session

    def save(self, entity: Item) -> Item:
        """
        Save Item to PostgreSQL.

        Args:
            entity: Domain model Item

        Returns:
            Saved Item with ID
        """
        # Generate ID if needed
        if not entity.id:
            entity.id = str(uuid.uuid4())

        # Convert domain model to ORM model
        db_item = ItemModel(
            id=entity.id,
            owner_id=entity.owner_id,
            label=entity.label,
            content_type=entity.content_type,
            payload=entity.payload,
            tags=entity.tags,
            created_at=entity.created_at or datetime.utcnow(),
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at
        )

        self.session.add(db_item)
        self.session.flush()  # Get ID without committing

        return entity

    def find_by_id(self, entity_id: str) -> Optional[Item]:
        """
        Find Item by ID.

        Args:
            entity_id: Item UUID

        Returns:
            Item if found, None otherwise
        """
        db_item = self.session.query(ItemModel).filter(
            ItemModel.id == entity_id
        ).first()

        if not db_item:
            return None

        return self._to_domain(db_item)

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Item]:
        """
        Find all Items with pagination.

        Args:
            limit: Max results
            offset: Skip results

        Returns:
            List of Items
        """
        db_items = self.session.query(ItemModel).offset(offset).limit(limit).all()
        return [self._to_domain(item) for item in db_items]

    def update(self, entity: Item) -> Item:
        """
        Update existing Item.

        Args:
            entity: Item with updated values

        Returns:
            Updated Item
        """
        db_item = self.session.query(ItemModel).filter(
            ItemModel.id == entity.id
        ).first()

        if not db_item:
            raise ValueError(f"Item not found: {entity.id}")

        # Update fields
        db_item.owner_id = entity.owner_id
        db_item.label = entity.label
        db_item.content_type = entity.content_type
        db_item.payload = entity.payload
        db_item.tags = entity.tags
        db_item.updated_at = datetime.utcnow()
        db_item.deleted_at = entity.deleted_at

        self.session.flush()

        return entity

    def delete(self, entity_id: str) -> bool:
        """
        Hard delete Item from database.

        Args:
            entity_id: Item UUID

        Returns:
            True if deleted
        """
        result = self.session.query(ItemModel).filter(
            ItemModel.id == entity_id
        ).delete()

        return result > 0

    def find_by(self, **criteria) -> List[Item]:
        """
        Find Items by criteria.

        Supported criteria:
            - owner_id: str
            - content_type: str
            - tags: List[str] (any match)
            - search: str (case-insensitive label search)
            - include_deleted: bool

        Args:
            **criteria: Field=value pairs

        Returns:
            List of matching Items
        """
        query = self.session.query(ItemModel)

        # Filter by owner_id
        if "owner_id" in criteria:
            query = query.filter(ItemModel.owner_id == criteria["owner_id"])

        # Filter by content_type
        if "content_type" in criteria:
            query = query.filter(ItemModel.content_type == criteria["content_type"])

        # Exclude soft-deleted by default
        if not criteria.get("include_deleted", False):
            query = query.filter(ItemModel.deleted_at.is_(None))

        # Filter by tags (any match)
        if "tags" in criteria and criteria["tags"]:
            # PostgreSQL JSON contains operator
            # Check if any tag in criteria matches any tag in JSON array
            from sqlalchemy import cast, String
            for tag in criteria["tags"]:
                # Cast JSON to string and check if tag exists
                query = query.filter(
                    cast(ItemModel.tags, String).like(f'%"{tag}"%')
                )

        # Search by label (case-insensitive)
        if "search" in criteria and criteria["search"]:
            search_term = criteria["search"]
            query = query.filter(ItemModel.label.ilike(f"%{search_term}%"))

        # Sort by created_at descending
        query = query.order_by(ItemModel.created_at.desc())

        # Execute query
        db_items = query.all()
        return [self._to_domain(item) for item in db_items]

    def _to_domain(self, db_item: ItemModel) -> Item:
        """
        Convert ORM model to domain model.

        Args:
            db_item: SQLAlchemy ItemModel

        Returns:
            Domain Item
        """
        return Item(
            id=db_item.id,
            owner_id=db_item.owner_id,
            label=db_item.label,
            content_type=db_item.content_type,
            payload=db_item.payload,
            tags=db_item.tags,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            deleted_at=db_item.deleted_at
        )
