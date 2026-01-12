"""
Log Formatters

JSON für Production, Human-readable für Development.
"""
import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Strukturiertes JSON-Format für Production.

    Output:
    {
        "timestamp": "2026-01-12T10:30:00Z",
        "level": "INFO",
        "logger": "item_manager",
        "message": "Item created",
        "context": {"item_id": "123"}
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Extra fields hinzufügen (z.B. request_id, user_id)
        if hasattr(record, "extra"):
            log_data["context"] = record.extra
        elif record.__dict__.get("request_id"):
            # Fallback für direkt übergebene extras
            log_data["context"] = {
                k: v for k, v in record.__dict__.items()
                if k not in ["name", "msg", "args", "created", "filename",
                             "funcName", "levelname", "levelno", "lineno",
                             "module", "msecs", "pathname", "process",
                             "processName", "relativeCreated", "stack_info",
                             "exc_info", "exc_text", "thread", "threadName",
                             "taskName", "message"]
            }

        # Exception info hinzufügen
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class HumanFormatter(logging.Formatter):
    """
    Lesbares Format für Development.

    Output:
    2026-01-12 10:30:00 | INFO | item_manager | Item created | {"item_id": "123"}
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(8)
        logger = record.name.ljust(30)
        message = record.getMessage()

        # Extra fields
        extra = ""
        if hasattr(record, "extra") and record.extra:
            extra = f" | {json.dumps(record.extra)}"

        base = f"{timestamp} | {level} | {logger} | {message}{extra}"

        # Exception info
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base
