"""
Memory Optimization Utilities - System-wide memory management
"""
import gc
import os
import logging
import psutil
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
import weakref

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Monitor and manage system memory usage"""
    
    def __init__(self, 
                 warning_threshold_mb: int = 500,
                 critical_threshold_mb: int = 800,
                 check_interval: int = 60):
        self.warning_threshold = warning_threshold_mb * 1024 * 1024
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        self.check_interval = check_interval
        self._monitoring = False
        self._monitor_thread = None
        self._callbacks = {
            'warning': [],
            'critical': [],
            'normal': []
        }
        self._last_state = 'normal'
        
    def add_callback(self, level: str, callback: Callable):
        """Add callback for memory threshold events"""
        if level in self._callbacks:
            self._callbacks[level].append(callback)
    
    def start_monitoring(self):
        """Start background memory monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
        logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                stats = self.get_memory_stats()
                current_state = self._evaluate_state(stats['memory_used'])
                
                if current_state != self._last_state:
                    self._trigger_callbacks(current_state, stats)
                    self._last_state = current_state
                
                threading.Event().wait(self.check_interval)
            except Exception as e:
                logger.error(f"Error in memory monitor: {e}")
    
    def _evaluate_state(self, memory_used: int) -> str:
        """Evaluate memory state"""
        if memory_used >= self.critical_threshold:
            return 'critical'
        elif memory_used >= self.warning_threshold:
            return 'warning'
        return 'normal'
    
    def _trigger_callbacks(self, state: str, stats: Dict):
        """Trigger callbacks for state change"""
        logger.info(f"Memory state changed to: {state}")
        for callback in self._callbacks.get(state, []):
            try:
                callback(stats)
            except Exception as e:
                logger.error(f"Error in memory callback: {e}")
    
    @staticmethod
    def get_memory_stats() -> Dict[str, Any]:
        """Get current memory statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # System memory
        system_memory = psutil.virtual_memory()
        
        return {
            "memory_used": memory_info.rss,
            "memory_used_mb": memory_info.rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "system_memory_percent": system_memory.percent,
            "system_available_mb": system_memory.available / 1024 / 1024,
            "gc_stats": gc.get_stats()
        }


class MemoryOptimizer:
    """Centralized memory optimization strategies"""
    
    def __init__(self):
        self._cleanup_registry = []
        self._cache_registry = weakref.WeakSet()
        self._last_gc = datetime.now()
        self._gc_interval = timedelta(minutes=5)
        
    def register_cleanup(self, cleanup_func: Callable):
        """Register a cleanup function to be called during memory pressure"""
        self._cleanup_registry.append(cleanup_func)
    
    def register_cache(self, cache_obj):
        """Register a cache object for automatic cleanup"""
        self._cache_registry.add(cache_obj)
    
    def optimize_memory(self, level: str = 'normal'):
        """Run memory optimization based on level"""
        logger.info(f"Running memory optimization at level: {level}")
        
        if level == 'normal':
            self._normal_cleanup()
        elif level == 'aggressive':
            self._aggressive_cleanup()
        elif level == 'emergency':
            self._emergency_cleanup()
        
        # Force garbage collection
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        
        return self._get_optimization_results()
    
    def _normal_cleanup(self):
        """Normal cleanup - clear old data"""
        # Clear expired cache entries
        for cache in self._cache_registry:
            if hasattr(cache, 'clear_expired'):
                cache.clear_expired()
        
        # Run registered cleanup functions
        for cleanup_func in self._cleanup_registry:
            try:
                cleanup_func('normal')
            except Exception as e:
                logger.error(f"Cleanup function error: {e}")
    
    def _aggressive_cleanup(self):
        """Aggressive cleanup - clear more data"""
        # Clear 50% of cache
        for cache in self._cache_registry:
            if hasattr(cache, 'clear_percent'):
                cache.clear_percent(50)
            elif hasattr(cache, 'clear'):
                cache.clear()
        
        # Run aggressive cleanup
        for cleanup_func in self._cleanup_registry:
            try:
                cleanup_func('aggressive')
            except Exception as e:
                logger.error(f"Cleanup function error: {e}")
    
    def _emergency_cleanup(self):
        """Emergency cleanup - clear everything non-essential"""
        logger.warning("Running emergency memory cleanup!")
        
        # Clear all caches
        for cache in self._cache_registry:
            if hasattr(cache, 'clear'):
                cache.clear()
        
        # Run emergency cleanup
        for cleanup_func in self._cleanup_registry:
            try:
                cleanup_func('emergency')
            except Exception as e:
                logger.error(f"Cleanup function error: {e}")
        
        # Force multiple GC passes
        for _ in range(3):
            gc.collect()
    
    def _get_optimization_results(self) -> Dict[str, Any]:
        """Get results of optimization"""
        return MemoryMonitor.get_memory_stats()
    
    def schedule_gc(self):
        """Schedule garbage collection if needed"""
        now = datetime.now()
        if now - self._last_gc > self._gc_interval:
            gc.collect()
            self._last_gc = now


class MemoryEfficientCache:
    """Memory-efficient LRU cache with size limits"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory = max_memory_mb * 1024 * 1024
        self._cache = {}
        self._access_times = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                self._access_times[key] = datetime.now()
                return self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with memory checks"""
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = value
            self._access_times[key] = datetime.now()
    
    def _evict_lru(self):
        """Evict least recently used items"""
        if not self._access_times:
            return
        
        # Find oldest item
        oldest_key = min(self._access_times, key=self._access_times.get)
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def clear_expired(self, max_age_seconds: int = 3600):
        """Clear items older than max_age"""
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, access_time in self._access_times.items()
                if (now - access_time).seconds > max_age_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
                del self._access_times[key]
    
    def clear_percent(self, percent: int):
        """Clear given percentage of cache (oldest first)"""
        with self._lock:
            to_remove = int(len(self._cache) * percent / 100)
            if to_remove == 0:
                return
            
            # Sort by access time
            sorted_keys = sorted(self._access_times, key=self._access_times.get)
            for key in sorted_keys[:to_remove]:
                del self._cache[key]
                del self._access_times[key]


def memory_efficient(max_memory_mb: int = 100):
    """Decorator to make functions memory-efficient"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check memory before execution
            stats = MemoryMonitor.get_memory_stats()
            if stats['memory_used_mb'] > max_memory_mb:
                gc.collect()
                logger.warning(f"High memory usage before {func.__name__}: {stats['memory_used_mb']:.1f}MB")
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cleanup after if needed
            stats_after = MemoryMonitor.get_memory_stats()
            if stats_after['memory_used_mb'] > stats['memory_used_mb'] + 50:  # 50MB increase
                gc.collect()
                logger.info(f"Memory cleanup after {func.__name__}")
            
            return result
        return wrapper
    return decorator


