"""Login handler for Clerk authentication via backend proxy."""

from typing import Dict, Any
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
import os


class ClerkLoginHandler:
    """Handles login requests by communicating with Clerk."""

    def __init__(self):
        self.clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in user with email and password via Clerk.

        Returns dict with:
        - token: JWT session token
        - user: User info (id, email, name)

        Raises Exception if sign-in fails.
        """
        try:
            # For testing: Use mock tokens in development
            if os.getenv("ENV") == "development":
                return self._mock_sign_in(email, password)

            # Production: Use Clerk API
            # NOTE: Clerk's sign-in flow typically requires:
            # 1. Create a sign-in attempt
            # 2. Submit credentials
            # 3. Get session token

            # For now, we'll create a simplified version
            # In production, you might want to use Clerk's hosted sign-in

            raise NotImplementedError(
                "Clerk sign-in requires hosted authentication page. "
                "Use development mode with mock tokens for testing."
            )

        except Exception as e:
            raise Exception(f"Sign-in failed: {str(e)}")

    def _mock_sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Mock sign-in for development/testing."""
        # Map test emails to mock tokens
        mock_users = {
            "chris@chrisbuilds64.com": "test-chris",
            "lars@chrisbuilds64.com": "test-lars",
            "lily@chrisbuilds64.com": "test-lily",
        }

        if email not in mock_users:
            raise Exception("Invalid email")

        # In development, any password works for testing
        token = mock_users[email]

        return {
            "token": token,
            "user": {
                "id": token,
                "email": email,
                "name": email.split("@")[0].title(),
            }
        }
