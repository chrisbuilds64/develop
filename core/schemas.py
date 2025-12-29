"""
Pydantic schemas for request/response validation.

Separates API contracts from database models.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, field_validator


class VideoCreate(BaseModel):
    """Schema for creating a new video."""
    url: str
    tags: Optional[List[str]] = None

    @field_validator('url')
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Validate that URL is a YouTube link."""
        if not ("youtube.com" in v or "youtu.be" in v):
            raise ValueError("URL must be a YouTube link")
        return v


class VideoResponse(BaseModel):
    """Schema for video response."""
    id: int
    url: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated string
    created_at: datetime

    class Config:
        from_attributes = True  # Allows creation from ORM model


class VideosListResponse(BaseModel):
    """Schema for list of videos."""
    videos: List[VideoResponse]
    count: int
