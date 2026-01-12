"""
Item Models

Datenmodelle für Items.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Item:
    """
    Item entity.

    Attributes:
        id: Unique identifier
        title: Item title
        content: Item content/body
        owner_id: User who owns this item
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata
    """
    title: str
    content: str
    owner_id: str
    id: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Optional[dict] = None
