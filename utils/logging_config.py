"""
Centralized Logging Configuration using Loguru
Provides structured logging with automatic rotation, formatting, and Sentry integration
"""

import os
import sys
from pathlib import Path
from loguru import logger
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from typing import Optional, Dict, Any
import builtins
import sys


class LogConfig:
    """Logging configuration management"""
    
    # Log levels
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Log file settings
    LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
    LOG_FILE_ROTATION = os.getenv("LOG_FILE_ROTATION", "100 MB")
    LOG_FILE_RETENTION = os.getenv("LOG_FILE_RETENTION", "30 days")
    LOG_FILE_COMPRESSION = os.getenv("LOG_FILE_COMPRESSION", "zip")
    
    # Sentry settings
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "development")
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    
    # Feature flags
    ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
    ENABLE_JSON_LOGS = os.getenv("ENABLE_JSON_LOGS", "false").lower() == "true"
    ENABLE_SENTRY = os.getenv("ENABLE_SENTRY", "true").lower() == "true"


def setup_logging(
    app_name: str = "email_agent",
    flask_app: Optional[Any] = None,
    extra_sinks: Optional[Dict[str, Dict[str, Any]]] = None
) -> None:
    """
    Configure Loguru for the application
    
    Args:
        app_name: Name of the application for log files
        flask_app: Flask application instance for Sentry integration
        extra_sinks: Additional log sinks to configure
    """
    # Remove default handler
    logger.remove()
    
    # Create log directory if it doesn't exist
    LogConfig.LOG_DIR.mkdir(exist_ok=True)
    
    # Console logging format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # File logging format (more detailed)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # JSON format for structured logging
    json_format = (
        '{"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
        '"level": "{level}", '
        '"logger": "{name}", '
        '"function": "{function}", '
        '"line": {line}, '
        '"message": "{message}", '
        '"extra": {extra}}'
    )
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=console_format,
        level=LogConfig.LOG_LEVEL,
        colorize=True,
        enqueue=True
    )
    
    # Add file handlers if enabled
    if LogConfig.ENABLE_FILE_LOGGING:
        # General application log
        logger.add(
            LogConfig.LOG_DIR / f"{app_name}.log",
            format=file_format if not LogConfig.ENABLE_JSON_LOGS else json_format,
            level=LogConfig.LOG_LEVEL,
            rotation=LogConfig.LOG_FILE_ROTATION,
            retention=LogConfig.LOG_FILE_RETENTION,
            compression=LogConfig.LOG_FILE_COMPRESSION,
            enqueue=True
        )
        
        # Error log (errors and above)
        logger.add(
            LogConfig.LOG_DIR / f"{app_name}.error.log",
            format=file_format,
            level="ERROR",
            rotation=LogConfig.LOG_FILE_ROTATION,
            retention=LogConfig.LOG_FILE_RETENTION,
            compression=LogConfig.LOG_FILE_COMPRESSION,
            enqueue=True
        )
        
        # Debug log (only in development)
        if LogConfig.SENTRY_ENVIRONMENT == "development":
            logger.add(
                LogConfig.LOG_DIR / f"{app_name}.debug.log",
                format=file_format,
                level="DEBUG",
                rotation="50 MB",
                retention="7 days",
                compression=LogConfig.LOG_FILE_COMPRESSION,
                enqueue=True
            )
    
    # Add extra sinks if provided
    if extra_sinks:
        for sink_name, sink_config in extra_sinks.items():
            logger.add(**sink_config)
    
    # Configure Sentry if enabled
    if LogConfig.ENABLE_SENTRY and LogConfig.SENTRY_DSN:
        setup_sentry(flask_app)
        logger.info("Sentry error tracking enabled")
    
    logger.info(f"Logging configured for {app_name}")
    logger.info(f"Log level: {LogConfig.LOG_LEVEL}")
    logger.info(f"Log directory: {LogConfig.LOG_DIR}")

    # ------------------------------------------------------------------ #
    # Patch built-in print so legacy prints are captured by Loguru
    # ------------------------------------------------------------------ #
    _patch_print()  # Safe-no-op if already patched


# ----------------------------------------------------------------------#
# Legacy print() redirection helpers
# ----------------------------------------------------------------------#

# Keep reference to the original print implementation
_ORIGINAL_PRINT = builtins.print
_PRINT_PATCHED = False


