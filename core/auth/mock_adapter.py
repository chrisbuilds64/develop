"""
Mock authentication adapter for testing and local development.

Allows development without Clerk account or internet connection.
Accepts any token starting with "test-" or "mock-".

Usage:
    # In main.py for local dev
    if os.getenv("ENV") == "development":
        auth_provider = MockAuthAdapter()

    # In tests
    adapter = MockAuthAdapter()
    user_info = adapter.verify_token("test-123")
"""

from typing import Dict
from auth.base import AuthProvider, AuthenticationError


class MockAuthAdapter(AuthProvider):
    """
    Mock authentication adapter for testing.

    Accepts tokens starting with "test-" or "mock-".
    Returns hardcoded user info for testing.

    Security: NEVER use in production!
    """

    def __init__(self):
        """Initialize mock adapter with default test user."""
        self.test_user = {
            'user_id': 'mock-user-chris-123',
            'email': 'chris@test.com',
            'name': 'Chris (Mock)'
        }

    def verify_token(self, token: str) -> Dict[str, str]:
        """
        Verify mock token (accepts "test-*" or "mock-*").

        Args:
            token: Token string (should start with "test-" or "mock-")

        Returns:
            Hardcoded test user info

        Raises:
            AuthenticationError: If token doesn't start with "test-" or "mock-"

        Examples:
            >>> adapter = MockAuthAdapter()
            >>> adapter.verify_token("test-123")
            {'user_id': 'mock-user-chris-123', 'email': 'chris@test.com', ...}

            >>> adapter.verify_token("invalid")
            AuthenticationError: Invalid mock token
        """
        # Accept any token starting with test- or mock-
        if not (token.startswith("test-") or token.startswith("mock-")):
            raise AuthenticationError(
                "Invalid mock token. Use 'test-*' or 'mock-*' for local development."
            )

        # You can extract user ID from token for different test users
        # Example: "test-user-lars" → different user
        if "lars" in token.lower():
            return {
                'user_id': 'mock-user-lars-456',
                'email': 'lars@test.com',
                'name': 'Lars (Mock)'
            }
        elif "lily" in token.lower():
            return {
                'user_id': 'mock-user-lily-789',
                'email': 'lily@test.com',
                'name': 'Lily (Mock)'
            }

        # Default test user (Chris)
        return self.test_user.copy()

    def set_test_user(self, user_id: str, email: str, name: str):
        """
        Override test user for specific tests.

        Useful in unit tests when you need specific user data.

        Example:
            >>> adapter = MockAuthAdapter()
            >>> adapter.set_test_user('test-123', 'test@example.com', 'Test User')
            >>> user_info = adapter.verify_token("test-token")
            >>> assert user_info['email'] == 'test@example.com'
        """
        self.test_user = {
            'user_id': user_id,
            'email': email,
            'name': name
        }
