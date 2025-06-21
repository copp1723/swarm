"""
Chat History Storage Service - Persistent storage for agent conversations
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import OrderedDict
import threading

from models.core import db
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ChatHistoryStorage:
    """Manages chat history with database persistence and memory optimization"""
    
    def __init__(self, max_memory_conversations: int = 100):
        self.max_memory_conversations = max_memory_conversations
        self._memory_cache = OrderedDict()  # LRU cache
        self._lock = threading.Lock()
        self._table_initialized = False
    
    def _ensure_table_initialized(self):
        """Ensure database table is initialized when needed"""
        if self._table_initialized:
            return
        
        # Only initialize if we have a Flask app context
        try:
            from flask import has_app_context
            if not has_app_context():
                logger.warning("Cannot initialize chat history table without Flask app context")
                return
        except ImportError:
            pass
        
        self._init_db_table()
        self._table_initialized = True
    
    def _init_db_table(self):
        """Create chat history table if it doesn't exist"""
        try:
            with db.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_chat_history'"
                ))
                if not result.fetchone():
                    # Create table
                    conn.execute(text("""
                        CREATE TABLE agent_chat_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            agent_id TEXT NOT NULL,
                            message_id TEXT NOT NULL,
                            role TEXT NOT NULL,
                            content TEXT NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            metadata TEXT,
                            UNIQUE(agent_id, message_id)
                        )
                    """))
                    conn.execute(text(
                        "CREATE INDEX idx_agent_chat_history ON agent_chat_history(agent_id, created_at)"
                    ))
                    conn.commit()
                    logger.info("Created agent_chat_history table")
        except Exception as e:
            logger.error(f"Failed to initialize chat history table: {e}")
    
    def add_message(self, agent_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to chat history"""
        self._ensure_table_initialized()
        message_id = f"{agent_id}_{int(datetime.now().timestamp() * 1000)}"
        
        # Add to memory cache
        with self._lock:
            if agent_id not in self._memory_cache:
                self._memory_cache[agent_id] = []
            
            message = {
                "message_id": message_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            self._memory_cache[agent_id].append(message)
            
            # Limit memory usage
            if len(self._memory_cache[agent_id]) > 1000:  # Max 1000 messages per agent
                self._memory_cache[agent_id] = self._memory_cache[agent_id][-500:]  # Keep last 500
            
            # Move to end (LRU)
            self._memory_cache.move_to_end(agent_id)
            
            # Evict old conversations if needed
            if len(self._memory_cache) > self.max_memory_conversations:
                oldest_agent = next(iter(self._memory_cache))
                del self._memory_cache[oldest_agent]
        
        # Persist to database
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    INSERT OR REPLACE INTO agent_chat_history 
                    (agent_id, message_id, role, content, metadata)
                    VALUES (:agent_id, :message_id, :role, :content, :metadata)
                """), {
                    "agent_id": agent_id,
                    "message_id": message_id,
                    "role": role,
                    "content": content,
                    "metadata": json.dumps(metadata or {})
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist chat message: {e}")
    
    def get_history(self, agent_id: str, limit: int = 100) -> List[Dict]:
        """Get chat history for an agent"""
        self._ensure_table_initialized()
        # Check memory cache first
        with self._lock:
            if agent_id in self._memory_cache:
                # Move to end (LRU)
                self._memory_cache.move_to_end(agent_id)
                return self._memory_cache[agent_id][-limit:]
        
        # Load from database
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT message_id, role, content, created_at, metadata
                    FROM agent_chat_history
                    WHERE agent_id = :agent_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """), {"agent_id": agent_id, "limit": limit})
                
                messages = []
                for row in result:
                    messages.append({
                        "message_id": row[0],
                        "role": row[1],
                        "content": row[2],
                        "timestamp": row[3],
                        "metadata": json.loads(row[4]) if row[4] else {}
                    })
                
                # Reverse to get chronological order
                messages.reverse()
                
                # Cache in memory
                with self._lock:
                    self._memory_cache[agent_id] = messages
                    if len(self._memory_cache) > self.max_memory_conversations:
                        oldest_agent = next(iter(self._memory_cache))
                        del self._memory_cache[oldest_agent]
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to load chat history: {e}")
            return []
    
    def clear_history(self, agent_id: str):
        """Clear chat history for an agent"""
        self._ensure_table_initialized()
        # Clear from memory
        with self._lock:
            if agent_id in self._memory_cache:
                del self._memory_cache[agent_id]
        
        # Clear from database
        try:
            with db.engine.connect() as conn:
                conn.execute(text(
                    "DELETE FROM agent_chat_history WHERE agent_id = :agent_id"
                ), {"agent_id": agent_id})
                conn.commit()
                logger.info(f"Cleared chat history for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        with self._lock:
            total_messages = sum(len(msgs) for msgs in self._memory_cache.values())
            return {
                "cached_agents": len(self._memory_cache),
                "total_cached_messages": total_messages,
                "max_conversations": self.max_memory_conversations,
                "agents": {
                    agent_id: len(messages) 
                    for agent_id, messages in self._memory_cache.items()
                }
            }
    
    def cleanup_old_messages(self, days: int = 30):
        """Clean up old messages from database"""
        self._ensure_table_initialized()
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM agent_chat_history
                    WHERE created_at < datetime('now', '-' || :days || ' days')
                """), {"days": days})
                conn.commit()
                logger.info(f"Cleaned up {result.rowcount} old messages")
        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")


# Global instance
_chat_history_storage = None


def get_chat_history_storage() -> ChatHistoryStorage:
    """Get or create the chat history storage instance"""
    global _chat_history_storage
    if _chat_history_storage is None:
        _chat_history_storage = ChatHistoryStorage()
    return _chat_history_storage