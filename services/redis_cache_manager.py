"""
Redis Cache Manager for Production Scaling
Provides caching layer for database queries and agent responses
"""

import json
import pickle
from typing import Any, Optional, Union, List, Dict, Callable
from datetime import timedelta
from functools import wraps
import hashlib

from config.production_database import get_production_db
from utils.logging_config import get_logger

logger = get_logger(__name__)

class RedisCacheManager:
    """
    Production-grade cache manager using Redis
    Supports JSON and pickle serialization
    """
    
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour default
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Redis client with production config"""
        try:
            db_manager = get_production_db()
            self.redis_client = db_manager.redis_client
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key"""
        return f"swarm:cache:{namespace}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (more portable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if not data:
            return None
        
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Failed to deserialize cache data: {e}")
                return None
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._make_key(namespace, key)
            data = self.redis_client.get(cache_key)
            if data:
                logger.debug(f"Cache hit: {cache_key}")
                return self._deserialize(data)
            logger.debug(f"Cache miss: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, namespace: str, key: str, value: Any, 
            ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._make_key(namespace, key)
            data = self._serialize(value)
            
            if ttl is None:
                ttl = self.default_ttl
            
            if ttl > 0:
                self.redis_client.setex(cache_key, ttl, data)
            else:
                self.redis_client.set(cache_key, data)
            
            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._make_key(namespace, key)
            result = self.redis_client.delete(cache_key) > 0
            if result:
                logger.debug(f"Cache delete: {cache_key}")
            return result
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, namespace: str, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            cache_pattern = self._make_key(namespace, pattern)
            keys = self.redis_client.keys(cache_pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    def exists(self, namespace: str, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._make_key(namespace, key)
            return bool(self.redis_client.exists(cache_key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def get_many(self, namespace: str, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self.redis_client:
            return {}
        
        try:
            cache_keys = [self._make_key(namespace, k) for k in keys]
            values = self.redis_client.mget(cache_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
            
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    def set_many(self, namespace: str, mapping: Dict[str, Any], 
                 ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        if not self.redis_client:
            return False
        
        try:
            pipe = self.redis_client.pipeline()
            
            for key, value in mapping.items():
                cache_key = self._make_key(namespace, key)
                data = self._serialize(value)
                
                if ttl is None:
                    ttl = self.default_ttl
                
                if ttl > 0:
                    pipe.setex(cache_key, ttl, data)
                else:
                    pipe.set(cache_key, data)
            
            pipe.execute()
            logger.debug(f"Cache set_many: {len(mapping)} keys")
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    def increment(self, namespace: str, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._make_key(namespace, key)
            return self.redis_client.incrby(cache_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None
    
    def flush_namespace(self, namespace: str) -> int:
        """Flush all keys in a namespace"""
        return self.delete_pattern(namespace, "*")
    
    def flush_all(self) -> bool:
        """Flush entire cache (use with caution)"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.flushdb()
            logger.warning("Cache flushed: all keys deleted")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

# Cache decorators for common use cases

def cache_result(namespace: str, ttl: int = 3600, 
                key_func: Optional[Callable] = None):
    """
    Decorator to cache function results
    
    Args:
        namespace: Cache namespace
        ttl: Time to live in seconds
        key_func: Custom function to generate cache key from args
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash args and kwargs
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_str = ":".join(key_parts)
                cache_key = hashlib.md5(key_str.encode()).hexdigest()
            
            # Try to get from cache
            cache = get_cache_manager()
            cached_value = cache.get(namespace, cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(namespace, cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache(namespace: str, key_pattern: str = "*"):
    """
    Decorator to invalidate cache after function execution
    
    Args:
        namespace: Cache namespace to invalidate
        key_pattern: Pattern of keys to invalidate
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache
            cache = get_cache_manager()
            deleted = cache.delete_pattern(namespace, key_pattern)
            logger.debug(f"Invalidated {deleted} cache keys in {namespace}")
            
            return result
        
        return wrapper
    return decorator

# Specialized cache managers

class TaskCache:
    """Cache manager specifically for task data"""
    
    def __init__(self):
        self.cache = get_cache_manager()
        self.namespace = "tasks"
        self.ttl = 300  # 5 minutes for task data
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task from cache"""
        return self.cache.get(self.namespace, task_id)
    
    def set_task(self, task_id: str, task_data: Dict[str, Any]):
        """Cache task data"""
        self.cache.set(self.namespace, task_id, task_data, self.ttl)
    
    def invalidate_task(self, task_id: str):
        """Invalidate task cache"""
        self.cache.delete(self.namespace, task_id)
    
    def get_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get cached tasks for an agent"""
        key = f"agent:{agent_id}:tasks"
        return self.cache.get(self.namespace, key) or []
    
    def set_agent_tasks(self, agent_id: str, tasks: List[Dict[str, Any]]):
        """Cache tasks for an agent"""
        key = f"agent:{agent_id}:tasks"
        self.cache.set(self.namespace, key, tasks, 600)  # 10 minutes

class AgentResponseCache:
    """Cache manager for agent responses"""
    
    def __init__(self):
        self.cache = get_cache_manager()
        self.namespace = "agent_responses"
        self.ttl = 1800  # 30 minutes for responses
    
    def get_response(self, agent_id: str, prompt_hash: str) -> Optional[str]:
        """Get cached agent response"""
        key = f"{agent_id}:{prompt_hash}"
        return self.cache.get(self.namespace, key)
    
    def set_response(self, agent_id: str, prompt_hash: str, response: str):
        """Cache agent response"""
        key = f"{agent_id}:{prompt_hash}"
        self.cache.set(self.namespace, key, response, self.ttl)
    
    def hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt"""
        return hashlib.md5(prompt.encode()).hexdigest()

# Global instances
_cache_manager = None
_task_cache = None
_response_cache = None

def get_cache_manager() -> RedisCacheManager:
    """Get or create cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = RedisCacheManager()
    return _cache_manager

def get_task_cache() -> TaskCache:
    """Get or create task cache instance"""
    global _task_cache
    if _task_cache is None:
        _task_cache = TaskCache()
    return _task_cache

def get_response_cache() -> AgentResponseCache:
    """Get or create response cache instance"""
    global _response_cache
    if _response_cache is None:
        _response_cache = AgentResponseCache()
    return _response_cache