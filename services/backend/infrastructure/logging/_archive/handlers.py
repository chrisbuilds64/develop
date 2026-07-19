"""
Log Handlers

Console, File, Remote (für später).
"""
import logging
from typing import Optional


class FileHandler(logging.FileHandler):
    """
    File Handler mit Rotation.

    Für später: Log-Rotation, Compression, etc.
    """

    def __init__(self, filename: str, max_bytes: int = 10_000_000, backup_count: int = 5):
        super().__init__(filename)
        self.max_bytes = max_bytes
        self.backup_count = backup_count


class RemoteHandler(logging.Handler):
    """
    Remote Handler für ELK/Datadog/etc.

    Placeholder für später.
    """

    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        super().__init__()
        self.endpoint = endpoint
        self.api_key = api_key

    def emit(self, record: logging.LogRecord):
        """Send log to remote endpoint"""
        # TODO: Implement when needed
        pass
