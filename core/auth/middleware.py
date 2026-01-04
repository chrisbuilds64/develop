"""
Authentication middleware for FastAPI.

Provides get_current_user dependency that:
1. Extracts JWT from Authorization header
2. Verifies token using AuthProvider
3. Gets or creates User in database
4. Returns User object for use in endpoints

Usage in endpoints:
    @app.get("/videos")
    def list_videos(user: User = Depends(get_current_user)):
        # user is authenticated User object
        videos = db.query(Video).filter(Video.user_id == user.id).all()
        ...
"""

import os
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth.base import AuthProvider, AuthenticationError
from auth.clerk_adapter import ClerkAdapter
from auth.mock_adapter import MockAuthAdapter


# Initialize auth provider based on environment
def get_auth_provider() -> AuthProvider:
    """
    Get authentication provider based on environment.

    Returns:
        - MockAuthAdapter if ENV=development or ENV=test
        - ClerkAdapter for production

    This allows local development without Clerk account.
    """
    env = os.getenv("ENV", "production").lower()

    if env in ["development", "test", "local"]:
        return MockAuthAdapter()
    else:
        return ClerkAdapter()


# Global auth provider instance
auth_provider = get_auth_provider()


def get_or_create_user(db: Session, provider_user_id: str, email: str, name: str) -> User:
    """
    Get existing user or create new one from auth provider data.

    Called on first API request after user signs in.
    Syncs user data from auth provider to our database.

    Args:
        db: Database session
        provider_user_id: Unique user ID from auth provider (Clerk/Mock)
        email: User's email
        name: User's display name

    Returns:
        User object (existing or newly created)
    """
    # Try to find existing user by provider_user_id
    user = db.query(User).filter(User.provider_user_id == provider_user_id).first()

    if user:
        # User exists - update email/name if changed
        if user.email != email or user.name != name:
            user.email = email
            user.name = name
            db.commit()
            db.refresh(user)
        return user

    # First time user - create in our DB
    user = User(
        provider_user_id=provider_user_id,
        email=email,
        name=name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_current_user(
    authorization: str = Header(..., description="Bearer token from auth provider"),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency: Extract and verify user from JWT.

    This is the main authentication dependency used by protected endpoints.

    Usage:
        @app.get("/videos")
        def list_videos(user: User = Depends(get_current_user)):
            # user is authenticated User object
            videos = db.query(Video).filter(Video.user_id == user.id).all()
            ...

    Args:
        authorization: Authorization header (e.g., "Bearer eyJhbGc...")
        db: Database session (injected by FastAPI)

    Returns:
        Authenticated User object

    Raises:
        HTTPException 401: If authentication fails
            - Missing Authorization header
            - Invalid token format
            - Token verification failed
            - User data invalid
    """
    # Check Authorization header format
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected format: 'Bearer <token>'"
        )

    # Extract token (remove "Bearer " prefix)
    token = authorization.replace("Bearer ", "")

    try:
        # Verify token with auth provider (Clerk/Mock)
        user_info = auth_provider.verify_token(token)

        # Extract user data
        provider_user_id = user_info.get("user_id")
        email = user_info.get("email")
        name = user_info.get("name", "")

        # Validate required fields
        if not provider_user_id or not email:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload: missing user_id or email"
            )

        # Get or create user in our database
        user = get_or_create_user(db, provider_user_id, email, name)

        return user

    except AuthenticationError as e:
        # Auth provider rejected token
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )


def get_current_user_optional(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Optional authentication dependency.

    Returns User if token provided and valid, None otherwise.
    Useful for endpoints that work for both authenticated and unauthenticated users.

    Usage:
        @app.get("/public-videos")
        def list_public_videos(user: User | None = Depends(get_current_user_optional)):
            if user:
                # Authenticated - show user's private videos
                ...
            else:
                # Unauthenticated - show only public videos
                ...
    """
    if not authorization:
        return None

    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None
