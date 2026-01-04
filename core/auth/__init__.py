"""
Authentication module for Core.

Provides abstract authentication interface with adapters for:
- Clerk (production)
- Mock (testing/development)
- Future: Auth0, Supabase, etc.

Philosophy: Thin facade over external auth providers.
Core business logic doesn't know about specific providers.
"""

from auth.base import AuthProvider, AuthenticationError
from auth.clerk_adapter import ClerkAdapter
from auth.mock_adapter import MockAuthAdapter

__all__ = [
    'AuthProvider',
    'AuthenticationError',
    'ClerkAdapter',
    'MockAuthAdapter',
]
