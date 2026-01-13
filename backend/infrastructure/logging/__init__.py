"""
Logging Infrastructure

Production-grade structured logging with structlog.

Usage:
    >>> from infrastructure.logging import setup_logging, get_logger
    >>>
    >>> # Setup once on application startup
    >>> setup_logging(environment="production")
    >>>
    >>> # Use anywhere
    >>> logger = get_logger()
    >>> logger.info("event_name", key="value", another_key=123)
"""
from .config import setup_logging, get_environment, get_log_level
from structlog import get_logger

__all__ = [
    "setup_logging",    # Call once on app startup
    "get_logger",       # Get logger instance anywhere
    "get_environment",  # Get current environment
    "get_log_level",    # Get current log level
]
