"""
Database Session Management
Ensures proper session lifecycle and cleanup to prevent connection leaks
"""
import logging
import functools
import weakref
from contextlib import contextmanager
from typing import Optional, Callable, Any
from threading import Lock, current_thread
from datetime import datetime, timedelta

from flask import g, has_request_context
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from utils.database_access import db_access

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages database sessions with proper lifecycle management
    Prevents connection leaks and ensures cleanup
    """
    
    def __init__(self):
        self._sessions = weakref.WeakValueDictionary()
        self._session_metadata = {}
        self._lock = Lock()
        self._max_session_age = timedelta(minutes=30)
    
    def get_request_session(self) -> Optional[Session]:
        """Get or create a session for the current Flask request"""
        if not has_request_context():
            return None
        
        # Check if session already exists in Flask g
        if hasattr(g, 'db_session') and g.db_session:
            return g.db_session
        
        # Create new session for this request
        with db_access.get_sync_session() as session:
            g.db_session = session
            self._track_session(session, 'request')
            return session
    
    def get_thread_session(self) -> Session:
        """Get or create a session for the current thread"""
        thread_id = current_thread().ident
        
        with self._lock:
            # Check if session exists for this thread
            if thread_id in self._sessions:
                session = self._sessions[thread_id]
                # Check if session is still valid
                if self._is_session_valid(session):
                    return session
                else:
                    # Clean up invalid session
                    self._cleanup_session(thread_id)
            
            # Create new session for this thread
            with db_access.get_sync_session() as session:
                self._sessions[thread_id] = session
                self._track_session(session, 'thread')
                return session
    
    def _track_session(self, session: Session, context: str):
        """Track session metadata for monitoring"""
        session_id = id(session)
        self._session_metadata[session_id] = {
            'created_at': datetime.utcnow(),
            'context': context,
            'thread_id': current_thread().ident,
            'active': True
        }
    
    def _is_session_valid(self, session: Session) -> bool:
        """Check if a session is still valid and not too old"""
        session_id = id(session)
        metadata = self._session_metadata.get(session_id)
        
        if not metadata:
            return False
        
        # Check age
        age = datetime.utcnow() - metadata['created_at']
        if age > self._max_session_age:
            logger.warning(f"Session {session_id} exceeded max age ({age})")
            return False
        
        # Check if session is still active
        try:
            session.execute('SELECT 1')
            return True
        except SQLAlchemyError:
            return False
    
    def _cleanup_session(self, thread_id: int):
        """Clean up a session for a specific thread"""
        if thread_id in self._sessions:
            session = self._sessions[thread_id]
            session_id = id(session)
            
            try:
                session.close()
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")
            
            del self._sessions[thread_id]
            if session_id in self._session_metadata:
                del self._session_metadata[session_id]
    
    def cleanup_stale_sessions(self):
        """Clean up all stale sessions"""
        with self._lock:
            stale_threads = []
            current_time = datetime.utcnow()
            
            for thread_id, session in list(self._sessions.items()):
                session_id = id(session)
                metadata = self._session_metadata.get(session_id, {})
                
                if metadata:
                    age = current_time - metadata['created_at']
                    if age > self._max_session_age:
                        stale_threads.append(thread_id)
            
            for thread_id in stale_threads:
                self._cleanup_session(thread_id)
            
            if stale_threads:
                logger.info(f"Cleaned up {len(stale_threads)} stale sessions")
    
    def get_session_stats(self) -> dict:
        """Get statistics about active sessions"""
        with self._lock:
            active_sessions = len(self._sessions)
            
            context_counts = {}
            for metadata in self._session_metadata.values():
                context = metadata.get('context', 'unknown')
                context_counts[context] = context_counts.get(context, 0) + 1
            
            return {
                'active_sessions': active_sessions,
                'contexts': context_counts,
                'total_tracked': len(self._session_metadata)
            }


# Global session manager instance
session_manager = SessionManager()


def with_managed_session(func: Callable) -> Callable:
    """
    Decorator that provides a managed database session
    Ensures proper cleanup even on exceptions
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Try to use request session first
        session = session_manager.get_request_session()
        if session:
            return func(session, *args, **kwargs)
        
        # Fall back to thread session
        session = session_manager.get_thread_session()
        try:
            return func(session, *args, **kwargs)
        finally:
            # Ensure session is properly closed
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
    
    return wrapper


@contextmanager
def managed_session():
    """
    Context manager for database sessions with automatic cleanup
    Usage:
        with managed_session() as session:
            # Use session
    """
    # Try to use request session first
    session = session_manager.get_request_session()
    if session:
        yield session
        return
    
    # Create a new session
    with db_access.get_sync_session() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        else:
            session.commit()


def cleanup_request_session():
    """Clean up database session at end of request"""
    if hasattr(g, 'db_session') and g.db_session:
        try:
            g.db_session.close()
        except Exception as e:
            logger.error(f"Error closing request session: {e}")
        finally:
            g.db_session = None


def init_session_management(app):
    """Initialize session management for Flask app"""
    
    @app.teardown_appcontext
    def teardown_db(exception=None):
        """Clean up database session at end of request"""
        cleanup_request_session()
    
    @app.before_request
    def before_request():
        """Initialize request tracking"""
        g._request_start_time = datetime.utcnow()
    
    # Schedule periodic cleanup of stale sessions
    from tasks.maintenance_tasks import cleanup_stale_db_sessions
    cleanup_stale_db_sessions.apply_async(countdown=300)  # Run after 5 minutes
    
    logger.info("Database session management initialized")