#!/usr/bin/env python3
"""
Production-ready server startup script
Handles initialization and error recovery
"""
import os
import sys
import logging
from app import app, register_services, ensure_mcp_initialized
from utils.db_init import initialize_databases

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_server():
    """Start the server with proper initialization"""
    try:
        # Register all services
        logger.info("Registering services...")
        register_services()
        
        # Initialize databases
        logger.info("Initializing databases...")
        with app.app_context():
            initialize_databases(app)
        
        # Initialize MCP servers
        logger.info("Initializing MCP servers...")
        ensure_mcp_initialized()
        
        # Start the server
        port = int(os.environ.get('PORT', 5006))
        logger.info(f"Starting server on port {port}...")
        
        if os.environ.get('PRODUCTION', '').lower() == 'true':
            # Production mode - let Gunicorn handle it
            logger.info("Running in production mode")
            return app
        else:
            # Development mode
            logger.info("Running in development mode")
            app.run(host='0.0.0.0', port=port, debug=True)
            
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_server()