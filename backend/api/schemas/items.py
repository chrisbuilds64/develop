"""
Item API Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ItemCreate(BaseModel):
    """Request schema for creating an item"""
    label: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="text/plain", max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    """Request schema for updating an item"""
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    content_type: Optional[str] = Field(None, max_length=100)
    payload: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ItemResponse(BaseModel):
    """Response schema for a single item"""
    id: str
    owner_id: str
    label: str
    content_type: str
    payload: Dict[str, Any]
    tags: List[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    """Response schema for item list"""
    items: List[ItemResponse]
    total: int
    limit: int
    offset: int
