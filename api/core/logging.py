# core/logging.py
import sys
import logging
import structlog
from pathlib import Path
from config.settings import settings

def configure_logging(log_file: str = "api/logs/app.log", log_to_console: bool = None):
    """Configure structlog for JSON logging to file and optional console output"""

    if log_to_console is None:
        log_to_console = settings.log_to_console

    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # JSON renderer for file
    json_processors = shared_processors + [
        structlog.processors.JSONRenderer()
    ]

    # Console renderer for development
    console_processors = shared_processors + [
        structlog.dev.ConsoleRenderer()
    ]

    # Configure structlog
    structlog.configure(
        processors=json_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(
            file=open(log_file, "a")
        ),
        cache_logger_on_first_use=True,
    )

    # Add console output if requested
    if log_to_console:
        structlog.configure(
            processors=console_processors,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        )

def get_logger(name: str):
    """Get a structured logger for the given module name"""
    return structlog.get_logger(name)
