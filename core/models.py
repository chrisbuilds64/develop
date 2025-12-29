"""
Database models for Tweight.

Currently: Video model for YouTube link management (UC-001)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from database import Base


class Video(Base):
    """
    Video model - stores YouTube links with tags.

    Simple approach for UC-001:
    - Tags stored as comma-separated string (normalize later if needed)
    - Title and thumbnail optional (can be fetched from YouTube)
    """
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)  # Fetched from YouTube (optional)
    thumbnail_url = Column(String, nullable=True)  # YouTube thumbnail
    tags = Column(String, nullable=True)  # Comma-separated: "workout,triceps,cable"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Video(id={self.id}, url={self.url}, tags={self.tags})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "thumbnail_url": self.thumbnail_url,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
