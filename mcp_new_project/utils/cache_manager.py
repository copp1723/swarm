"""Simple cache manager for query results"""
import hashlib
import json
import time
from functools import wraps
from typing import Any, Optional, Union, Callable
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Simple in-memory cache manager (use Redis in production)"""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache manager
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.cache = {}  # {key: {'value': value, 'expires_at': timestamp}}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # Clean up every 5 minutes
    
    def _cleanup(self):
        """Remove expired entries"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            expired_keys = [
                key for key, data in self.cache.items()
                if data['expires_at'] < current_time
            ]
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            self.last_cleanup = current_time
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        # Create a unique key from prefix and arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, tuple, dict)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                # For complex objects, use their string representation
                key_parts.append(str(arg))
        
        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        # Create hash of the key for consistent length
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        self._cleanup()
        
        if key in self.cache:
            entry = self.cache[key]
            if entry['expires_at'] > time.time():
                self.hits += 1
                logger.debug(f"Cache hit for key: {key}")
                return entry['value']
            else:
                # Expired
                del self.cache[key]
        
        self.misses += 1
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        self._cleanup()
        
        expires_at = time.time() + (ttl or self.default_ttl)
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
        logger.debug(f"Cached value for key: {key} (expires in {ttl or self.default_ttl}s)")
    
    def delete(self, key: str):
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Deleted cache key: {key}")
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'entries': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate * 100, 2),
            'total_requests': total_requests
        }
    
    def cache_result(self, key_prefix: str, ttl: Optional[int] = None):
        """
        Decorator to cache function results
        
        Args:
            key_prefix: Prefix for cache key
            ttl: Time-to-live in seconds
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(key_prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache the result
                self.set(cache_key, result, ttl)
                
                return result
            
            # Add cache control methods
            wrapper.cache_clear = lambda: self.clear()
            wrapper.cache_delete = lambda *args, **kwargs: self.delete(
                self._generate_key(key_prefix, *args, **kwargs)
            )
            
            return wrapper
        return decorator


# Global cache instance
cache_manager = CacheManager(default_ttl=300)


# Convenience decorators
def cache_for_minutes(minutes: int):
    """Cache result for specified minutes"""
    def decorator(func):
        return cache_manager.cache_result(
            f"{func.__module__}.{func.__name__}",
            ttl=minutes * 60
        )(func)
    return decorator


def cache_for_request():
    """Cache result for current request only (very short TTL)"""
    def decorator(func):
        return cache_manager.cache_result(
            f"{func.__module__}.{func.__name__}",
            ttl=5  # 5 seconds
        )(func)
    return decorator


# Example usage for common queries
@cache_for_minutes(10)
def get_agent_profiles():
    """Cache agent profiles for 10 minutes"""
    from utils.file_io import safe_read_json
    import os
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'agents.json')
    config = safe_read_json(config_path, default_value={'AGENT_PROFILES': {}})
    return config.get('AGENT_PROFILES', {})


@cache_for_minutes(5)
def get_workflow_templates():
    """Cache workflow templates for 5 minutes"""
    from utils.file_io import safe_read_json
    import os
    
    workflows_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'workflows.json')
    return safe_read_json(workflows_path, default_value={'templates': []})


# Redis-based cache manager for production
class RedisCacheManager(CacheManager):
    """Production cache manager using Redis"""
    
    def __init__(self, redis_client, default_ttl: int = 300):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = self.redis.get(key)
            if value:
                self.hits += 1
                return json.loads(value)
            self.misses += 1
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in Redis"""
        try:
            self.redis.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete key from Redis"""
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear(self):
        """Clear cache (careful in production!)"""
        # Only clear keys with our prefix
        try:
            for key in self.redis.scan_iter("cache:*"):
                self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")