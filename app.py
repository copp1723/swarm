#!/usr/bin/env python3
"""
MCP Executive Interface Backend Server - New Modular Project
Streamlined app with modular architecture and dependency injection
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Add Homebrew path for npx/node
os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

# Load environment variables first
load_dotenv(dotenv_path='config/.env')

# Setup centralized logging with Loguru
from utils.logging_config import setup_logging, get_logger
logger = None

# Import startup validation
from utils.startup_validation import validate_startup

import asyncio
from core.dependency_injection import get_container
from core.service_registry import initialize_services, get_service
from core.base_implementations import ServiceLifecycleManager
from utils.async_wrapper import async_manager
from utils.websocket import init_socketio
from config.celery_config import make_celery

# Import security utilities
from utils.auth import auth_manager, require_auth, optional_auth, generate_default_api_key
from utils.rate_limiter import add_rate_limit_headers, standard_rate_limit

# Import memory optimization
from utils.memory_optimizer import setup_memory_management, get_memory_monitor

# Import security-headers middleware (CSP, HSTS, etc.)
from middleware.security_headers import init_security_headers
# Import models
from models.core import db
from utils.db_init import initialize_databases

# Import blueprints
from routes.chat import chat_bp
from routes.mcp import mcp_bp
from routes.files import files_bp
from routes.agents import agents_bp
from routes.async_demo import async_demo_bp
from routes.tasks import tasks_bp
from routes.memory import memory_bp
from routes.memory_api import memory_api_bp
from routes.workflows import workflows_bp
from routes.zen import zen_bp
from routes.templates import templates_bp
from routes.monitoring import monitoring_bp
from routes.email import email_api_bp
from routes.plugins import plugins_bp
from routes.audit import audit_bp

# Import Email Agent
from services.email_agent import email_bp, register_email_agent

app = Flask(__name__, static_folder='static')
# Fix CORS to allow all origins during development
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

# --------------------------------------------------------------------------- #
# Initialize comprehensive security headers (CSP, HSTS, etc.)
# --------------------------------------------------------------------------- #
env = os.getenv("FLASK_ENV", "production").lower()
init_security_headers(
    app,
    hsts_enabled=(env == "production"),
    hsts_preload=(env == "production"),
)

# Initialize logging with Flask app for Sentry integration
setup_logging(app_name="mcp_executive", flask_app=app)
logger = get_logger(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'mcp-executive-secret-key')
backend_dir = os.path.dirname(os.path.abspath(__file__))
instance_dir = os.path.join(backend_dir, "instance")
os.makedirs(instance_dir, exist_ok=True)
default_db_path = f'sqlite:///{os.path.join(instance_dir, "mcp_executive.db")}'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_db_path)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enhanced connection pooling configuration
if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] or 'postgres' in app.config['SQLALCHEMY_DATABASE_URI']:
    # PostgreSQL optimizations
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,          # Number of connections to maintain
        'pool_recycle': 3600,     # Recycle connections after 1 hour
        'pool_pre_ping': True,    # Test connections before using
        'max_overflow': 20,       # Maximum overflow connections
        'pool_timeout': 30,       # Timeout for getting connection
        'echo_pool': app.debug,   # Log pool checkouts/checkins in debug
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'swarm_app',
            'options': '-c statement_timeout=30000'  # 30 second statement timeout
        }
    }
else:
    # SQLite optimizations
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'connect_args': {
            'check_same_thread': False,  # Allow multiple threads
            'timeout': 15  # 15 second busy timeout
        }
    }
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db.init_app(app)

# Initialize authentication
auth_manager.init_app(app)

# Generate and log a development API key if in debug mode
if app.debug and not os.environ.get('SWARM_DEV_API_KEY'):
    dev_key = generate_default_api_key()
    os.environ['SWARM_DEV_API_KEY'] = dev_key
    logger.info(f"Development API Key: {dev_key}")
    logger.info("Use header 'X-API-Key: {key}' for authenticated requests")

# Initialize Celery
celery = make_celery(app)

# Initialize WebSocket support
socketio = init_socketio(app)

# Register blueprints
app.register_blueprint(chat_bp)
app.register_blueprint(mcp_bp)
app.register_blueprint(files_bp)
app.register_blueprint(agents_bp)
app.register_blueprint(async_demo_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(memory_bp)
app.register_blueprint(memory_api_bp)
app.register_blueprint(workflows_bp)
app.register_blueprint(zen_bp)
app.register_blueprint(templates_bp)
app.register_blueprint(monitoring_bp)
app.register_blueprint(email_api_bp)
app.register_blueprint(plugins_bp)
app.register_blueprint(audit_bp)

# Register Email Agent
register_email_agent(app)

# Service lifecycle manager
lifecycle_manager = ServiceLifecycleManager()

# Initialize MCP servers flag
_services_initialized = False

def initialize_application_services():
    """Initialize all application services using dependency injection"""
    global _services_initialized
    if _services_initialized:
        return
    
    try:
        # Initialize the service container
        container = initialize_services()
        
        # Register Flask app and database in container
        container.register_singleton('flask_app', app)
        container.register_singleton('db', db)
        container.register_singleton('celery', celery)
        container.register_singleton('socketio', socketio)
        
        # Get core services that need initialization
        services_to_init = [
            'event_bus',
            'cache',
            'monitoring',
            'mcp_manager',
        ]
        
        # Setup memory management
        memory_monitor, memory_optimizer = setup_memory_management(app)
        container.register_singleton('memory_monitor', memory_monitor)
        container.register_singleton('memory_optimizer', memory_optimizer)
        
        # Add services to lifecycle manager
        for service_name in services_to_init:
            service = get_service(service_name)
            if service and hasattr(service, 'initialize'):
                lifecycle_manager.add_service(service)
        
        # Initialize plugin system
        plugin_loader = get_service('plugin_loader')
        if plugin_loader:
            # Add default plugin directory
            plugin_dir = os.path.join(os.path.dirname(__file__), 'plugins')
            if os.path.exists(plugin_dir):
                plugin_loader.add_plugin_directory(plugin_dir)
                logger.info(f"Added plugin directory: {plugin_dir}")
            
            # Start plugin discovery
            async_manager.run_sync(plugin_loader.discover_and_load_plugins())
            async_manager.run_sync(plugin_loader.start_watching())
            logger.info("Plugin system initialized")
        
        # Initialize all services
        async_manager.run_sync(lifecycle_manager.initialize_all())

        # ------------------------------------------------------------------ #
        # Initialise services that require an async startup step
        # ------------------------------------------------------------------ #
        container = get_container()
        if hasattr(container, '_async_init_services'):
            logger.info("Starting async service initialization...")
            for service_name in container._async_init_services:
                service = get_service(service_name)
                if service and hasattr(service, 'initialize'):
                    try:
                        async_manager.run_sync(service.initialize())
                        logger.info(f"Async initialized: {service_name}")
                    except Exception as e:
                        logger.error(f"Failed to async initialize {service_name}: {e}")
                        raise
        
        # Start MCP servers
        mcp_manager = get_service('mcp_manager')
        if mcp_manager:
            logger.info("Initializing MCP servers...")
            async_manager.run_sync(mcp_manager.start_all_servers())
        
        _services_initialized = True
        logger.info("All application services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.route('/workflows')
def serve_workflows():
    """Serve the workflow templates interface"""
    return app.send_static_file('workflows.html')

@app.route('/virtual-chat-test.html')
def virtual_chat_test():
    """Serve the virtual chat performance test page"""
    return app.send_static_file('virtual-chat-test.html')

@app.route('/task_demo.html')
def task_demo():
    """Serve the task management demo page"""
    return app.send_static_file('task_demo.html')

@app.route('/')
def serve_index():
    """Serve the main multi-agent interface"""
    return app.send_static_file('index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files"""
    if filename.startswith('api/'):
        from flask import abort
        abort(404)
    return send_from_directory(app.static_folder, filename)

