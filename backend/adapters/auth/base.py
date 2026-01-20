"""
Auth Adapter Interface

Abstract base for all authentication providers.
Compliant with REQ-000 Infrastructure Standards.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserInfo:
    """
    User identity from auth provider.

    Standardized representation across all providers.
    """
    user_id: str
    email: str
    name: str


class AuthProvider(ABC):
    """
    Abstract base class for auth providers.

    Implementations: MockAuthAdapter, ClerkAdapter, (future: SuperTokens)
    """

    @abstractmethod
    def verify_token(self, token: str) -> UserInfo:
        """
        Verify token and extract user identity.

        Args:
            token: JWT or session token (without "Bearer " prefix)

        Returns:
            UserInfo with user_id, email, name

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        pass
