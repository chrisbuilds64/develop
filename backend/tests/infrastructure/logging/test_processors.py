"""
Unit tests for logging processors
"""
import pytest
from infrastructure.logging.processors import (
    mask_sensitive_data,
    _mask_email,
    _looks_like_token,
    censor_sql_passwords,
    add_app_context,
)


class TestMaskSensitiveData:
    """Test sensitive data masking processor"""

    def test_password_masking(self):
        """Test that password fields are completely masked"""
        event_dict = {
            "username": "chris",
            "password": "super_secret_123",
            "event": "user_login"
        }

        result = mask_sensitive_data(None, None, event_dict)

        assert result["password"] == "***REDACTED***"
        assert result["username"] == "chris"  # Not masked

    def test_token_masking(self):
        """Test that token fields are completely masked"""
        event_dict = {
            "api_key": "sk_live_abc123",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "event": "api_call"
        }

        result = mask_sensitive_data(None, None, event_dict)

        assert result["api_key"] == "***REDACTED***"
        assert result["access_token"] == "***REDACTED***"

    def test_email_partial_masking(self):
        """Test that email is partially masked"""
        event_dict = {
            "email": "chris@example.com",
            "event": "user_created"
        }

        result = mask_sensitive_data(None, None, event_dict)

        assert result["email"].startswith("c***@")
        assert "@example.com" in result["email"]

    def test_long_token_detection(self):
        """Test detection of token-like strings"""
        long_token = "abc123def456ghi789jkl012mno345pqr678stu901vwx234"

        event_dict = {
            "auth_header": f"Bearer {long_token}",
            "event": "request"
        }

        result = mask_sensitive_data(None, None, event_dict)

        # Should be partially masked (first4...last4)
        assert "abc1..." in result["auth_header"] or "***REDACTED***" in result["auth_header"]

    def test_safe_data_not_masked(self):
        """Test that safe data is not masked"""
        event_dict = {
            "order_id": 12345,
            "amount": 99.99,
            "status": "completed",
            "description": "Test order"
        }

        result = mask_sensitive_data(None, None, event_dict)

        assert result["order_id"] == 12345
        assert result["amount"] == 99.99
        assert result["status"] == "completed"
        assert result["description"] == "Test order"


class TestEmailMasking:
    """Test email masking helper function"""

    def test_standard_email(self):
        """Test standard email masking"""
        result = _mask_email("chris@example.com")
        assert result.startswith("c***@")
        assert result.endswith("example.com")

    def test_single_char_email(self):
        """Test email with single character local part"""
        result = _mask_email("a@example.com")
        assert result.startswith("***@")

    def test_invalid_email(self):
        """Test invalid email format"""
        result = _mask_email("not-an-email")
        assert result == "not-an-email"  # No @ sign, unchanged


class TestTokenDetection:
    """Test token-like string detection"""

    def test_long_alphanumeric_detected(self):
        """Test that long alphanumeric strings are detected"""
        token = "abc123def456ghi789jkl012mno345pqr678stu901vwx234"
        assert _looks_like_token(token) is True

    def test_short_string_not_detected(self):
        """Test that short strings are not detected"""
        short = "abc123"
        assert _looks_like_token(short) is False

    def test_string_with_spaces_not_detected(self):
        """Test that strings with spaces are not detected"""
        with_spaces = "abc 123 def 456 ghi 789 jkl 012"
        assert _looks_like_token(with_spaces) is False

    def test_only_letters_not_detected(self):
        """Test that only letters is not detected"""
        only_letters = "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"
        assert _looks_like_token(only_letters) is False

    def test_only_numbers_not_detected(self):
        """Test that only numbers is not detected"""
        only_numbers = "12345678901234567890123456789012345678901234567890"
        assert _looks_like_token(only_numbers) is False


class TestSQLPasswordCensoring:
    """Test SQL connection string password censoring"""

    def test_postgresql_url(self):
        """Test PostgreSQL URL password censoring"""
        event_dict = {
            "url": "postgresql://admin:secret_password@localhost:5432/mydb"
        }

        result = censor_sql_passwords(None, None, event_dict)

        assert "secret_password" not in result["url"]
        assert "postgresql://admin:***@localhost:5432/mydb" == result["url"]

    def test_mysql_url(self):
        """Test MySQL URL password censoring"""
        event_dict = {
            "url": "mysql://root:mysql_pass@localhost/db"
        }

        result = censor_sql_passwords(None, None, event_dict)

        assert "mysql_pass" not in result["url"]
        assert "***" in result["url"]

    def test_non_sql_url_unchanged(self):
        """Test that non-SQL URLs are unchanged"""
        event_dict = {
            "url": "https://example.com/api/data"
        }

        result = censor_sql_passwords(None, None, event_dict)

        assert result["url"] == "https://example.com/api/data"


class TestAppContext:
    """Test application context processor"""

    def test_app_name_added(self):
        """Test that app_name is added"""
        event_dict = {"event": "test"}

        result = add_app_context(None, None, event_dict)

        assert "app_name" in result
        assert result["app_name"] == "chrisbuilds64-api"

    def test_environment_added(self):
        """Test that environment is added"""
        event_dict = {"event": "test"}

        result = add_app_context(None, None, event_dict)

        assert "environment" in result
        assert result["environment"] in ["development", "production"]

    def test_existing_values_not_overwritten(self):
        """Test that existing values are not overwritten"""
        event_dict = {
            "event": "test",
            "app_name": "custom-app",
            "environment": "staging"
        }

        result = add_app_context(None, None, event_dict)

        assert result["app_name"] == "custom-app"
        assert result["environment"] == "staging"
