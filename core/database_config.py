"""
Centralized Database Configuration
Simplifies database setup and configuration
"""
import os
from typing import Dict, Any
from flask import Flask
from sqlalchemy.engine import Engine


class DatabaseConfig:
    """Manages database configuration and connection settings"""
    
    @staticmethod
    def get_database_url(app: Flask) -> str:
        """Get database URL with proper defaults"""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        instance_dir = os.path.join(backend_dir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        
        default_db_path = f'sqlite:///{os.path.join(instance_dir, "mcp_executive.db")}'
        return os.environ.get('DATABASE_URL', default_db_path)
    
    @staticmethod
    def get_engine_options(database_url: str, debug: bool = False) -> Dict[str, Any]:
        """Get optimized engine options based on database type"""
        is_postgres = any(db in database_url for db in ['postgresql', 'postgres'])
        
        if is_postgres:
            return {
                'pool_size': 10,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'max_overflow': 20,
                'pool_timeout': 30,
                'echo_pool': debug,
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'swarm_app',
                    'options': '-c statement_timeout=30000'
                }
            }
        else:  # SQLite
            return {
                'pool_recycle': 300,
                'pool_pre_ping': True,
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 15
                }
            }
    
    @staticmethod
    def configure_database(app: Flask) -> None:
        """Configure all database settings for the Flask app"""
        # Basic settings
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Database URL
        database_url = DatabaseConfig.get_database_url(app)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        
        # Engine options
        engine_options = DatabaseConfig.get_engine_options(database_url, app.debug)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
        
        # File upload settings (related to database storage)
        app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
        app.config['UPLOAD_FOLDER'] = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'uploads'
        )
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)