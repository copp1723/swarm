"""
Monitoring endpoints for system health and performance metrics
"""

from flask import Blueprint, jsonify
import psutil
from datetime import datetime, timezone

from utils.logging_config import get_logger
from utils.performance_monitor import get_performance_summary

logger = get_logger(__name__)

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


@monitoring_bp.route('/health', methods=['GET'])
def health_check():
    """
    Comprehensive health check endpoint
    """
    try:
        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check service dependencies
        checks = {
            "database": check_database(),
            "redis": check_redis(),
            "celery": check_celery()
        }
        
        # Overall health status
        all_healthy = all(checks.values())
        status = "healthy" if all_healthy else "degraded"
        
        return jsonify({
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            }
        }), 200 if all_healthy else 503
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@monitoring_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Get performance metrics
    """
    try:
        summary = get_performance_summary()
        
        # Add current system metrics
        summary["current_system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "active_connections": len(psutil.net_connections()),
            "process_count": len(psutil.pids())
        }
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": summary
        }), 200
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@monitoring_bp.route('/ready', methods=['GET'])
def readiness():
    """
    Kubernetes-style readiness probe
    """
    # Check if the service is ready to accept traffic
    ready_checks = {
        "initialized": True,  # Service initialization complete
        "database": check_database(),
        "dependencies": check_redis() and check_celery()
    }
    
    is_ready = all(ready_checks.values())
    
    return jsonify({
        "ready": is_ready,
        "checks": ready_checks
    }), 200 if is_ready else 503


@monitoring_bp.route('/live', methods=['GET'])
def liveness():
    """
    Kubernetes-style liveness probe
    """
    # Simple check to see if the service is alive
    return jsonify({
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@monitoring_bp.route('/simple-health', methods=['GET'])
def simple_health():
    """
    Simple health check without external dependencies for deployment
    """
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "mcp-executive",
            "version": "1.0.0"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/services', methods=['GET'])
def service_status():
    """Get detailed service status for debugging dependency injection issues"""
    try:
        from core.service_registry import get_service_status, validate_critical_services
        
        # Get overall service status
        status = get_service_status()
        
        # Get critical service validation
        critical_status = validate_critical_services()
        
        # Add health information
        overall_health = all(critical_status.values())
        
        return jsonify({
            'overall_health': overall_health,
            'critical_services': critical_status,
            'service_details': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        return jsonify({
            'error': str(e),
            'overall_health': False,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


def check_database():
    """Check database connectivity"""
    try:
        from models.core import db
        # Execute a simple query
        db.session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.warning("Database check failed", error=str(e))
        return False


def check_redis():
    """Check Redis connectivity"""
    try:
        import redis
        from config.celery_config import CELERY_BROKER_URL
        
        # Parse Redis URL
        r = redis.from_url(CELERY_BROKER_URL)
        r.ping()
        return True
    except Exception as e:
        logger.warning("Redis check failed", error=str(e))
        return False


def check_celery():
    """Check Celery worker availability"""
    try:
        from celery import current_app as celery_app
        
        # Get active worker stats
        stats = celery_app.control.inspect().stats()
        return stats is not None and len(stats) > 0
    except Exception as e:
        logger.warning("Celery check failed", error=str(e))
        return False