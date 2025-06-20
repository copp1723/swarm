"""
Database Operations Wrapper Utilities
Provides safe wrappers for common database operations that work in both sync and async contexts
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any, TypeVar, Union, Callable
from datetime import datetime
from functools import wraps

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from models.core import db, Conversation, Message, UserPreference, ModelUsage, SystemLog
from utils.database_access import db_access, with_sync_session, with_async_session
from utils.error_catalog import ErrorCodes
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseOperationError(Exception):
    """Custom exception for database operation failures"""
    pass


def handle_db_errors(func: Callable) -> Callable:
    """Decorator to handle common database errors"""
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            logger.error(f"Database integrity error in {func.__name__}: {e}")
            raise DatabaseOperationError(f"Data integrity violation: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise DatabaseOperationError(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except IntegrityError as e:
            logger.error(f"Database integrity error in {func.__name__}: {e}")
            raise DatabaseOperationError(f"Data integrity violation: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise DatabaseOperationError(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


class ConversationOps:
    """Conversation database operations with both sync and async support"""
    
    @staticmethod
    @handle_db_errors
    @with_sync_session
    def create_sync(session: Session, session_id: str, model_id: str, title: str = None) -> Conversation:
        """Create a conversation synchronously"""
        conversation = Conversation(
            session_id=session_id,
            model_id=model_id,
            title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        session.add(conversation)
        session.flush()
        return conversation
    
    @staticmethod
    @handle_db_errors
    @with_async_session
    async def create_async(session: AsyncSession, session_id: str, model_id: str, title: str = None) -> Conversation:
        """Create a conversation asynchronously"""
        conversation = Conversation(
            session_id=session_id,
            model_id=model_id,
            title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        session.add(conversation)
        await session.flush()
        return conversation
    
    @staticmethod
    @handle_db_errors
    @with_sync_session
    def get_by_session_sync(session: Session, session_id: str) -> Optional[Conversation]:
        """Get conversation by session ID synchronously"""
        return session.query(Conversation).filter_by(session_id=session_id).first()
    
    @staticmethod
    @handle_db_errors
    @with_async_session
    async def get_by_session_async(session: AsyncSession, session_id: str) -> Optional[Conversation]:
        """Get conversation by session ID asynchronously"""
        result = await session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def create(session_id: str, model_id: str, title: str = None, use_async: bool = False) -> Union[Conversation, Callable]:
        """Create a conversation with automatic sync/async detection"""
        if use_async:
            return ConversationOps.create_async(session_id, model_id, title)
        return ConversationOps.create_sync(session_id, model_id, title)
    
    @staticmethod
    def get_by_session(session_id: str, use_async: bool = False) -> Union[Optional[Conversation], Callable]:
        """Get conversation with automatic sync/async detection"""
        if use_async:
            return ConversationOps.get_by_session_async(session_id)
        return ConversationOps.get_by_session_sync(session_id)


class MessageOps:
    """Message database operations with both sync and async support"""
    
    @staticmethod
    @handle_db_errors
    @with_sync_session
    def create_sync(session: Session, conversation_id: int, message_id: str, 
                   role: str, content: str, model_used: str = None, 
                   tools_used: List = None, metadata: Dict = None) -> Message:
        """Create a message synchronously"""
        message = Message(
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
            content=content,
            model_used=model_used,
            tools_used=tools_used or [],
            message_metadata=metadata or {}
        )
        session.add(message)
        
        # Update conversation's updated_at
        session.query(Conversation).filter_by(id=conversation_id).update(
            {'updated_at': datetime.utcnow()}
        )
        session.flush()
        return message
    
    @staticmethod
    @handle_db_errors
    @with_async_session
    async def create_async(session: AsyncSession, conversation_id: int, message_id: str,
                          role: str, content: str, model_used: str = None,
                          tools_used: List = None, metadata: Dict = None) -> Message:
        """Create a message asynchronously"""
        message = Message(
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
            content=content,
            model_used=model_used,
            tools_used=tools_used or [],
            message_metadata=metadata or {}
        )
        session.add(message)
        
        # Update conversation's updated_at
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )
        await session.flush()
        return message
    
    @staticmethod
    @handle_db_errors
    @with_sync_session
    def get_by_conversation_sync(session: Session, conversation_id: int, limit: int = 100) -> List[Message]:
        """Get messages for a conversation synchronously"""
        messages = session.query(Message)\
            .filter_by(conversation_id=conversation_id)\
            .order_by(Message.created_at.desc())\
            .limit(limit)\
            .all()
        return list(reversed(messages))
    
    @staticmethod
    @handle_db_errors
    @with_async_session
    async def get_by_conversation_async(session: AsyncSession, conversation_id: int, limit: int = 100) -> List[Message]:
        """Get messages for a conversation asynchronously"""
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))


class SystemLogOps:
    """System log operations with both sync and async support"""
    
    @staticmethod
    @handle_db_errors
    @with_sync_session
    def log_event_sync(session: Session, event_type: str, event_source: str, 
                      message: str, session_id: str = None, 
                      additional_data: Dict = None) -> SystemLog:
        """Log a system event synchronously"""
        log_entry = SystemLog(
            event_type=event_type,
            event_source=event_source,
            message=message,
            session_id=session_id,
            additional_data=additional_data or {}
        )
        session.add(log_entry)
        session.flush()
        return log_entry
    
    @staticmethod
    @handle_db_errors
    @with_async_session
    async def log_event_async(session: AsyncSession, event_type: str, event_source: str,
                             message: str, session_id: str = None,
                             additional_data: Dict = None) -> SystemLog:
        """Log a system event asynchronously"""
        log_entry = SystemLog(
            event_type=event_type,
            event_source=event_source,
            message=message,
            session_id=session_id,
            additional_data=additional_data or {}
        )
        session.add(log_entry)
        await session.flush()
        return log_entry
    
    @staticmethod
    def log_event(event_type: str, event_source: str, message: str,
                  session_id: str = None, additional_data: Dict = None,
                  use_async: bool = False) -> Union[SystemLog, Callable]:
        """Log event with automatic sync/async detection"""
        if use_async:
            return SystemLogOps.log_event_async(
                event_type, event_source, message, session_id, additional_data
            )
        return SystemLogOps.log_event_sync(
            event_type, event_source, message, session_id, additional_data
        )


class HealthCheckOps:
    """Database health check operations"""
    
    @staticmethod
    def check_sync() -> Dict[str, Any]:
        """Perform synchronous health check"""
        return db_access.health_check_sync()
    
    @staticmethod
    async def check_async() -> Dict[str, Any]:
        """Perform asynchronous health check"""
        return await db_access.health_check_async()
    
    @staticmethod
    async def check_both() -> Dict[str, Any]:
        """Check both sync and async database connections"""
        sync_result = HealthCheckOps.check_sync()
        async_result = await HealthCheckOps.check_async()
        
        return {
            'sync_database': sync_result,
            'async_database': async_result,
            'overall_status': 'healthy' if (
                sync_result['status'] == 'healthy' and 
                async_result['status'] == 'healthy'
            ) else 'unhealthy'
        }


class DatabaseUtils:
    """Utility functions for database operations"""
    
    @staticmethod
    def run_in_sync_context(async_func: Callable, *args, **kwargs) -> Any:
        """Run an async database operation in a sync context"""
        return db_access.sync_to_async_bridge(async_func)(*args, **kwargs)
    
    @staticmethod
    async def run_in_async_context(sync_func: Callable, *args, **kwargs) -> Any:
        """Run a sync database operation in an async context"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)
    
    @staticmethod
    def initialize_database(app=None):
        """Initialize the database access layer"""
        db_access.initialize(app)
    
    @staticmethod
    def close_database():
        """Close all database connections"""
        db_access.close()