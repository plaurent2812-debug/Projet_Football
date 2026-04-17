"""Centralized structured logging configuration for ProbaLab."""

from __future__ import annotations

import contextvars
import logging
import uuid

from pythonjsonlogger.json import JsonFormatter

# Context variable for request tracing
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class ProbaLabFormatter(JsonFormatter):
    """JSON formatter that injects request_id into every log record."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["request_id"] = request_id_var.get("")
        log_record["logger"] = record.name
        log_record["level"] = record.levelname


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON structured output.

    Call this ONCE at application startup (api/main.py lifespan or worker.py).

    Args:
        level: Logging level for the root logger (default: logging.INFO).

    Returns:
        None.
    """
    root = logging.getLogger()

    # Avoid duplicate handlers on repeated calls
    if any(isinstance(h.formatter, ProbaLabFormatter) for h in root.handlers):
        return

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler()
    formatter = ProbaLabFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def generate_request_id() -> str:
    """Generate and set a new request ID in the context.

    Returns:
        The newly generated request ID (12-char hex string).
    """
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """Get the current request ID from context.

    Returns:
        Current request ID, or empty string if none is set.
    """
    return request_id_var.get("")
