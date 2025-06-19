"""
Memory-Aware Chat Service - Optimized chat management with persistent storage
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import json

from services.chat_history_storage import get_chat_history_storage
from utils.memory_optimizer import (
    memory_efficient, async_memory_efficient,
    MemoryEfficientCache, get_memory_optimizer
)
from models.core import db
from sqlalchemy import text

logger = logging.getLogger(__name__)


class MemoryAwareChatService:
    """
    Optimized chat service with memory management and persistent storage
    """
    
    def __init__(self):
        # Storage backends
        self.storage = get_chat_history_storage()
        self.memory_optimizer = get_memory_optimizer()
        
        # Memory-efficient caches
        self.active_chats = MemoryEfficientCache(max_size=100, max_memory_mb=50)
        self.user_sessions = MemoryEfficientCache(max_size=500, max_memory_mb=20)
        
        # Configuration
        self.max_messages_in_memory = 50
        self.max_chat_age_hours = 24
        self.cleanup_interval_minutes = 30
        
        # Register cleanup functions
        self.memory_optimizer.register_cache(self.active_chats)
        self.memory_optimizer.register_cache(self.user_sessions)
        self.memory_optimizer.register_cleanup(self._memory_cleanup)
        
        # Background-task state flags (started later in async context)
        self._background_task_started: bool = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    # ------------------------------------------------------------------ #
    # Async-aware lifecycle helpers
    # ------------------------------------------------------------------ #

    async def initialize(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """
        Initialise background tasks once an event loop is running.
        Call this from the application’s async startup phase.
        Idempotent – safe to call multiple times.
        """
        if self._background_task_started:
            return

        if loop is None:
            loop = asyncio.get_running_loop()

        self._schedule_background_tasks(loop)
        self._background_task_started = True
        logger.info("MemoryAwareChatService background tasks started")

    async def shutdown(self) -> None:
        """
        Gracefully cancel background tasks.
        Call this during application shutdown to avoid noisy warnings.
        """
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("MemoryAwareChatService background tasks stopped")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _schedule_background_tasks(self, loop: asyncio.AbstractEventLoop) -> None:
        """Attach the periodic cleanup coroutine to the supplied loop."""
        self._cleanup_task = loop.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                self._cleanup_old_chats()
                self._optimize_storage()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    @memory_efficient(max_memory_mb=200)
    def create_chat(self, user_id: str, chat_type: str = "v2", metadata: Optional[Dict] = None) -> str:
        """Create a new chat session"""
        chat_id = f"{chat_type}_{user_id}_{int(datetime.now().timestamp())}"
        
        chat_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "chat_type": chat_type,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "messages": deque(maxlen=self.max_messages_in_memory)
        }
        
        # Store in memory cache
        self.active_chats.set(chat_id, chat_data)
        
        # Persist metadata to database
        self._persist_chat_metadata(chat_id, user_id, chat_type, metadata)
        
        logger.info(f"Created new {chat_type} chat: {chat_id}")
        return chat_id
    
    @memory_efficient()
    def add_message(self, chat_id: str, role: str, content: str, agent_id: Optional[str] = None) -> bool:
        """Add a message to a chat"""
        # Get or load chat
        chat_data = self._get_or_load_chat(chat_id)
        if not chat_data:
            logger.error(f"Chat not found: {chat_id}")
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id
        }
        
        # Add to memory (deque automatically limits size)
        chat_data["messages"].append(message)
        
        # Persist to storage
        if agent_id:
            self.storage.add_message(agent_id, role, content, {"chat_id": chat_id})
        else:
            self._persist_message(chat_id, message)
        
        return True
    
    def get_chat_history(self, chat_id: str, limit: int = 100) -> List[Dict]:
        """Get chat history with memory optimization"""
        # Try memory cache first
        chat_data = self.active_chats.get(chat_id)
        if chat_data and chat_data.get("messages"):
            messages = list(chat_data["messages"])
            if len(messages) >= limit:
                return messages[-limit:]
        
        # Load from persistent storage
        return self._load_chat_history(chat_id, limit)
    
    def get_agent_history(self, agent_id: str, limit: int = 100) -> List[Dict]:
        """Get agent-specific chat history"""
        return self.storage.get_history(agent_id, limit)
    
    @memory_efficient()
    def search_chats(self, user_id: str, query: str, chat_type: Optional[str] = None) -> List[Dict]:
        """Search through user's chats"""
        try:
            with db.engine.connect() as conn:
                sql = """
                    SELECT DISTINCT c.chat_id, c.chat_type, c.created_at, 
                           cm.content as first_match
                    FROM chats c
                    JOIN chat_messages cm ON c.chat_id = cm.chat_id
                    WHERE c.user_id = :user_id
                    AND cm.content LIKE :query
                """
                params = {"user_id": user_id, "query": f"%{query}%"}
                
                if chat_type:
                    sql += " AND c.chat_type = :chat_type"
                    params["chat_type"] = chat_type
                
                sql += " ORDER BY c.created_at DESC LIMIT 20"
                
                result = conn.execute(text(sql), params)
                
                chats = []
                for row in result:
                    chats.append({
                        "chat_id": row[0],
                        "chat_type": row[1],
                        "created_at": row[2],
                        "first_match": row[3][:100] + "..." if len(row[3]) > 100 else row[3]
                    })
                
                return chats
                
        except Exception as e:
            logger.error(f"Error searching chats: {e}")
            return []
    
    def _get_or_load_chat(self, chat_id: str) -> Optional[Dict]:
        """Get chat from memory or load from storage"""
        # Check memory first
        chat_data = self.active_chats.get(chat_id)
        if chat_data:
            return chat_data
        
        # Load from database
        chat_data = self._load_chat_metadata(chat_id)
        if chat_data:
            # Load recent messages
            messages = self._load_chat_history(chat_id, self.max_messages_in_memory)
            chat_data["messages"] = deque(messages, maxlen=self.max_messages_in_memory)
            
            # Cache in memory
            self.active_chats.set(chat_id, chat_data)
            
        return chat_data
    
    def _persist_chat_metadata(self, chat_id: str, user_id: str, chat_type: str, metadata: Optional[Dict]):
        """Persist chat metadata to database"""
        try:
            with db.engine.connect() as conn:
                # Create chats table if needed
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        chat_type TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        INDEX idx_user_chats (user_id, created_at)
                    )
                """))
                
                conn.execute(text("""
                    INSERT INTO chats (chat_id, user_id, chat_type, metadata)
                    VALUES (:chat_id, :user_id, :chat_type, :metadata)
                """), {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "chat_type": chat_type,
                    "metadata": json.dumps(metadata or {})
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist chat metadata: {e}")
    
    def _persist_message(self, chat_id: str, message: Dict):
        """Persist message to database"""
        try:
            with db.engine.connect() as conn:
                # Create messages table if needed
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        agent_id TEXT,
                        INDEX idx_chat_messages (chat_id, timestamp)
                    )
                """))
                
                conn.execute(text("""
                    INSERT INTO chat_messages (chat_id, role, content, agent_id)
                    VALUES (:chat_id, :role, :content, :agent_id)
                """), {
                    "chat_id": chat_id,
                    "role": message["role"],
                    "content": message["content"],
                    "agent_id": message.get("agent_id")
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")
    
    def _load_chat_metadata(self, chat_id: str) -> Optional[Dict]:
        """Load chat metadata from database"""
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT user_id, chat_type, created_at, metadata
                    FROM chats
                    WHERE chat_id = :chat_id
                """), {"chat_id": chat_id})
                
                row = result.fetchone()
                if row:
                    return {
                        "chat_id": chat_id,
                        "user_id": row[0],
                        "chat_type": row[1],
                        "created_at": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {}
                    }
        except Exception as e:
            logger.error(f"Failed to load chat metadata: {e}")
        
        return None
    
    def _load_chat_history(self, chat_id: str, limit: int) -> List[Dict]:
        """Load chat history from database"""
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT role, content, timestamp, agent_id
                    FROM chat_messages
                    WHERE chat_id = :chat_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """), {"chat_id": chat_id, "limit": limit})
                
                messages = []
                for row in result:
                    messages.append({
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                        "agent_id": row[3]
                    })
                
                # Reverse to get chronological order
                messages.reverse()
                return messages
                
        except Exception as e:
            logger.error(f"Failed to load chat history: {e}")
            return []
    
    def _cleanup_old_chats(self):
        """Clean up old chat data"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.max_chat_age_hours)
            
            # Clear from memory cache
            self.active_chats.clear_expired(self.max_chat_age_hours * 3600)
            
            # Archive old chats in database
            with db.engine.connect() as conn:
                # Move to archive table
                conn.execute(text("""
                    INSERT INTO archived_chats 
                    SELECT * FROM chats 
                    WHERE created_at < :cutoff
                """), {"cutoff": cutoff_time})
                
                conn.execute(text("""
                    INSERT INTO archived_chat_messages
                    SELECT cm.* FROM chat_messages cm
                    JOIN chats c ON cm.chat_id = c.chat_id
                    WHERE c.created_at < :cutoff
                """), {"cutoff": cutoff_time})
                
                # Delete from main tables
                conn.execute(text("""
                    DELETE FROM chat_messages
                    WHERE chat_id IN (
                        SELECT chat_id FROM chats WHERE created_at < :cutoff
                    )
                """), {"cutoff": cutoff_time})
                
                conn.execute(text("""
                    DELETE FROM chats WHERE created_at < :cutoff
                """), {"cutoff": cutoff_time})
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to cleanup old chats: {e}")
    
    def _optimize_storage(self):
        """Optimize storage tables"""
        try:
            with db.engine.connect() as conn:
                # Vacuum to reclaim space
                conn.execute(text("VACUUM"))
                
                # Analyze for query optimization
                conn.execute(text("ANALYZE"))
                
        except Exception as e:
            logger.error(f"Failed to optimize storage: {e}")
    
    def _memory_cleanup(self, level: str):
        """Memory cleanup callback"""
        if level == 'normal':
            # Clear expired entries
            self.active_chats.clear_expired()
            self.user_sessions.clear_expired()
        elif level == 'aggressive':
            # Clear 50% of caches
            self.active_chats.clear_percent(50)
            self.user_sessions.clear_percent(50)
        elif level == 'emergency':
            # Clear all caches
            self.active_chats.clear()
            self.user_sessions.clear()
            
            # Also clear agent storage cache
            self.storage._memory_cache.clear()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        return {
            "active_chats_cached": len(self.active_chats._cache),
            "user_sessions_cached": len(self.user_sessions._cache),
            "storage_stats": self.storage.get_memory_usage(),
            "config": {
                "max_messages_in_memory": self.max_messages_in_memory,
                "max_chat_age_hours": self.max_chat_age_hours
            }
        }


# Global instance
_chat_service = None


def get_memory_aware_chat_service() -> MemoryAwareChatService:
    """Get or create the chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = MemoryAwareChatService()
    return _chat_service