"""
Clerk authentication adapter.

Implements AuthProvider interface using Clerk as the backend.
Handles JWT verification using Clerk's SDK.

Setup:
    1. Set CLERK_SECRET_KEY environment variable
    2. Get key from: https://dashboard.clerk.com/

Usage:
    adapter = ClerkAdapter()
    user_info = adapter.verify_token(jwt_token)
"""

import os
from typing import Dict
from auth.base import AuthProvider, AuthenticationError


class ClerkAdapter(AuthProvider):
    """
    Clerk authentication adapter.

    Uses Clerk's JWT verification to validate tokens.
    Extracts user information from verified JWT payload.
    """

    def __init__(self):
        """
        Initialize Clerk adapter.

        Requires:
            CLERK_SECRET_KEY environment variable
        """
        self.secret_key = os.getenv("CLERK_SECRET_KEY")

        if not self.secret_key:
            raise ValueError(
                "CLERK_SECRET_KEY environment variable not set. "
                "Get it from https://dashboard.clerk.com/"
            )

    def verify_token(self, token: str) -> Dict[str, str]:
        """
        Verify Clerk JWT token.

        Args:
            token: JWT token string (without "Bearer " prefix)

        Returns:
            {
                'user_id': str,  # Clerk user ID (e.g., "user_2abc123...")
                'email': str,    # User's email
                'name': str      # User's display name
            }

        Raises:
            AuthenticationError: If token is invalid or verification fails
        """
        try:
            # Import here to avoid dependency when using MockAdapter
            from clerk_backend_api import Clerk

            # Initialize Clerk client
            clerk = Clerk(bearer_auth=self.secret_key)

            # Verify JWT token
            # Clerk SDK will raise exception if token is invalid/expired
            session = clerk.sessions.verify_session(token)

            # Extract user info from session
            user_id = session.user_id

            # Get user details
            user = clerk.users.get(user_id)

            return {
                'user_id': user_id,
                'email': user.email_addresses[0].email_address if user.email_addresses else '',
                'name': f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or ''
            }

        except ImportError:
            raise AuthenticationError(
                "clerk-backend-api package not installed. "
                "Run: pip install clerk-backend-api"
            )
        except Exception as e:
            # Wrap all Clerk errors in our generic AuthenticationError
            raise AuthenticationError(f"Clerk token verification failed: {str(e)}")
