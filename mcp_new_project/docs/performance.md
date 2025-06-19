# Performance Optimization Guide

This guide covers performance optimizations, monitoring, and best practices for the SWARM system.

## 🚀 Performance Improvements Implemented

### 1. Database Connection Pooling
The centralized database manager provides optimized connection pooling:

```python
from utils.db_connection import get_db_manager

# Automatically uses connection pooling
db = get_db_manager()

# Pool configuration (PostgreSQL)
pool_kwargs = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600,  # Recycle connections after 1 hour
    'pool_pre_ping': True   # Verify connections before use
}
```

### 2. Async Architecture
Improved async/sync bridge with cached thread pools:

```python
from utils.async_bridge import AsyncBridge

# Cached thread pool executor (reused across calls)
async_bridge = AsyncBridge()

# Efficient async-to-sync conversion
result = await async_bridge.run_async(async_function, *args)
```

### 3. Lazy Loading
Prevents circular imports and reduces startup time:

```python
# In blueprint_registry.py
def _lazy_import(module_path: str):
    """Lazy import to avoid circular dependencies"""
    module = importlib.import_module(module_path)
    return getattr(module, f"{module_path.split('.')[-1]}_bp")
```

## 📊 Monitoring & Metrics

### 1. Request Performance Logging
```python
from utils.logging_setup import get_logger
import time

logger = get_logger(__name__)

@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def log_request_time(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        logger.info(f"{request.method} {request.path} - {elapsed:.3f}s")
    return response
```

### 2. Database Query Monitoring
```python
# Enable query logging in development
if app.debug:
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Log slow queries
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 1.0:  # Log queries over 1 second
        logger.warning(f"Slow query ({total:.3f}s): {statement[:100]}...")
```

### 3. Memory Usage Tracking
```python
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return {
        'memory_percent': process.memory_percent(),
        'memory_mb': process.memory_info().rss / 1024 / 1024,
        'cpu_percent': process.cpu_percent(interval=1)
    }

# Add to health endpoint
@app.route('/api/health')
def health_check():
    return {
        'status': 'healthy',
        'metrics': get_memory_usage(),
        'timestamp': datetime.utcnow().isoformat()
    }
```

## ⚡ Optimization Techniques

### 1. Caching Strategies

#### In-Memory Caching
```python
from functools import lru_cache
from cachetools import TTLCache

# LRU cache for frequently accessed data
@lru_cache(maxsize=128)
def get_agent_config(agent_id: str):
    return load_agent_config(agent_id)

# Time-based cache for API responses
response_cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes

@app.route('/api/agents/list')
def list_agents():
    if 'agents_list' in response_cache:
        return response_cache['agents_list']
    
    result = compute_agents_list()
    response_cache['agents_list'] = result
    return result
```

#### Redis Caching
```python
import redis
import json

redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

def cache_result(key: str, data: dict, ttl: int = 300):
    redis_client.setex(key, ttl, json.dumps(data))

def get_cached(key: str):
    data = redis_client.get(key)
    return json.loads(data) if data else None
```

### 2. Database Optimization

#### Index Creation
```python
# Add indexes for frequently queried columns
from sqlalchemy import Index

class CompletedTask(db.Model):
    __tablename__ = 'completed_tasks'
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_task_status_created', 'status', 'created_at'),
        Index('idx_task_agent_id', 'agent_id'),
        Index('idx_task_user_created', 'user_id', 'created_at'),
    )
```

#### Query Optimization
```python
# Bad: N+1 query problem
tasks = Task.query.all()
for task in tasks:
    print(task.user.name)  # Additional query per task

# Good: Eager loading
tasks = Task.query.options(joinedload(Task.user)).all()
for task in tasks:
    print(task.user.name)  # No additional queries

# Use pagination for large datasets
page = request.args.get('page', 1, type=int)
per_page = 20
tasks = Task.query.paginate(page=page, per_page=per_page)
```

### 3. Async Task Processing

#### Background Jobs with Celery
```python
from celery import Celery

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])

@celery.task
def process_heavy_task(task_id):
    # Move heavy processing to background
    result = perform_expensive_operation()
    save_result(task_id, result)
    return result

# In your route
@app.route('/api/process', methods=['POST'])
def start_processing():
    task = process_heavy_task.delay(task_id)
    return {'task_id': task.id, 'status': 'processing'}
```

