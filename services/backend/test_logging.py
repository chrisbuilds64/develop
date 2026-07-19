"""
Test script for structlog configuration

Tests both production (JSON) and development (pretty console) modes.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.logging import setup_logging, get_logger


def test_production_mode():
    """Test production mode (JSON output)"""
    print("\n" + "="*60)
    print("TESTING PRODUCTION MODE (JSON)")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="DEBUG")
    logger = get_logger()

    # Test different log levels
    logger.debug("debug_message", key="debug_value")
    logger.info("info_message", key="info_value", number=42)
    logger.warning("warning_message", status="warning")
    logger.error("error_message", error_code="ERR_123")

    # Test with bound logger (persistent context)
    bound_logger = logger.bind(service="test", version="1.0")
    bound_logger.info("bound_logger_test", extra="data")

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("exception_test", error=str(e))

    print("\n")


def test_development_mode():
    """Test development mode (pretty console)"""
    print("\n" + "="*60)
    print("TESTING DEVELOPMENT MODE (PRETTY CONSOLE)")
    print("="*60 + "\n")

    setup_logging(environment="development", log_level="DEBUG")
    logger = get_logger()

    # Test different log levels
    logger.debug("debug_message", key="debug_value")
    logger.info("info_message", key="info_value", number=42)
    logger.warning("warning_message", status="warning")
    logger.error("error_message", error_code="ERR_123")

    # Test with bound logger (persistent context)
    bound_logger = logger.bind(service="test", version="1.0")
    bound_logger.info("bound_logger_test", extra="data")

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("exception_test", error=str(e))

    print("\n")


def test_context_variables():
    """Test context variables (request_id simulation)"""
    print("\n" + "="*60)
    print("TESTING CONTEXT VARIABLES")
    print("="*60 + "\n")

    setup_logging(environment="production", log_level="INFO")
    logger = get_logger()

    import structlog

    # Simulate request context
    structlog.contextvars.bind_contextvars(
        request_id="req-abc-123",
        user_id="user-456",
        endpoint="/api/items"
    )

    logger.info("request_started")
    logger.info("processing_item", item_id=789)
    logger.info("request_completed", duration_ms=45.2)

    # Clear context
    structlog.contextvars.clear_contextvars()

    logger.info("after_clear")  # Should not have request context

    print("\n")


if __name__ == "__main__":
    # Test production mode
    test_production_mode()

    # Test development mode
    test_development_mode()

    # Test context variables
    test_context_variables()

    print("="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
