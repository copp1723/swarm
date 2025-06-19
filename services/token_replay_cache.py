"""
Token Replay Cache Service
Prevents replay attacks by tracking and rejecting duplicate tokens
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError
import hashlib
import json

logger = logging.getLogger(__name__)

class TokenReplayCache:
    """
    Implements a token replay cache to prevent replay attacks.
    Supports both Redis and in-memory storage with automatic TTL.
    """
    
    def __init__(
        self, 
        ttl_seconds: int = 3600,  # 1 hour default
        use_redis: bool = True,
        redis_url: Optional[str] = None,
        cache_prefix: str = "token_replay:"
    ):
        """
        Initialize the token replay cache.
        
        Args:
            ttl_seconds: Time-to-live for tokens in seconds
            use_redis: Whether to use Redis (True) or in-memory cache (False)
            redis_url: Redis connection URL
            cache_prefix: Prefix for cache keys
        """
        self.ttl_seconds = ttl_seconds
        self.cache_prefix = cache_prefix
        self.use_redis = use_redis
        
        if use_redis:
            try:
                redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Token replay cache initialized with Redis")
            except (RedisError, Exception) as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory cache.")
                self.use_redis = False
                self.redis_client = None
        
        if not self.use_redis:
            # In-memory cache with expiration tracking
            self._memory_cache: Dict[str, float] = {}
            self._last_cleanup = time.time()
            logger.info("Token replay cache initialized with in-memory storage")
    
    def _get_cache_key(self, token: str) -> str:
        """Generate a cache key for the token"""
        # Hash the token to ensure consistent key length and privacy
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return f"{self.cache_prefix}{token_hash}"
    
    def _cleanup_memory_cache(self):
        """Remove expired tokens from in-memory cache"""
        current_time = time.time()
        # Cleanup every 60 seconds
        if current_time - self._last_cleanup > 60:
            expired_keys = [
                key for key, expiry in self._memory_cache.items()
                if expiry < current_time
            ]
            for key in expired_keys:
                del self._memory_cache[key]
            self._last_cleanup = current_time
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired tokens from memory cache")
    
    async def has_seen_token(self, token: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a token has been seen before (replay attack detection).
        
        Args:
            token: The token to check
            context: Optional context information (e.g., user_id, ip_address)
            
        Returns:
            True if token has been seen (potential replay), False if new token
        """
        if not token:
            logger.warning("Empty token provided to replay cache")
            return True  # Treat empty tokens as replays
        
        cache_key = self._get_cache_key(token)
        
        # Add context to the cache key if provided
        if context:
            context_str = json.dumps(context, sort_keys=True)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
            cache_key = f"{cache_key}:{context_hash}"
        
        try:
            if self.use_redis and self.redis_client:
                # Check if token exists in Redis
                exists = self.redis_client.exists(cache_key)
                if exists:
                    logger.warning(f"Token replay detected: {token[:20]}...")
                    return True
                
                # Token not seen, add it with TTL
                self.redis_client.setex(cache_key, self.ttl_seconds, "1")
                logger.debug(f"New token cached: {token[:20]}...")
                return False
            else:
                # In-memory cache
                self._cleanup_memory_cache()
                
                current_time = time.time()
                if cache_key in self._memory_cache:
                    if self._memory_cache[cache_key] > current_time:
                        logger.warning(f"Token replay detected (memory): {token[:20]}...")
                        return True
                    else:
                        # Token expired, treat as new
                        del self._memory_cache[cache_key]
                
                # Add new token
                self._memory_cache[cache_key] = current_time + self.ttl_seconds
                logger.debug(f"New token cached (memory): {token[:20]}...")
                return False
                
        except Exception as e:
            logger.error(f"Error checking token replay: {e}")
            # On error, be conservative and allow the request
            # but log it for monitoring
            return False
    
    async def mark_token_used(self, token: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Explicitly mark a token as used.
        
        Args:
            token: The token to mark as used
            context: Optional context information
            
        Returns:
            True if successfully marked, False if already used
        """
        return not await self.has_seen_token(token, context)
    
    async def revoke_token(self, token: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Revoke a token by adding it to the cache permanently (until TTL).
        
        Args:
            token: The token to revoke
            context: Optional context information
            
        Returns:
            True if successfully revoked
        """
        try:
            cache_key = self._get_cache_key(token)
            
            if context:
                context_str = json.dumps(context, sort_keys=True)
                context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{context_hash}"
            
            if self.use_redis and self.redis_client:
                # Set with extended TTL for revoked tokens
                self.redis_client.setex(cache_key, self.ttl_seconds * 24, "revoked")
                logger.info(f"Token revoked: {token[:20]}...")
            else:
                # In-memory cache with extended expiry
                self._memory_cache[cache_key] = time.time() + (self.ttl_seconds * 24)
                logger.info(f"Token revoked (memory): {token[:20]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache"""
        try:
            if self.use_redis and self.redis_client:
                # Get Redis stats
                info = self.redis_client.info()
                keys_count = self.redis_client.dbsize()
                pattern_count = len(self.redis_client.keys(f"{self.cache_prefix}*"))
                
                return {
                    "type": "redis",
                    "total_keys": keys_count,
                    "replay_tokens": pattern_count,
                    "memory_used": info.get('used_memory_human', 'unknown'),
                    "connected_clients": info.get('connected_clients', 0),
                    "ttl_seconds": self.ttl_seconds
                }
            else:
                # In-memory stats
                self._cleanup_memory_cache()
                current_time = time.time()
                active_tokens = sum(1 for exp in self._memory_cache.values() if exp > current_time)
                
                return {
                    "type": "in-memory",
                    "total_tokens": len(self._memory_cache),
                    "active_tokens": active_tokens,
                    "ttl_seconds": self.ttl_seconds
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    async def clear_cache(self) -> bool:
        """Clear all tokens from the cache (use with caution)"""
        try:
            if self.use_redis and self.redis_client:
                keys = self.redis_client.keys(f"{self.cache_prefix}*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} tokens from Redis cache")
            else:
                self._memory_cache.clear()
                logger.info("Cleared in-memory token cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Singleton instance
_token_cache = None

def get_token_replay_cache(ttl_seconds: Optional[int] = None) -> TokenReplayCache:
    """Get or create the token replay cache instance"""
    global _token_cache
    if _token_cache is None:
        ttl = ttl_seconds or int(os.getenv('TOKEN_REPLAY_TTL', '3600'))
        _token_cache = TokenReplayCache(ttl_seconds=ttl)
    return _token_cache