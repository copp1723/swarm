"""Logging utilities"""
import logging
from typing import Optional
from models.core import db, SystemLog
from utils.database import db_transaction

logger = logging.getLogger(__name__)

def log_system_event(event_type: str, event_source: str, message: str, session_id: Optional[str] = None, additional_data: Optional[dict] = None):
    """Log a system event to database and logger"""
    try:
        # Log to Python logger
        logger.info(f"[{event_type}] {event_source}: {message}")

        # Create database log entry using context manager
        with db_transaction():
            log_entry = SystemLog(
                event_type=event_type,
                event_source=event_source,
                message=message,
                session_id=session_id,
                additional_data=additional_data or {}
            )
            db.session.add(log_entry)

    except Exception as e:
        # If database logging fails, at least log to Python logger
        logger.error(f"Failed to log system event to database: {e}")
        logger.info(f"Original event - [{event_type}] {event_source}: {message}")