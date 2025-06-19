"""Persistent chat history storage using database"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from models.core import db

logger = logging.getLogger(__name__)

Base = declarative_base()


class AgentChatHistory(db.Model):
    """Store agent chat history in database"""
    __tablename__ = 'agent_chat_history'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(255), index=True)
    message_id = Column(String(255), unique=True, nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column('metadata', Text)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'session_id': self.session_id,
            'message_id': self.message_id,
            'role': self.role,
            'content': self.content,
            'metadata': json.loads(self.message_metadata) if self.message_metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ChatHistoryService:
    """Service for managing chat history with database persistence"""
    
    def __init__(self, max_memory_messages=100):
        self.max_memory_messages = max_memory_messages
        self._memory_cache = {}  # Limited in-memory cache
        self._cache_metadata = {}  # Track cache usage
        
    def add_message(self, agent_id: str, role: str, content: str, 
                   session_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Add a message to chat history"""
        try:
            # Generate message ID
            message_id = f"{agent_id}_{datetime.utcnow().timestamp()}_{role[:3]}"
            
            # Store in database
            chat_entry = AgentChatHistory(
                agent_id=agent_id,
                session_id=session_id or 'default',
                message_id=message_id,
                role=role,
                content=content,
                message_metadata=json.dumps(metadata) if metadata else None
            )
            db.session.add(chat_entry)
            db.session.commit()
            
            # Update memory cache (limited)
            self._update_memory_cache(agent_id, {
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.debug(f"Added message to history for agent {agent_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to add message to history: {e}")
            db.session.rollback()
            return None
    
    def get_history(self, agent_id: str, limit: int = 50, 
                   session_id: Optional[str] = None) -> List[Dict]:
        """Get chat history for an agent"""
        try:
            # Try memory cache first for recent messages
            if agent_id in self._memory_cache and limit <= 10:
                return self._memory_cache[agent_id][-limit:]
            
            # Query database
            query = AgentChatHistory.query.filter_by(agent_id=agent_id)
            if session_id:
                query = query.filter_by(session_id=session_id)
            
            messages = query.order_by(AgentChatHistory.created_at.desc()).limit(limit).all()
            
            # Convert to list of dicts (reverse to get chronological order)
            history = [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat() if msg.created_at else None,
                    'metadata': json.loads(msg.metadata) if msg.metadata else {}
                }
                for msg in reversed(messages)
            ]
            
            # Update cache with recent messages
            if history and len(history) <= self.max_memory_messages:
                self._memory_cache[agent_id] = history
                
            return history
            
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []
    
    def clear_history(self, agent_id: str, session_id: Optional[str] = None):
        """Clear chat history for an agent"""
        try:
            query = AgentChatHistory.query.filter_by(agent_id=agent_id)
            if session_id:
                query = query.filter_by(session_id=session_id)
            
            query.delete()
            db.session.commit()
            
            # Clear memory cache
            if agent_id in self._memory_cache:
                del self._memory_cache[agent_id]
                
            logger.info(f"Cleared chat history for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")
            db.session.rollback()
    
    def _update_memory_cache(self, agent_id: str, message: Dict):
        """Update memory cache with size limits"""
        if agent_id not in self._memory_cache:
            self._memory_cache[agent_id] = []
            
        self._memory_cache[agent_id].append(message)
        
        # Trim cache if too large
        if len(self._memory_cache[agent_id]) > self.max_memory_messages:
            # Keep only recent messages
            self._memory_cache[agent_id] = self._memory_cache[agent_id][-self.max_memory_messages:]
            
        # Track cache usage
        self._cache_metadata[agent_id] = {
            'last_access': datetime.utcnow(),
            'message_count': len(self._memory_cache[agent_id])
        }
        
        # Clean up old cache entries if too many agents
        if len(self._memory_cache) > 50:  # Max 50 agents in memory
            self._evict_old_cache_entries()
    
    def _evict_old_cache_entries(self):
        """Remove least recently used cache entries"""
        # Sort by last access time
        sorted_agents = sorted(
            self._cache_metadata.items(),
            key=lambda x: x[1]['last_access']
        )
        
        # Remove oldest entries
        for agent_id, _ in sorted_agents[:10]:  # Remove 10 oldest
            if agent_id in self._memory_cache:
                del self._memory_cache[agent_id]
            if agent_id in self._cache_metadata:
                del self._cache_metadata[agent_id]
                
        logger.debug(f"Evicted old cache entries, current size: {len(self._memory_cache)}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage stats"""
        total_messages = sum(len(msgs) for msgs in self._memory_cache.values())
        
        return {
            'agents_cached': len(self._memory_cache),
            'total_messages_cached': total_messages,
            'cache_metadata': {
                agent_id: {
                    'message_count': meta['message_count'],
                    'last_access': meta['last_access'].isoformat()
                }
                for agent_id, meta in self._cache_metadata.items()
            }
        }


# Global instance
_chat_history_service = None


def get_chat_history_service() -> ChatHistoryService:
    """Get or create the chat history service"""
    global _chat_history_service
    if _chat_history_service is None:
        _chat_history_service = ChatHistoryService()
    return _chat_history_service


# Create default instance for backward compatibility
chat_history_service = get_chat_history_service()