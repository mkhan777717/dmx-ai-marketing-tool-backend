import json
import logging
from datetime import datetime, timezone

from app.operations.logging.context import get_context_dict


class JSONFormatter(logging.Formatter):
    """
    Format logs as JSON including context variables (request_id, correlation_id, etc.).
    """

    def __init__(self, hostname: str = "localhost"):
        super().__init__()
        self.hostname = hostname

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "hostname": self.hostname,
        }

        # Merge context vars
        log_obj.update(get_context_dict())

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Extract custom extras if present
        if hasattr(record, "duration"):
            log_obj["duration"] = record.duration
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code

        return json.dumps(log_obj)
