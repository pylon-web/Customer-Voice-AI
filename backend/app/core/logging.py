"""Structured logging configuration for Customer Voice AI.

Provides JSON-formatted logs in production for log aggregators (ELK, CloudWatch, Datadog)
and readable colorized logs in development.
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include extra attributes
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName"
            }:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(level: str = "INFO", environment: str = "development") -> None:
    """Initialize structured logging across the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if environment.lower() == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        # Standard readable formatting for local dev
        dev_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(dev_formatter)

    root_logger.addHandler(console_handler)

    # Suppress verbose noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Adapter allowing arbitrary keyword arguments in log calls, populating extra dictionary."""

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        reserved = {"exc_info", "stack_info", "stacklevel", "extra"}
        extra_keys = [k for k in kwargs if k not in reserved]
        for k in extra_keys:
            extra[k] = kwargs.pop(k)
        return msg, kwargs


def get_logger(name: str) -> StructuredLoggerAdapter:
    """Return a logger instance configured for structured keyword arguments."""
    base_logger = logging.getLogger(name)
    return StructuredLoggerAdapter(base_logger, {})
