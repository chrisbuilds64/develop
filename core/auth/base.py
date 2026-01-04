"""
Abstract base class for authentication providers.

Philosophy: Core defines the interface, adapters implement it.
This allows swapping auth providers without changing Core logic.
"""

from abc import ABC, abstractmethod
from typing import Dict


class AuthProvider(ABC):
    """
    Abstract authentication provider interface.

    All auth providers (Clerk, Auth0, Supabase, etc.) must implement this.
    Core code only depends on this interface, not specific implementations.
    """

    @abstractmethod
    def verify_token(self, token: str) -> Dict[str, str]:
        """
        Verify JWT token and extract user information.

        Args:
            token: JWT token string (without "Bearer " prefix)

        Returns:
            Dictionary with user info:
            {
                'user_id': str,    # Provider's unique user ID
                'email': str,      # User's email
                'name': str        # User's display name (can be empty)
            }

        Raises:
            AuthenticationError: If token is invalid, expired, or verification fails

        Example:
            >>> adapter = ClerkAdapter()
            >>> user_info = adapter.verify_token("eyJhbGciOiJ...")
            >>> print(user_info['email'])
            'chris@example.com'
        """
        pass


class AuthenticationError(Exception):
    """
    Raised when authentication fails.

    This is a generic error that wraps provider-specific errors.
    Core code catches this instead of provider-specific exceptions.
    """
    pass