def _patched_print(*args, **kwargs):  # type: ignore
    """
    Replacement for built-in print that forwards to Loguru.
    Falls back to original print if writing to a custom stream.
    """
    # If user passed a custom file stream (not stdout/stderr) use original.
    file_obj = kwargs.get("file", sys.stdout)
    if file_obj not in (sys.stdout, sys.stderr):
        return _ORIGINAL_PRINT(*args, **kwargs)

    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    # Compose message similar to default print behaviour
    message = sep.join(str(a) for a in args) + end.rstrip("\n")
    logger.bind(orig="print_patch").info(message)


def _patch_print() -> None:
    """Replace built-in print with Loguru logger wrapper (idempotent)."""
    global _PRINT_PATCHED
    if _PRINT_PATCHED:
        return
    builtins.print = _patched_print  # type: ignore
    _PRINT_PATCHED = True



def setup_sentry(flask_app: Optional[Any] = None) -> None:
    """
    Configure Sentry error tracking
    
    Args:
        flask_app: Flask application instance
    """
    integrations = [
        LoggingIntegration(
            level=None,  # Capture all levels
            event_level=None  # Don't send logs as events
        ),
        CeleryIntegration()
    ]
    
    if flask_app:
        integrations.append(FlaskIntegration())
    
    sentry_sdk.init(
        dsn=LogConfig.SENTRY_DSN,
        environment=LogConfig.SENTRY_ENVIRONMENT,
        integrations=integrations,
        traces_sample_rate=LogConfig.SENTRY_TRACES_SAMPLE_RATE,
        # Additional options
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send personally identifiable information
        before_send=before_send_filter
    )


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter events before sending to Sentry
    
    Args:
        event: The event to be sent
        hint: Additional information about the event
        
    Returns:
        Modified event or None to drop it
    """
    # Filter out certain errors
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        
        # Don't send certain expected errors
        ignored_errors = [
            "BrokenPipeError",
            "ConnectionResetError",
            "KeyboardInterrupt"
        ]
        
        if exc_type.__name__ in ignored_errors:
            return None
    
    # Scrub sensitive data
    if 'request' in event:
        request = event['request']
        
        # Remove authorization headers
        if 'headers' in request:
            headers = dict(request['headers'])
            for key in ['authorization', 'x-api-key', 'x-mailgun-signature']:
                if key in headers:
                    headers[key] = '[FILTERED]'
            request['headers'] = headers
        
        # Remove sensitive query parameters
        if 'query_string' in request:
            # Parse and filter query string
            pass
    
    return event


def get_logger(name: str) -> logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)


# Performance monitoring decorators
def log_performance(func):
    """Decorator to log function performance"""
    def wrapper(*args, **kwargs):
        logger.debug(f"Starting {func.__name__}")
        start_time = logger.time()
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__} in {logger.time() - start_time:.3f}s")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    
    return wrapper


def log_email_task(task_id: str, action: str, **kwargs):
    """
    Log email task processing events
    
    Args:
        task_id: Task identifier
        action: Action being performed
        **kwargs: Additional context
    """
    logger.bind(
        task_id=task_id,
        action=action,
        **kwargs
    ).info(f"Email task {action}: {task_id}")


def log_webhook_event(event_type: str, sender: str, status: str, **kwargs):
    """
    Log webhook events
    
    Args:
        event_type: Type of webhook event
        sender: Email sender
        status: Processing status
        **kwargs: Additional context
    """
    logger.bind(
        event_type=event_type,
        sender=sender,
        status=status,
        **kwargs
    ).info(f"Webhook {event_type} from {sender}: {status}")


def log_agent_assignment(task_id: str, agent_id: str, task_type: str, priority: str):
    """
    Log agent assignment decisions
    
    Args:
        task_id: Task identifier
        agent_id: Assigned agent ID
        task_type: Type of task
        priority: Task priority
    """
    logger.bind(
        task_id=task_id,
        agent_id=agent_id,
        task_type=task_type,
        priority=priority
    ).info(f"Task {task_id} assigned to {agent_id}")


# Contextual logging
class LogContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        self.token = logger.contextualize(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            logger.unbind(**self.context)


# Export commonly used functions
__all__ = [
    "setup_logging",
    "get_logger",
    "log_performance",
    "log_email_task",
    "log_webhook_event",
    "log_agent_assignment",
    "LogContext",
    "logger"
]