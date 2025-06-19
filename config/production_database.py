"""
Production Database Configuration
Handles PostgreSQL and Redis setup with connection pooling and failover
"""

import os
import redis
from sqlalchemy import create_engine, pool
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager
from urllib.parse import urlparse
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ProductionDatabaseConfig:
    """Production-grade database configuration with PostgreSQL and Redis"""
    
    def __init__(self):
        self.postgres_url = self._get_postgres_url()
        self.redis_url = self._get_redis_url()
        self.postgres_pool = None
        self.redis_pool = None
        
    def _get_postgres_url(self):
        """Get PostgreSQL URL with proper formatting"""
        # Try multiple environment variable names
        db_url = (
            os.environ.get('DATABASE_URL') or
            os.environ.get('POSTGRES_URL') or
            os.environ.get('POSTGRESQL_URL')
        )
        
        if not db_url:
            # Build from components if available
            host = os.environ.get('POSTGRES_HOST', 'localhost')
            port = os.environ.get('POSTGRES_PORT', '5432')
            user = os.environ.get('POSTGRES_USER', 'postgres')
            password = os.environ.get('POSTGRES_PASSWORD', '')
            database = os.environ.get('POSTGRES_DB', 'swarm_db')
            
            if password:
                db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                db_url = f"postgresql://{user}@{host}:{port}/{database}"
        
        # Handle Heroku-style postgres:// URLs
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
            
        return db_url
    
    def _get_redis_url(self):
        """Get Redis URL with proper formatting"""
        redis_url = (
            os.environ.get('REDIS_URL') or
            os.environ.get('REDIS_TLS_URL') or
            os.environ.get('REDISTOGO_URL')
        )
        
        if not redis_url:
            # Build from components
            host = os.environ.get('REDIS_HOST', 'localhost')
            port = os.environ.get('REDIS_PORT', '6379')
            password = os.environ.get('REDIS_PASSWORD', '')
            db = os.environ.get('REDIS_DB', '0')
            
            if password:
                redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                redis_url = f"redis://{host}:{port}/{db}"
                
        return redis_url
    
    def get_postgres_engine_config(self):
        """Get PostgreSQL engine configuration with connection pooling"""
        return {
            # Connection pool settings
            'pool_size': int(os.environ.get('POSTGRES_POOL_SIZE', '10')),
            'max_overflow': int(os.environ.get('POSTGRES_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.environ.get('POSTGRES_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.environ.get('POSTGRES_POOL_RECYCLE', '3600')),
            'pool_pre_ping': True,  # Test connections before using
            
            # Connection args
            'connect_args': {
                'connect_timeout': 10,
                'application_name': 'swarm_mcp',
                'options': '-c statement_timeout=30000',  # 30 second timeout
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            },
            
            # Performance settings
            'echo_pool': os.environ.get('DEBUG', '').lower() == 'true',
            'execution_options': {
                'isolation_level': 'AUTOCOMMIT'
            }
        }
    
    def get_redis_pool(self):
        """Get Redis connection pool"""
        if not self.redis_pool:
            parsed = urlparse(self.redis_url)
            
            pool_kwargs = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 6379,
                'db': int(parsed.path.lstrip('/') or 0),
                'password': parsed.password,
                'socket_timeout': 5,
                'socket_connect_timeout': 5,
                'socket_keepalive': True,
                'socket_keepalive_options': {},
                'connection_pool_kwargs': {
                    'max_connections': int(os.environ.get('REDIS_MAX_CONNECTIONS', '50')),
                    'retry_on_timeout': True,
                    'health_check_interval': 30,
                }
            }
            
            # Handle Redis TLS/SSL
            if 'rediss' in self.redis_url or 'REDIS_TLS_URL' in os.environ:
                pool_kwargs['ssl'] = True
                pool_kwargs['ssl_cert_reqs'] = 'required'
                
            self.redis_pool = redis.ConnectionPool(**pool_kwargs)
            
        return self.redis_pool
    
    def get_redis_client(self, decode_responses=True):
        """Get Redis client with connection pool"""
        return redis.Redis(
            connection_pool=self.get_redis_pool(),
            decode_responses=decode_responses
        )
    
    def test_postgres_connection(self):
        """Test PostgreSQL connection"""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.postgres_url, **self.get_postgres_engine_config())
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("PostgreSQL connection successful")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False
    
    def test_redis_connection(self):
        """Test Redis connection"""
        try:
            r = self.get_redis_client()
            r.ping()
            logger.info("Redis connection successful")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False
    
    def get_celery_config(self):
        """Get Celery configuration for production"""
        return {
            'broker_url': self.redis_url,
            'result_backend': self.redis_url,
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            'timezone': 'UTC',
            'enable_utc': True,
            'broker_connection_retry_on_startup': True,
            'broker_connection_retry': True,
            'broker_connection_max_retries': 10,
            'worker_prefetch_multiplier': 4,
            'worker_max_tasks_per_child': 1000,
            'task_acks_late': True,
            'task_reject_on_worker_lost': True,
            'task_time_limit': 300,  # 5 minutes
            'task_soft_time_limit': 270,  # 4.5 minutes
            'result_expires': 3600,  # 1 hour
        }

class DatabaseConnectionManager:
    """Manages database connections with failover and health checks"""
    
    def __init__(self):
        self.config = ProductionDatabaseConfig()
        self._postgres_engine = None
        self._redis_client = None
        
    @property
    def postgres_engine(self):
        """Get or create PostgreSQL engine"""
        if not self._postgres_engine:
            from sqlalchemy import create_engine
            self._postgres_engine = create_engine(
                self.config.postgres_url,
                **self.config.get_postgres_engine_config()
            )
        return self._postgres_engine
    
    @property
    def redis_client(self):
        """Get or create Redis client"""
        if not self._redis_client:
            self._redis_client = self.config.get_redis_client()
        return self._redis_client
    
    @contextmanager
    def get_db_session(self):
        """Get database session with automatic cleanup"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.postgres_engine)
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def health_check(self):
        """Check health of all database connections"""
        status = {
            'postgres': False,
            'redis': False,
            'errors': []
        }
        
        # Check PostgreSQL
        try:
            with self.postgres_engine.connect() as conn:
                conn.execute("SELECT 1")
            status['postgres'] = True
        except Exception as e:
            status['errors'].append(f"PostgreSQL: {str(e)}")
        
        # Check Redis
        try:
            self.redis_client.ping()
            status['redis'] = True
        except Exception as e:
            status['errors'].append(f"Redis: {str(e)}")
        
        status['healthy'] = status['postgres'] and status['redis']
        return status

# Global instance
_db_manager = None

def get_production_db():
    """Get or create production database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
    return _db_manager

def init_production_database(app):
    """Initialize Flask app with production database"""
    db_manager = get_production_db()
    
    # Set SQLAlchemy config
    app.config['SQLALCHEMY_DATABASE_URI'] = db_manager.config.postgres_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = db_manager.config.get_postgres_engine_config()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Set Redis config
    app.config['REDIS_URL'] = db_manager.config.redis_url
    
    # Set Celery config
    app.config.update(db_manager.config.get_celery_config())
    
    logger.info("Production database configuration initialized")
    
    # Run health check
    health = db_manager.health_check()
    if not health['healthy']:
        logger.warning(f"Database health check failed: {health['errors']}")
    
    return db_manager