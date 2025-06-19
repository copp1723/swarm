"""Rate limiting utilities for SWARM API endpoints"""
import time
import json
from functools import wraps
from flask import request, jsonify, g
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)"""
    
    def __init__(self):
        # Store: {key: [(timestamp, count)]}
        self.requests = {}
        self.cleanup_interval = 300  # Clean up old entries every 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup(self):
        """Remove old entries to prevent memory bloat"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            for key in list(self.requests.keys()):
                # Remove entries older than 1 hour
                self.requests[key] = [
                    (ts, count) for ts, count in self.requests.get(key, [])
                    if current_time - ts < 3600
                ]
                # Remove empty keys
                if not self.requests[key]:
                    del self.requests[key]
            self.last_cleanup = current_time
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier (e.g., IP or user ID)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        self._cleanup()
        
        current_time = time.time()
        window_start = current_time - window
        
        # Get requests in current window
        request_list = self.requests.get(key, [])
        recent_requests = [
            (ts, count) for ts, count in request_list
            if ts >= window_start
        ]
        
        # Count total requests in window
        total_requests = sum(count for _, count in recent_requests)
        
        # Check if limit exceeded
        if total_requests >= limit:
            # Calculate when the oldest request will expire
            if recent_requests:
                oldest_timestamp = min(ts for ts, _ in recent_requests)
                reset_time = oldest_timestamp + window
            else:
                reset_time = current_time + window
            
            return False, {
                'limit': limit,
                'remaining': 0,
                'reset': int(reset_time),
                'retry_after': int(reset_time - current_time)
            }
        
        # Add current request
        if key not in self.requests:
            self.requests[key] = []
        self.requests[key].append((current_time, 1))
        
        # Update recent requests count
        remaining = limit - total_requests - 1
        
        return True, {
            'limit': limit,
            'remaining': max(0, remaining),
            'reset': int(current_time + window)
        }


# Global rate limiter instance (replace with Redis in production)
rate_limiter = RateLimiter()


def rate_limit(requests_per_minute: int = 60, 
               requests_per_hour: int = None,
               key_func: Optional[callable] = None):
    """
    Rate limiting decorator
    
    Args:
        requests_per_minute: Max requests per minute
        requests_per_hour: Max requests per hour (optional)
        key_func: Function to determine rate limit key (default: IP address)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Determine rate limit key
            if key_func:
                limit_key = key_func()
            else:
                # Default to IP address or user ID
                if hasattr(request, 'user_id'):
                    limit_key = f"user:{request.user_id}"
                else:
                    limit_key = f"ip:{request.remote_addr}"
            
            # Check per-minute limit
            allowed, info = rate_limiter.check_rate_limit(
                limit_key,
                requests_per_minute,
                60  # 60 seconds
            )
            
            if not allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please retry after {info["retry_after"]} seconds'
                })
                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(info['reset'])
                response.headers['Retry-After'] = str(info['retry_after'])
                return response, 429
            
            # Check per-hour limit if specified
            if requests_per_hour:
                allowed_hour, info_hour = rate_limiter.check_rate_limit(
                    f"{limit_key}:hourly",
                    requests_per_hour,
                    3600  # 1 hour
                )
                
                if not allowed_hour:
                    response = jsonify({
                        'error': 'Hourly rate limit exceeded',
                        'message': f'Too many requests this hour. Please retry after {info_hour["retry_after"]} seconds'
                    })
                    response.headers['X-RateLimit-Limit-Hour'] = str(info_hour['limit'])
                    response.headers['X-RateLimit-Remaining-Hour'] = str(info_hour['remaining'])
                    response.headers['X-RateLimit-Reset-Hour'] = str(info_hour['reset'])
                    response.headers['Retry-After'] = str(info_hour['retry_after'])
                    return response, 429
            
            # Add rate limit headers to successful responses
            g.rate_limit_info = info
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def add_rate_limit_headers(response):
    """Add rate limit headers to response"""
    if hasattr(g, 'rate_limit_info'):
        info = g.rate_limit_info
        response.headers['X-RateLimit-Limit'] = str(info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(info['reset'])
    return response


# Specific rate limiters for different endpoint types
def strict_rate_limit(f):
    """Strict rate limit for expensive operations (5 per minute)"""
    return rate_limit(requests_per_minute=5, requests_per_hour=50)(f)


def standard_rate_limit(f):
    """Standard rate limit for normal API calls (60 per minute)"""
    return rate_limit(requests_per_minute=60, requests_per_hour=1000)(f)


def relaxed_rate_limit(f):
    """Relaxed rate limit for read operations (120 per minute)"""
    return rate_limit(requests_per_minute=120)(f)


# Redis-based rate limiter for production
class RedisRateLimiter:
    """Production-ready rate limiter using Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, any]]:
        """Check rate limit using Redis sliding window"""
        current_time = time.time()
        window_start = current_time - window
        
        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, window + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count >= limit:
            # Get oldest entry to calculate reset time
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_time = oldest[0][1] + window
            else:
                reset_time = current_time + window
            
            return False, {
                'limit': limit,
                'remaining': 0,
                'reset': int(reset_time),
                'retry_after': int(reset_time - current_time)
            }
        
        return True, {
            'limit': limit,
            'remaining': limit - current_count - 1,
            'reset': int(current_time + window)
        }