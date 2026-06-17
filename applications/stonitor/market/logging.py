"""Structured logging configuration for Stonitor."""

from __future__ import annotations

import logging
from typing import Any

import structlog


def configure_logging(*, json_logs: bool = False) -> None:
    """Configure structlog with JSON or console rendering."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_logs:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def bind_context(**kwargs: Any) -> None:
    """Bind request-scoped fields into structlog context."""
    structlog.contextvars.bind_contextvars(**kwargs)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger for the given module."""
    return structlog.get_logger(name)
