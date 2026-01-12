"""
Item Models
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Item:
    """
    Core Item entity.

    Attributes:
        id: UUID
        owner_id: User who owns this item
        label: Display name for lists
        content_type: MIME-like type (e.g., "media/youtube", "app/address")
        payload: Type-specific data as dict
        tags: Simple tag list
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft-delete timestamp
    """
    owner_id: str
    label: str
    content_type: str = "text/plain"
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    id: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    def is_deleted(self) -> bool:
        """Check if item is soft-deleted"""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark item as deleted"""
        self.deleted_at = datetime.utcnow()
