"""
Shared Types

Gemeinsame Typen für Module (falls benötigt).
"""
from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class PagedResult(Generic[T]):
    """Paginated result wrapper"""
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