### 4. Response Optimization

#### Compression
```python
from flask_compress import Compress

Compress(app)  # Automatically compresses responses
```

#### Pagination
```python
from utils.api_response import APIResponse

@app.route('/api/tasks')
def list_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Task.query.filter_by(status='active')
    paginated = query.paginate(page=page, per_page=per_page)
    
    return APIResponse.paginated(
        items=[task.to_dict() for task in paginated.items],
        page=page,
        per_page=per_page,
        total=paginated.total
    )
```

## 🔥 Production Optimization

### 1. Gunicorn Configuration
```python
# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:5006"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
timeout = 30
graceful_timeout = 30
preload_app = True

# Enable statsd metrics
statsd_host = "localhost:8125"
statsd_prefix = "swarm"
```

### 2. Nginx Configuration
```nginx
upstream swarm_backend {
    server localhost:5006;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Enable gzip compression
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1000;
    
    # Cache static files
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Proxy to backend
    location / {
        proxy_pass http://swarm_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. Database Optimizations

#### Connection Pooling (Production)
```python
# For PostgreSQL in production
DATABASE_URL = "postgresql://user:pass@localhost/db?pool_size=20&max_overflow=40"

# Or configure programmatically
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo_pool=True  # Log pool checkouts/checkins
)
```

## 📈 Performance Monitoring

### 1. Application Performance Monitoring (APM)
```python
# Using built-in metrics
@app.route('/api/metrics')
def metrics():
    return {
        'database': {
            'pool_size': db.engine.pool.size(),
            'checked_out_connections': db.engine.pool.checkedout(),
            'overflow': db.engine.pool.overflow(),
            'total': db.engine.pool.checkedin()
        },
        'memory': get_memory_usage(),
        'cache': {
            'hits': cache_hits,
            'misses': cache_misses,
            'hit_rate': cache_hits / (cache_hits + cache_misses)
        }
    }
```

### 2. Logging Performance Metrics
```python
from utils.logging_setup import get_logger

logger = get_logger('performance')

# Log performance metrics periodically
def log_performance_metrics():
    metrics = {
        'memory_mb': get_memory_usage()['memory_mb'],
        'active_tasks': Task.query.filter_by(status='active').count(),
        'db_connections': db.engine.pool.checkedout(),
        'cache_size': len(response_cache)
    }
    logger.info(f"Performance metrics: {json.dumps(metrics)}")
```

## 🎯 Performance Best Practices

### 1. API Design
- Use pagination for list endpoints
- Implement field filtering to reduce payload size
- Cache frequently accessed, rarely changing data
- Use ETags for conditional requests

### 2. Database
- Add indexes for frequently queried columns
- Use eager loading to prevent N+1 queries
- Implement database connection pooling
- Regular VACUUM and ANALYZE (PostgreSQL)

### 3. Caching
- Cache at multiple levels (application, Redis, CDN)
- Set appropriate TTLs based on data volatility
- Implement cache warming for critical data
- Monitor cache hit rates

### 4. Async Processing
- Move heavy operations to background tasks
- Use queues for non-critical operations
- Implement proper timeout handling
- Monitor queue lengths and processing times

### 5. Monitoring
- Set up alerts for slow queries
- Monitor memory usage trends
- Track API response times
- Watch for connection pool exhaustion

## 🔧 Debugging Performance Issues

### 1. Profiling Requests
```python
from werkzeug.middleware.profiler import ProfilerMiddleware

if app.debug:
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, profile_dir='./profiles')
```

### 2. Query Analysis
```python
# Log all SQL queries in development
app.config['SQLALCHEMY_ECHO'] = True

# Or use Flask-SQLAlchemy's get_debug_queries()
from flask_sqlalchemy import get_debug_queries

@app.after_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= 0.5:
            app.logger.warning(f"Slow query: {query.statement} [{query.duration}s]")
    return response
```

## 📊 Performance Targets

### Recommended Targets
- API Response Time: < 200ms (p95)
- Database Query Time: < 100ms (p95)
- Memory Usage: < 512MB per worker
- CPU Usage: < 70% sustained
- Cache Hit Rate: > 80%
- Error Rate: < 0.1%

### Monitoring Tools
- Application: Built-in `/api/metrics` endpoint
- Infrastructure: Prometheus + Grafana
- Logs: ELK Stack or CloudWatch
- APM: New Relic or DataDog (optional)