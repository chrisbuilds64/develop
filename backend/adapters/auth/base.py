"""
Auth Adapter Interface

Basis-Interface für alle Auth-Provider.
"""
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class User:
    """User representation from auth provider"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class Session:
    """Session representation"""
    id: str
    user_id: str
    expires_at: Optional[str] = None


class AuthAdapter(ABC):
    """
    Abstract base class for auth adapters.

    Implementierungen: Clerk, SuperTokens, Mock
    """

    @abstractmethod
    def authenticate(self, token: str) -> Optional[User]:
        """
        Validate token and return user if valid.

        Args:
            token: Auth token (JWT, session token, etc.)

        Returns:
            User if valid, None if invalid
        """
        pass

    @abstractmethod
    def create_session(self, user_id: str) -> Session:
        """
        Create a new session for user.

        Args:
            user_id: User identifier

        Returns:
            New session
        """
        pass

    @abstractmethod
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate/logout a session.

        Args:
            session_id: Session to invalidate

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User if found, None otherwise
        """
        pass
