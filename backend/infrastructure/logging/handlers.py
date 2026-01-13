"""
Logging Handlers Configuration

Async logging with QueueHandler and multiple output handlers.
"""
import sys
import logging
import os
from queue import Queue
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from typing import Optional, List

# Global queue listener (started once, stopped on shutdown)
_queue_listener: Optional[QueueListener] = None


def setup_async_handlers(
    environment: str = "production",
    log_level: str = "INFO",
    enable_file_logging: bool = True
) -> Optional[QueueListener]:
    """
    Setup async logging with QueueHandler pattern.

    Args:
        environment: "development" or "production"
        log_level: Logging level
        enable_file_logging: Whether to enable file logging (default: True)

    Returns:
        QueueListener instance (or None if already started)
    """
    global _queue_listener

    # Don't create multiple listeners
    if _queue_listener is not None:
        return None

    # Create handlers for I/O operations
    handlers: List[logging.Handler] = []

    # Console handler (stdout for Docker/Kubernetes)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    handlers.append(console_handler)

    # File handler (optional, for local debugging)
    if enable_file_logging:
        log_dir = os.getenv("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=f"{log_dir}/app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        handlers.append(file_handler)

    # Create queue for async logging
    log_queue: Queue = Queue(maxsize=1000)

    # Create queue handler (non-blocking)
    queue_handler = QueueHandler(log_queue)

    # Create queue listener (processes queue in background thread)
    _queue_listener = QueueListener(
        log_queue,
        *handlers,
        respect_handler_level=True
    )

    # Replace root logger handlers with queue handler
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(queue_handler)

    # Start listener
    _queue_listener.start()

    return _queue_listener


def stop_async_handlers() -> None:
    """
    Stop the queue listener (call on application shutdown).

    This ensures all queued log messages are processed before exit.
    """
    global _queue_listener

    if _queue_listener is not None:
        _queue_listener.stop()
        _queue_listener = None


def get_queue_listener() -> Optional[QueueListener]:
    """
    Get the current queue listener instance.

    Returns:
        QueueListener instance or None if not started
    """
    return _queue_listener
