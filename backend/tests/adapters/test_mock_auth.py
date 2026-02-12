"""
MockAuthAdapter unit tests.
"""
import pytest
from adapters.auth.mock_adapter import MockAuthAdapter, TEST_USERS
from adapters.auth.exceptions import AuthenticationError


class TestMockAuthAdapter:

    @pytest.fixture
    def auth(self):
        return MockAuthAdapter()

    def test_chris_token(self, auth):
        user = auth.verify_token("test-chris")
        assert user.user_id == TEST_USERS["chris"].user_id

    def test_lars_token(self, auth):
        user = auth.verify_token("test-lars")
        assert user.user_id == TEST_USERS["lars"].user_id

    def test_lily_token(self, auth):
        user = auth.verify_token("test-lily")
        assert user.user_id == TEST_USERS["lily"].user_id

    def test_generic_token_defaults_to_chris(self, auth):
        user = auth.verify_token("some-random-token")
        assert user.user_id == TEST_USERS["chris"].user_id

    def test_empty_token_raises(self, auth):
        with pytest.raises(AuthenticationError):
            auth.verify_token("")

    def test_invalid_token_raises(self, auth):
        with pytest.raises(AuthenticationError):
            auth.verify_token("invalid")
