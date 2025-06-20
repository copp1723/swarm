#!/usr/bin/env python3
"""
Production-ready Flask application with PostgreSQL, Redis, and Email Integration
Includes database persistence, caching, and email-to-agent workflow
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from flask import Flask, jsonify
from flask_cors import CORS
from celery import Celery

# Import configurations
from config.production_database import init_production_database, get_production_db
from config.database import create_all_tables
from models.core import db
from utils.logging_config import get_logger
from utils.celery_app import make_celery

logger = get_logger(__name__)

def create_production_app():
    """Create and configure production Flask application"""
    
    # Create Flask app
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='/static')
    
    # CORS configuration
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
    
    # Initialize production database
    logger.info("Initializing production database...")
    db_manager = init_production_database(app)
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Celery
    celery = make_celery(app)
    
    # Create database tables
    with app.app_context():
        logger.info("Creating database tables...")
        create_all_tables(db)
        
        # Run health check
        health = db_manager.health_check()
        logger.info(f"Database health check: {health}")
    
    # Initialize services
    _initialize_services(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Initialize WebSocket support if available
    socketio = None
    if os.environ.get('ENABLE_WEBSOCKETS', 'true').lower() == 'true':
        try:
            from utils.websocket import init_socketio
            socketio = init_socketio(app)
            logger.info("WebSocket support enabled")
        except ImportError:
            logger.warning("WebSocket support not available")
    
    app.socketio = socketio
    app.celery = celery
    
    return app

def _initialize_services(app):
    """Initialize all application services"""
    
    # Initialize cache manager
    from services.redis_cache_manager import get_cache_manager
    cache = get_cache_manager()
    app.cache = cache
    
    # Initialize task storage
    from services.db_task_storage import get_task_storage
    task_storage = get_task_storage()
    app.task_storage = task_storage
    
    # Initialize email integration
    from services.email_agent_integration import get_email_integration
    email_integration = get_email_integration()
    app.email_integration = email_integration
    
    logger.info("All services initialized")

def _register_blueprints(app):
    """Register all API blueprints"""
    
    # Core blueprints
    from routes.agents import agents_bp
    from routes.tasks import tasks_bp
    from routes.chat import chat_bp
    from routes.files import files_bp
    from routes.audit import audit_bp
    
    app.register_blueprint(agents_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(audit_bp)
    
    # Email routes
    from services.email_agent import email_bp
    app.register_blueprint(email_bp)
    
    # Additional production routes
    from routes.monitoring import monitoring_bp
    app.register_blueprint(monitoring_bp)
    
    logger.info("All blueprints registered")

def _register_error_handlers(app):
    """Register error handlers for production"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(Exception)
    def unhandled_exception(error):
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Create the application instance before defining routes
app = None

def get_app():
    global app
    if app is None:
        app = create_production_app()
    return app

# Production routes
@app.route('/health')
def health_check():
    """Comprehensive health check endpoint"""
    db_manager = get_production_db()
    db_health = db_manager.health_check()
    
    # Check cache
    cache_healthy = False
    try:
        from services.redis_cache_manager import get_cache_manager
        cache = get_cache_manager()
        cache.set('health', 'check', 'ok', ttl=10)
        cache_healthy = cache.get('health', 'check') == 'ok'
    except:
        pass
    
    # Check Celery
    celery_healthy = False
    try:
        from celery import current_app as celery_app
        i = celery_app.control.inspect()
        stats = i.stats()
        celery_healthy = stats is not None and len(stats) > 0
    except:
        pass
    
    overall_health = db_health['healthy'] and cache_healthy
    
    return jsonify({
        'status': 'healthy' if overall_health else 'degraded',
        'database': {
            'postgres': db_health['postgres'],
            'redis': db_health['redis']
        },
        'cache': cache_healthy,
        'celery': celery_healthy,
        'errors': db_health.get('errors', [])
    }), 200 if overall_health else 503

@app.route('/metrics')
def metrics():
    """Metrics endpoint for monitoring"""
    from models.task_storage import CollaborationTask, AuditLog
    from datetime import datetime, timedelta
    
    # Task metrics
    total_tasks = CollaborationTask.query.count()
    active_tasks = CollaborationTask.query.filter_by(status='running').count()
    completed_today = CollaborationTask.query.filter(
        CollaborationTask.completed_at >= datetime.utcnow() - timedelta(days=1)
    ).count()
    
    # Audit metrics
    total_actions = AuditLog.query.count()
    recent_errors = AuditLog.query.filter(
        AuditLog.success == False,
        AuditLog.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).count()
    
    return jsonify({
        'tasks': {
            'total': total_tasks,
            'active': active_tasks,
            'completed_today': completed_today
        },
        'audit': {
            'total_actions': total_actions,
            'recent_errors': recent_errors
        }
    })

@app.route('/ready')
def ready_check():
    """Render-compatible readiness check endpoint"""
    try:
        # Basic health check
        db_manager = get_production_db()
        db_health = db_manager.health_check()
        
        # Check if core services are available
        ready = db_health.get('postgres', {}).get('status') == 'healthy'
        
        status_code = 200 if ready else 503
        
        return jsonify({
            'status': 'ready' if ready else 'not_ready',
            'services': {
                'database': ready,
                'application': True
            },
            'port': os.environ.get('PORT', '10000')
        }), status_code
        
    except Exception as e:
        logger.error(f"Ready check failed: {e}")
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'port': os.environ.get('PORT', '10000')
        }), 503

# Create the application
app = create_production_app()

# Celery worker entry point
celery = app.celery

if __name__ == '__main__':
    # For development only - use Gunicorn in production
    port = int(os.environ.get('PORT', 5006))
    
    if app.socketio:
        logger.info(f"Starting production server with WebSockets on port {port}")
        app.socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        logger.info(f"Starting production server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)