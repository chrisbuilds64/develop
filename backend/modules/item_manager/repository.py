"""
Item Repository

Database-Interface für Items.
"""
from typing import Optional, List

from adapters.database.base import DatabaseAdapter
from .models import Item


class ItemRepository:
    """
    Repository für Item-Persistenz.

    Nutzt DatabaseAdapter für tatsächliche DB-Operationen.
    """

    def __init__(self, adapter: DatabaseAdapter):
        self.adapter = adapter

    def save(self, item: Item) -> Item:
        """Save item"""
        return self.adapter.save(item)

    def find_by_id(self, item_id: str) -> Optional[Item]:
        """Find item by ID"""
        return self.adapter.find_by_id(item_id)

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Item]:
        """Find all items"""
        return self.adapter.find_all(limit=limit, offset=offset)

    def find_by_owner(self, owner_id: str) -> List[Item]:
        """Find items by owner"""
        return self.adapter.find_by(owner_id=owner_id)

    def update(self, item: Item) -> Item:
        """Update item"""
        return self.adapter.update(item)

    def delete(self, item_id: str) -> bool:
        """Delete item"""
        return self.adapter.delete(item_id)
