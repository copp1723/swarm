"""
Performance Monitoring Module
Tracks and logs performance metrics for the Email Agent system
"""

import time
import functools
import psutil
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from collections import defaultdict

from utils.logging_config import get_logger, logger as root_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Singleton class for monitoring system performance"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.active_operations = {}
        self._start_time = time.time()
        
        # Start background monitoring thread
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_system(self):
        """Background thread to monitor system resources"""
        while self._monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_mb = memory.used / (1024 * 1024)
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                
                # Log high resource usage
                if cpu_percent > 80:
                    logger.warning("High CPU usage detected", cpu_percent=cpu_percent)
                
                if memory_percent > 85:
                    logger.warning("High memory usage detected", 
                                 memory_percent=memory_percent,
                                 memory_mb=memory_mb)
                
                # Store metrics
                self.record_metric("system.cpu_percent", cpu_percent)
                self.record_metric("system.memory_percent", memory_percent)
                self.record_metric("system.memory_mb", memory_mb)
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error("Error in system monitoring", error=str(e))
                time.sleep(60)  # Back off on error
    
    def start_operation(self, operation_name: str, **context) -> str:
        """Start tracking a long-running operation"""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        self.active_operations[operation_id] = {
            "name": operation_name,
            "start_time": time.time(),
            "context": context
        }
        logger.debug(f"Started operation: {operation_name}", operation_id=operation_id, **context)
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, **result):
        """End tracking of an operation and record its duration"""
        if operation_id not in self.active_operations:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return
        
        operation = self.active_operations.pop(operation_id)
        duration = time.time() - operation["start_time"]
        
        # Record the metric
        self.record_metric(f"operation.{operation['name']}.duration", duration)
        
        # Increment counter
        status = "success" if success else "failure"
        self.increment_counter(f"operation.{operation['name']}.{status}")
        
        # Log the completion
        log_data = {
            "operation_id": operation_id,
            "duration_seconds": duration,
            "success": success,
            **operation["context"],
            **result
        }
        
        if duration > 10:  # Log slow operations
            logger.warning(f"Slow operation completed: {operation['name']}", **log_data)
        else:
            logger.info(f"Operation completed: {operation['name']}", **log_data)
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        metric_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "value": value,
            "tags": tags or {}
        }
        
        self.metrics[metric_name].append(metric_data)
        
        # Keep only last 1000 entries per metric
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a counter"""
        self.counters[counter_name] += value
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics"""
        summary = {
            "uptime_seconds": time.time() - self._start_time,
            "counters": dict(self.counters),
            "active_operations": len(self.active_operations),
            "metrics": {}
        }
        
        # Calculate metric summaries
        for metric_name, values in self.metrics.items():
            if values:
                recent_values = [v["value"] for v in values[-100:]]  # Last 100 values
                summary["metrics"][metric_name] = {
                    "count": len(values),
                    "latest": values[-1]["value"],
                    "avg": sum(recent_values) / len(recent_values),
                    "min": min(recent_values),
                    "max": max(recent_values)
                }
        
        return summary
    
    def log_metrics_summary(self):
        """Log a summary of metrics"""
        summary = self.get_metrics_summary()
        logger.info("Performance metrics summary", **summary)
    
    def shutdown(self):
        """Shutdown the monitor"""
        self._monitoring = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)


# Global instance
_monitor = PerformanceMonitor()


# Decorator for timing functions
def timed_operation(operation_name: Optional[str] = None):
    """Decorator to time function execution"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            op_id = _monitor.start_operation(op_name)
            
            try:
                result = func(*args, **kwargs)
                _monitor.end_operation(op_id, success=True)
                return result
            except Exception as e:
                _monitor.end_operation(op_id, success=False, error=str(e))
                raise
        
        return wrapper
    return decorator


# Convenience functions
def record_metric(metric_name: str, value: float, **tags):
    """Record a metric value"""
    _monitor.record_metric(metric_name, value, tags)


def increment_counter(counter_name: str, value: int = 1):
    """Increment a counter"""
    _monitor.increment_counter(counter_name, value)


def track_email_processing(email_id: str, stage: str, duration: float, success: bool = True):
    """Track email processing performance"""
    record_metric(f"email.{stage}.duration", duration, email_id=email_id)
    increment_counter(f"email.{stage}.{'success' if success else 'failure'}")
    
    if duration > 5:  # Log slow email processing
        logger.warning(f"Slow email {stage}", email_id=email_id, duration=duration)


def track_webhook_processing(webhook_type: str, duration: float, status_code: int):
    """Track webhook processing performance"""
    record_metric(f"webhook.{webhook_type}.duration", duration)
    increment_counter(f"webhook.{webhook_type}.status_{status_code}")
    
    if status_code >= 400:
        logger.warning(f"Webhook error", webhook_type=webhook_type, status_code=status_code)


def get_performance_summary() -> Dict[str, Any]:
    """Get current performance summary"""
    return _monitor.get_metrics_summary()


# Context manager for tracking operations
class track_operation:
    """Context manager for tracking operations"""
    
    def __init__(self, operation_name: str, **context):
        self.operation_name = operation_name
        self.context = context
        self.operation_id = None
        self.start_time = None
    
    def __enter__(self):
        self.operation_id = _monitor.start_operation(self.operation_name, **self.context)
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        duration = time.time() - self.start_time
        
        _monitor.end_operation(
            self.operation_id,
            success=success,
            duration=duration,
            error=str(exc_val) if exc_val else None
        )
        
        # Don't suppress exceptions
        return False


# Export public API
__all__ = [
    'timed_operation',
    'record_metric',
    'increment_counter',
    'track_email_processing',
    'track_webhook_processing',
    'get_performance_summary',
    'track_operation'
]