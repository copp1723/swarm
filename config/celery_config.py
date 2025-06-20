"""
Celery Configuration for MCP Executive Interface
Handles long-running agent tasks and background operations
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

# Redis configuration
def get_redis_url(db_number=0):
    """Get Redis URL with proper database number handling"""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # If URL already has a database number, replace it
    # Otherwise append the database number
    if redis_url.endswith(('/0', '/1', '/2', '/3', '/4', '/5', '/6', '/7', '/8', '/9')):
        # Remove existing database number
        redis_url = redis_url.rsplit('/', 1)[0]
    
    return f"{redis_url}/{db_number}"

REDIS_URL = get_redis_url(0)  # Main Redis database
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', get_redis_url(1))  # Celery broker on db 1
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', get_redis_url(1))  # Celery results on db 1

def make_celery(app=None):
    """Create Celery instance with Flask app context"""
    celery = Celery(
        'mcp_executive',
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
        include=[
            'tasks.agent_tasks', 
            'tasks.analysis_tasks',
            'tasks.email_tasks',
            'tasks.webhook_tasks',
            'tasks.memory_tasks',
            'tasks.maintenance_tasks'
        ]
    )
    
    # Configure Celery
    celery.conf.update(
        # Task serialization
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Task routing
        task_routes={
            'tasks.agent_tasks.*': {'queue': 'agent_queue'},
            'tasks.analysis_tasks.*': {'queue': 'analysis_queue'},
            'tasks.email_tasks.*': {'queue': 'email_queue'},
            'tasks.webhook_tasks.*': {'queue': 'webhook_queue'},
            'tasks.memory_tasks.*': {'queue': 'memory_queue'},
            'tasks.maintenance_tasks.*': {'queue': 'maintenance_queue'},
        },
        
        # Worker configuration
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        
        # Task time limits
        task_soft_time_limit=300,  # 5 minutes
        task_time_limit=600,       # 10 minutes
        
        # Result backend settings
        result_expires=3600,       # 1 hour
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Beat schedule for periodic tasks
        beat_schedule={
            'cleanup-expired-tokens': {
                'task': 'tasks.maintenance_tasks.cleanup_expired_tokens',
                'schedule': 3600.0,  # Every hour
            },
            'sync-agent-memories': {
                'task': 'tasks.memory_tasks.sync_agent_memories',
                'schedule': 300.0,  # Every 5 minutes
            },
        }
    )
    
    # Update task base classes if Flask app provided
    if app:
        class ContextTask(celery.Task):
            """Make celery tasks work with Flask app context"""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# Create global Celery instance
celery_app = make_celery()

# Export for easy import
__all__ = ['celery_app', 'make_celery']