"""
Async Repository Classes for Database Operations
Provides async methods for common database operations
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.core import Conversation, Message, UserPreference, ModelUsage, SystemLog
from utils.async_database import get_async_session

logger = logging.getLogger(__name__)


class AsyncConversationRepository:
    """Async repository for Conversation operations"""
    
    @staticmethod
    async def create(session_id: str, model_id: str, title: str = None) -> Conversation:
        """Create a new conversation"""
        async with get_async_session() as session:
            conversation = Conversation(
                session_id=session_id,
                model_id=model_id,
                title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation
    
    @staticmethod
    async def get_by_session_id(session_id: str) -> Optional[Conversation]:
        """Get conversation by session ID"""
        async with get_async_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .options(selectinload(Conversation.messages))
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_active_conversations(limit: int = 50) -> List[Conversation]:
        """Get recent active conversations"""
        async with get_async_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.is_active == True)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    @staticmethod
    async def update_title(conversation_id: int, title: str) -> bool:
        """Update conversation title"""
        async with get_async_session() as session:
            result = await session.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(title=title, updated_at=datetime.utcnow())
            )
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def delete(conversation_id: int) -> bool:
        """Delete a conversation and all its messages"""
        async with get_async_session() as session:
            result = await session.execute(
                delete(Conversation)
                .where(Conversation.id == conversation_id)
            )
            await session.commit()
            return result.rowcount > 0


class AsyncMessageRepository:
    """Async repository for Message operations"""
    
    @staticmethod
    async def create(conversation_id: int, message_id: str, role: str, 
                    content: str, model_used: str = None, tools_used: List = None,
                    metadata: Dict = None) -> Message:
        """Create a new message"""
        async with get_async_session() as session:
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
            
            await session.commit()
            await session.refresh(message)
            return message
    
    @staticmethod
    async def get_by_conversation(conversation_id: int, limit: int = 100) -> List[Message]:
        """Get messages for a conversation"""
        async with get_async_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            messages = result.scalars().all()
            # Return in chronological order
            return list(reversed(messages))
    
    @staticmethod
    async def count_by_conversation(conversation_id: int) -> int:
        """Count messages in a conversation"""
        async with get_async_session() as session:
            result = await session.execute(
                select(func.count(Message.id))
                .where(Message.conversation_id == conversation_id)
            )
            return result.scalar() or 0
    
    @staticmethod
    async def delete_by_conversation(conversation_id: int) -> int:
        """Delete all messages in a conversation"""
        async with get_async_session() as session:
            result = await session.execute(
                delete(Message)
                .where(Message.conversation_id == conversation_id)
            )
            await session.commit()
            return result.rowcount


class AsyncUserPreferenceRepository:
    """Async repository for UserPreference operations"""
    
    @staticmethod
    async def get(session_id: str, key: str) -> Optional[str]:
        """Get a user preference value"""
        async with get_async_session() as session:
            result = await session.execute(
                select(UserPreference.preference_value)
                .where(and_(
                    UserPreference.session_id == session_id,
                    UserPreference.preference_key == key
                ))
            )
            value = result.scalar_one_or_none()
            return value
    
    @staticmethod
    async def set(session_id: str, key: str, value: str) -> UserPreference:
        """Set a user preference (create or update)"""
        async with get_async_session() as session:
            # Try to get existing preference
            result = await session.execute(
                select(UserPreference)
                .where(and_(
                    UserPreference.session_id == session_id,
                    UserPreference.preference_key == key
                ))
            )
            preference = result.scalar_one_or_none()
            
            if preference:
                # Update existing
                preference.preference_value = value
                preference.updated_at = datetime.utcnow()
            else:
                # Create new
                preference = UserPreference(
                    session_id=session_id,
                    preference_key=key,
                    preference_value=value
                )
                session.add(preference)
            
            await session.commit()
            await session.refresh(preference)
            return preference
    
    @staticmethod
    async def get_all(session_id: str) -> Dict[str, str]:
        """Get all preferences for a session"""
        async with get_async_session() as session:
            result = await session.execute(
                select(UserPreference)
                .where(UserPreference.session_id == session_id)
            )
            preferences = result.scalars().all()
            return {pref.preference_key: pref.preference_value for pref in preferences}


class AsyncModelUsageRepository:
    """Async repository for ModelUsage tracking"""
    
    @staticmethod
    async def track_usage(model_id: str, session_id: str, tokens: int = 0) -> ModelUsage:
        """Track model usage for the current date"""
        async with get_async_session() as session:
            today = datetime.utcnow().date()
            
            # Try to get existing usage record for today
            result = await session.execute(
                select(ModelUsage)
                .where(and_(
                    ModelUsage.model_id == model_id,
                    ModelUsage.session_id == session_id,
                    ModelUsage.date_created == today
                ))
            )
            usage = result.scalar_one_or_none()
            
            if usage:
                # Update existing record
                usage.usage_count += 1
                usage.total_tokens += tokens
                usage.total_messages += 1
                usage.last_used = datetime.utcnow()
            else:
                # Create new record
                usage = ModelUsage(
                    model_id=model_id,
                    session_id=session_id,
                    total_tokens=tokens,
                    total_messages=1,
                    date_created=today
                )
                session.add(usage)
            
            await session.commit()
            await session.refresh(usage)
            return usage
    
    @staticmethod
    async def get_usage_stats(session_id: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get usage statistics for the last N days"""
        async with get_async_session() as session:
            query = select(
                ModelUsage.model_id,
                func.sum(ModelUsage.usage_count).label('total_uses'),
                func.sum(ModelUsage.total_tokens).label('total_tokens'),
                func.sum(ModelUsage.total_messages).label('total_messages')
            ).group_by(ModelUsage.model_id)
            
            if session_id:
                query = query.where(ModelUsage.session_id == session_id)
            
            # Filter by date range
            from datetime import timedelta
            start_date = datetime.utcnow().date() - timedelta(days=days)
            query = query.where(ModelUsage.date_created >= start_date)
            
            result = await session.execute(query)
            stats = []
            for row in result:
                stats.append({
                    'model_id': row.model_id,
                    'total_uses': row.total_uses,
                    'total_tokens': row.total_tokens,
                    'total_messages': row.total_messages
                })
            return stats


class AsyncSystemLogRepository:
    """Async repository for SystemLog operations"""
    
    @staticmethod
    async def log_event(event_type: str, event_source: str, message: str,
                       session_id: str = None, additional_data: Dict = None) -> SystemLog:
        """Log a system event"""
        async with get_async_session() as session:
            log_entry = SystemLog(
                event_type=event_type,
                event_source=event_source,
                message=message,
                session_id=session_id,
                additional_data=additional_data or {}
            )
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            return log_entry
    
    @staticmethod
    async def get_recent_logs(limit: int = 100, event_type: str = None) -> List[SystemLog]:
        """Get recent system logs"""
        async with get_async_session() as session:
            query = select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)
            
            if event_type:
                query = query.where(SystemLog.event_type == event_type)
            
            result = await session.execute(query)
            return result.scalars().all()