def async_memory_efficient(max_memory_mb: int = 100):
    """Async decorator for memory-efficient functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check memory before execution
            stats = MemoryMonitor.get_memory_stats()
            if stats['memory_used_mb'] > max_memory_mb:
                gc.collect()
                logger.warning(f"High memory usage before {func.__name__}: {stats['memory_used_mb']:.1f}MB")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cleanup after if needed
            stats_after = MemoryMonitor.get_memory_stats()
            if stats_after['memory_used_mb'] > stats['memory_used_mb'] + 50:  # 50MB increase
                gc.collect()
                logger.info(f"Memory cleanup after {func.__name__}")
            
            return result
        return wrapper
    return decorator


# Global instances
_memory_monitor = None
_memory_optimizer = None


def get_memory_monitor() -> MemoryMonitor:
    """Get global memory monitor instance"""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor()
    return _memory_monitor


def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer


def setup_memory_management(app=None):
    """Setup memory management for the application"""
    monitor = get_memory_monitor()
    optimizer = get_memory_optimizer()
    
    # Add optimization callbacks
    monitor.add_callback('warning', lambda stats: optimizer.optimize_memory('normal'))
    monitor.add_callback('critical', lambda stats: optimizer.optimize_memory('aggressive'))
    
    # Start monitoring
    monitor.start_monitoring()
    
    logger.info("Memory management system initialized")
    
    if app:
        # Register Flask app cleanup
        @app.teardown_appcontext
        def cleanup(error):
            if error:
                optimizer.optimize_memory('normal')
    
    return monitor, optimizer