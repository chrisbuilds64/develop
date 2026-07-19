"""
Test sensitive data masking processors
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.logging import setup_logging, get_logger


def test_password_masking():
    """Test password field masking"""
    print("\n" + "="*60)
    print("TEST: Password Masking")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    # These should be masked
    logger.info("user_login",
                username="chris",
                password="super_secret_123",  # Should be ***REDACTED***
                api_key="sk_live_abc123def456")  # Should be ***REDACTED***

    logger.info("database_connection",
                host="localhost",
                db_password="db_secret_pass")  # Should be ***REDACTED***

    print("\n✅ Check that password and api_key are masked\n")


def test_token_masking():
    """Test token-like string detection"""
    print("\n" + "="*60)
    print("TEST: Token-like String Detection")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    # Long alphanumeric string (looks like token)
    long_token = "abc123def456ghi789jkl012mno345pqr678stu901vwx234"

    logger.info("api_call",
                endpoint="/api/data",
                auth_header=f"Bearer {long_token}")  # Should detect and mask

    print("\n✅ Check that long token is partially masked\n")


def test_email_masking():
    """Test email address masking"""
    print("\n" + "="*60)
    print("TEST: Email Masking")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    logger.info("user_created",
                user_id=123,
                email="chris@example.com")  # Should be c***@example.com

    print("\n✅ Check that email is partially masked\n")


def test_sql_url_censoring():
    """Test SQL connection string censoring"""
    print("\n" + "="*60)
    print("TEST: SQL Connection String Censoring")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    logger.info("database_connected",
                url="postgresql://admin:secret_password@localhost:5432/mydb")
    # Should be: postgresql://admin:***@localhost:5432/mydb

    print("\n✅ Check that password in URL is censored\n")


def test_safe_logging():
    """Test that safe data is NOT masked"""
    print("\n" + "="*60)
    print("TEST: Safe Data (Should NOT be masked)")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    logger.info("order_created",
                order_id=12345,
                amount=99.99,
                currency="USD",
                status="completed",
                description="This is a safe description")

    print("\n✅ Check that normal data is NOT masked\n")


def test_app_context():
    """Test app_name and environment added automatically"""
    print("\n" + "="*60)
    print("TEST: App Context (app_name, environment)")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    logger.info("test_event", message="Check for app_name and environment")

    print("\n✅ Check that app_name and environment are added\n")


if __name__ == "__main__":
    test_password_masking()
    test_token_masking()
    test_email_masking()
    test_sql_url_censoring()
    test_safe_logging()
    test_app_context()

    print("="*60)
    print("✅ ALL PROCESSOR TESTS COMPLETED")
    print("="*60)
    print("\nVerify in output above:")
    print("1. Passwords are ***REDACTED***")
    print("2. Long tokens are partially masked (first4...last4)")
    print("3. Emails are partially masked (u***@example.com)")
    print("4. SQL URLs have password censored (user:***@host)")
    print("5. Normal data is NOT masked")
    print("6. app_name and environment are added to all logs")
    print("\n")
