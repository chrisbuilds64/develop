"""
SQLAlchemy Database Models

ORM Models für PostgreSQL/SQLite.
Getrennt von Domain Models (modules/*/models.py).
"""
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

from infrastructure.database_sqlalchemy import Base


class ItemModel(Base):
    """
    SQLAlchemy Model für Item Table.

    Maps to domain model: modules.item_manager.models.Item
    """
    __tablename__ = "items"

    # Primary Key
    id = Column(String, primary_key=True, index=True)

    # Core Fields
    owner_id = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    content_type = Column(String, nullable=False, default="text/plain", index=True)

    # Flexible Data
    payload = Column(JSON, nullable=False, default=dict)

    # Tags (PostgreSQL ARRAY or JSON for SQLite)
    tags = Column(JSON, nullable=False, default=list)  # JSON for cross-DB compatibility

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete

    def __repr__(self):
        return f"<ItemModel(id={self.id}, label={self.label}, owner={self.owner_id})>"
