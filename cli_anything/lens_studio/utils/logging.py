"""Structured logging utilities for Lens Studio CLI.

Provides setup_logging() for configuration and get_logger() for per-module loggers.
Supports plain text and JSON-formatted output.
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines for structured log output."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(
    level: int = logging.INFO,
    json_format: bool = False,
) -> None:
    """Configure the root logger for the CLI.

    Args:
        level: Logging level (default: INFO).
        json_format: If True, emit JSON-formatted log lines.
    """
    root = logging.getLogger("cli_anything")
    root.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the cli_anything namespace.

    Args:
        name: Typically ``__name__`` of the calling module.
    """
    return logging.getLogger(name)
