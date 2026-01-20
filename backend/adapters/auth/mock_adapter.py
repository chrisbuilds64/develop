"""
Mock Auth Adapter

For testing and development without external auth services.
Compliant with REQ-000 Infrastructure Standards.
"""
from infrastructure.logging import get_logger
from .base import AuthProvider, UserInfo
from .exceptions import AuthenticationError

logger = get_logger()


# Test users as defined in REQ-001
TEST_USERS = {
    "chris": UserInfo(
        user_id="mock-user-chris-123",
        email="chris@test.com",
        name="Chris (Mock)"
    ),
    "lars": UserInfo(
        user_id="mock-user-lars-456",
        email="lars@test.com",
        name="Lars (Mock)"
    ),
    "lily": UserInfo(
        user_id="mock-user-lily-789",
        email="lily@test.com",
        name="Lily (Mock)"
    ),
}

# Default user for generic test tokens
DEFAULT_USER = TEST_USERS["chris"]


class MockAuthAdapter(AuthProvider):
    """
    Mock implementation for testing.

    Accepts tokens in format:
    - "test-chris", "test-lars", "test-lily" → specific user
    - "test-*", "mock-*" → default user (chris)
    - Any other non-empty token → default user (for simple testing)

    Rejects:
    - Empty tokens
    - "invalid" token (explicit rejection for testing)
    """

    def verify_token(self, token: str) -> UserInfo:
        """
        Verify mock token and return test user.

        Args:
            token: Test token (e.g., "test-chris")

        Returns:
            UserInfo for test user

        Raises:
            AuthenticationError: If token is empty or "invalid"
        """
        logger.debug("mock_auth_verify", token_prefix=token[:10] if token else None)

        # Reject empty or explicit invalid tokens
        if not token:
            logger.warning("mock_auth_failed", reason="empty_token")
            raise AuthenticationError(
                message="Token is required",
                context={"reason": "empty_token"}
            )

        if token == "invalid":
            logger.warning("mock_auth_failed", reason="explicit_invalid")
            raise AuthenticationError(
                message="Invalid token",
                context={"reason": "explicit_invalid"}
            )

        # Check for specific user tokens
        token_lower = token.lower()
        for user_key, user_info in TEST_USERS.items():
            if user_key in token_lower:
                logger.info("mock_auth_success", user_id=user_info.user_id)
                return user_info

        # Default to chris for any other valid token
        logger.info("mock_auth_success", user_id=DEFAULT_USER.user_id, default=True)
        return DEFAULT_USER
