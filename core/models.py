"""
Database models for Tweight Core.

Models:
- User: User account (synced from auth provider - Clerk, Mock, etc.)
- Video: YouTube link with tags (UC-001, now user-specific)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """
    User model - synced from authentication provider.

    We don't store passwords (handled by Clerk/Auth0/Mock).
    We only store: provider user_id, email, display name.

    The provider_user_id is unique ID from auth provider:
    - Clerk: "user_2abc123..."
    - Auth0: "auth0|123..."
    - Mock: "mock-user-chris-123"
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_user_id = Column(String, unique=True, nullable=False, index=True)  # From auth provider
    email = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, provider_id={self.provider_user_id})>"


class Video(Base):
    """
    Video model - stores YouTube links with tags (user-specific).

    UC-003 Update: Added user_id foreign key.
    Now videos belong to users, supporting multi-user system.
    """
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # UC-003: Added
    url = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)  # Fetched from YouTube (optional)
    thumbnail_url = Column(String, nullable=True)  # YouTube thumbnail
    tags = Column(String, nullable=True)  # Comma-separated: "workout,triceps,cable"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="videos")

    def __repr__(self):
        return f"<Video(id={self.id}, user_id={self.user_id}, url={self.url}, tags={self.tags})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "url": self.url,
            "title": self.title,
            "thumbnail_url": self.thumbnail_url,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