@app.route('/health')
@async_manager.async_route
async def health_check():
    """Health check endpoint using async database"""
    from flask import jsonify
    from datetime import datetime
    import time
    
    start_time = time.time()
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'unknown',
        'async_database': 'unknown',
        'mcp_servers': 'unknown',
        'services': {}
    }
    
    # Check sync database
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check async database
    try:
        from repositories.async_repositories import AsyncSystemLogRepository
        await AsyncSystemLogRepository.log_event(
            event_type='health_check',
            event_source='app',
            message='Health check performed',
            additional_data={'endpoint': '/health'}
        )
        health_status['async_database'] = 'connected'
    except Exception as e:
        health_status['async_database'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check MCP servers
    mcp_manager = get_service('mcp_manager')
    if mcp_manager:
        health_status['mcp_servers'] = 'initialized'
        health_status['services']['mcp_manager'] = 'active'
    else:
        health_status['mcp_servers'] = 'not initialized'
        health_status['services']['mcp_manager'] = 'missing'
    
    # Check other critical services
    critical_services = ['cache', 'event_bus', 'monitoring', 'notification_service']
    for service_name in critical_services:
        service = get_service(service_name)
        health_status['services'][service_name] = 'active' if service else 'missing'
    
    # Add memory stats
    memory_monitor = get_service('memory_monitor')
    if memory_monitor:
        memory_stats = memory_monitor.get_memory_stats()
        health_status['memory'] = {
            'usage_mb': round(memory_stats['memory_used_mb'], 1),
            'percent': round(memory_stats['memory_percent'], 1)
        }
    
    # Add response time
    health_status['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
    
    return jsonify(health_status)

@app.teardown_appcontext
def shutdown_services(error=None):
    """Cleanup services on app context teardown"""
    # Services are managed at app level, not request level
    pass

@app.after_request
def after_request(response):
    """Add security headers and rate limit info to responses"""
    # Add rate limit headers
    add_rate_limit_headers(response)

    return response

if __name__ == '__main__':
    # Run startup validation
    logger.info("Running startup validation...")
    if not validate_startup(exit_on_error=False):
        logger.warning("Startup validation had warnings/errors, continuing anyway...")
    
    # Initialize databases
    with app.app_context():
        initialize_databases(app)
        logger.info("All databases initialized successfully")
    
    # Initialize all application services
    initialize_application_services()

    port = int(os.environ.get('PORT', 5006))
    
    # Use SocketIO run method instead of Flask run for WebSocket support
    socketio.run(app, host='0.0.0.0', port=port, debug=True)