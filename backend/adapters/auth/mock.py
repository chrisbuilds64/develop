"""
Mock Auth Adapter

Für Tests und Entwicklung.
"""
from typing import Optional
import uuid

from .base import AuthAdapter, User, Session


class MockAuthAdapter(AuthAdapter):
    """
    Mock implementation for testing.

    Akzeptiert jeden Token und gibt Test-User zurück.
    """

    def __init__(self):
        self._users: dict[str, User] = {
            "test-user-1": User(
                id="test-user-1",
                email="test@example.com",
                name="Test User"
            )
        }
        self._sessions: dict[str, Session] = {}

    def authenticate(self, token: str) -> Optional[User]:
        """Accept any non-empty token"""
        if not token or token == "invalid":
            return None
        return self._users.get("test-user-1")

    def create_session(self, user_id: str) -> Session:
        """Create mock session"""
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id
        )
        self._sessions[session.id] = session
        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Remove session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_user(self, user_id: str) -> Optional[User]:
        """Get mock user"""
        return self._users.get(user_id)
