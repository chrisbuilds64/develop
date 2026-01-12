"""
Logger Factory

Erzeugt konfigurierte Logger pro Komponente.
"""
import logging
import sys
from typing import Optional

from .formatters import JSONFormatter, HumanFormatter


# Cache für Logger
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger for the given name.

    Args:
        name: Logger name (e.g., "item_manager", "api.routes.items")
        level: Optional log level override

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    # Neuen Logger erstellen
    logger = logging.getLogger(name)

    # Level setzen (default: INFO)
    log_level = level or _get_default_level()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Handler nur einmal hinzufügen
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_get_formatter())
        logger.addHandler(handler)

    # Cachen
    _loggers[name] = logger

    return logger


def _get_default_level() -> str:
    """Get default log level from config"""
    import os
    return os.getenv("LOG_LEVEL", "INFO")


def _get_formatter() -> logging.Formatter:
    """Get formatter based on config"""
    import os
    log_format = os.getenv("LOG_FORMAT", "json")

    if log_format == "human":
        return HumanFormatter()
    return JSONFormatter()
