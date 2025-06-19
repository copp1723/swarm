# High Priority Implementation Plan

## 🚨 P0: Security Implementation (4-6 hours)

### 1. Basic API Key Authentication
```python
# utils/auth.py
import os
import secrets
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
import jwt

class AuthManager:
    def __init__(self, app):
        self.app = app
        self.secret_key = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        
    def generate_api_key(self, user_id):
        """Generate a new API key for a user"""
        return f"swarm_{user_id}_{secrets.token_urlsafe(32)}"
    
    def generate_jwt_token(self, user_id, expires_in=3600):
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key
        api_key = request.headers.get('X-API-Key')
        if api_key and validate_api_key(api_key):
            return f(*args, **kwargs)
        
        # Check for JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer TOKEN
                payload = auth_manager.verify_jwt_token(token)
                if payload:
                    request.user_id = payload['user_id']
                    return f(*args, **kwargs)
            except:
                pass
        
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function

def require_role(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # Check user role from database
            user_role = get_user_role(request.user_id)
            if user_role != role:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 2. Rate Limiting
```python
# utils/rate_limiter.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def setup_rate_limiting(app):
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="redis://localhost:6379"  # Use Redis for distributed limiting
    )
    
    # Specific limits for sensitive endpoints
    @limiter.limit("5 per minute")
    @app.route("/api/agents/execute", methods=["POST"])
    @require_auth
    def execute_agent():
        pass
    
    return limiter
```

### 3. Request Signing for Webhooks
```python
# utils/webhook_security.py
import hmac
import hashlib
import time

class WebhookSecurity:
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def generate_signature(self, payload, timestamp):
        """Generate HMAC signature for webhook"""
        message = f"{timestamp}.{payload}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, payload, signature, timestamp):
        """Verify webhook signature"""
        # Check timestamp is within 5 minutes
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            return False
        
        expected_signature = self.generate_signature(payload, timestamp)
        return hmac.compare_digest(expected_signature, signature)
```

---

## 🚨 P0: Error Recovery & Resilience (3-4 hours)

### 1. Circuit Breaker Pattern
```python
# utils/circuit_breaker.py
from datetime import datetime, timedelta
from enum import Enum
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self):
        return (
            self.last_failure_time and
            datetime.utcnow() > self.last_failure_time + timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage in multi_agent_executor.py
class EnhancedMultiAgentExecutor:
    def __init__(self):
        self.circuit_breakers = {}
        
    def get_circuit_breaker(self, agent_id):
        if agent_id not in self.circuit_breakers:
            self.circuit_breakers[agent_id] = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=30
            )
        return self.circuit_breakers[agent_id]
    
    async def execute_with_circuit_breaker(self, agent_id, task):
        breaker = self.get_circuit_breaker(agent_id)
        try:
            return await breaker.call(self._execute_agent, agent_id, task)
        except Exception as e:
            # Try fallback agent
            fallback_agent = self.get_fallback_agent(agent_id)
            if fallback_agent:
                logger.warning(f"Agent {agent_id} failed, trying fallback {fallback_agent}")
                return await self.execute_with_circuit_breaker(fallback_agent, task)
            raise e
```

### 2. Retry with Exponential Backoff
```python
# utils/retry_handler.py
import asyncio
import random
from functools import wraps

class RetryHandler:
    @staticmethod
    def async_retry(max_attempts=3, base_delay=1, max_delay=60, exponential_base=2, jitter=True):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                attempt = 0
                while attempt < max_attempts:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise e
                        
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                        
                        # Add jitter to prevent thundering herd
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}, "
                            f"retrying in {delay:.2f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                
            return wrapper
        return decorator

# Usage
@RetryHandler.async_retry(max_attempts=3, base_delay=2)
async def execute_agent_task(agent_id, task):
    return await agent.execute(task)
```

### 3. Dead Letter Queue
```python
# utils/dead_letter_queue.py
import json
from datetime import datetime
from models.core import db

class DeadLetterQueue:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.use_redis = redis_client is not None
        
    async def add_failed_task(self, task_id, agent_id, task_data, error, attempt_count):
        """Add failed task to dead letter queue"""
        failed_task = {
            'task_id': task_id,
            'agent_id': agent_id,
            'task_data': task_data,
            'error': str(error),
            'attempt_count': attempt_count,
            'failed_at': datetime.utcnow().isoformat(),
            'status': 'failed'
        }
        
        if self.use_redis:
            # Store in Redis for quick access
            await self.redis.lpush('dlq:failed_tasks', json.dumps(failed_task))
        
        # Also store in database for persistence
        from models.agent_task import FailedTask
        db_task = FailedTask(**failed_task)
        db.session.add(db_task)
        db.session.commit()
        
        # Send alert if critical task
        if task_data.get('priority') == 'critical':
            await self.send_critical_failure_alert(failed_task)
    
    async def retry_failed_tasks(self, max_tasks=10):
        """Retry failed tasks from DLQ"""
        if self.use_redis:
            tasks = []
            for _ in range(max_tasks):
                task_json = await self.redis.rpop('dlq:failed_tasks')
                if task_json:
                    tasks.append(json.loads(task_json))
                else:
                    break
            return tasks
        else:
            # Fallback to database
            from models.agent_task import FailedTask
            tasks = FailedTask.query.filter_by(status='failed').limit(max_tasks).all()
            return [task.to_dict() for task in tasks]
```

---

## 🟡 P1: Quick Database Optimizations (1-2 hours)

### 1. Add Indexes
```python
# migrations/add_performance_indexes.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add indexes for common queries
    op.create_index('idx_conversation_session_id', 'conversations', ['session_id'])
    op.create_index('idx_conversation_updated', 'conversations', ['updated_at'])
    op.create_index('idx_message_conversation_id', 'messages', ['conversation_id'])
    op.create_index('idx_message_created', 'messages', ['created_at'])
    op.create_index('idx_agent_task_status', 'agent_tasks', ['status', 'created_at'])
    op.create_index('idx_workflow_status', 'workflows', ['status'])
    
    # Composite indexes for common join queries
    op.create_index('idx_message_conv_created', 'messages', ['conversation_id', 'created_at'])

def downgrade():
    # Remove indexes
    op.drop_index('idx_conversation_session_id')
    # ... etc
```

### 2. Connection Pooling
```python
# config/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def setup_database(app):
    # Optimal pool configuration
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,          # Number of connections to maintain
        'pool_recycle': 3600,     # Recycle connections after 1 hour
        'pool_pre_ping': True,    # Test connections before using
        'max_overflow': 20,       # Maximum overflow connections
        'pool_timeout': 30,       # Timeout for getting connection
        'echo_pool': app.debug,   # Log pool checkouts/checkins
    }
    
    # For PostgreSQL, add additional optimizations
    if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'].update({
            'connect_args': {
                'connect_timeout': 10,
                'application_name': 'swarm_app',
                'options': '-c statement_timeout=30000'  # 30 second statement timeout
            }
        })
```

### 3. Query Result Caching
```python
# utils/cache_manager.py
import hashlib
import json
from functools import wraps

class CacheManager:
    def __init__(self, redis_client=None, default_ttl=300):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.local_cache = {}  # Fallback in-memory cache
    
    def cache_result(self, key_prefix, ttl=None):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(key_prefix, args, kwargs)
                
                # Try to get from cache
                cached = await self._get_from_cache(cache_key)
                if cached is not None:
                    return cached
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self._store_in_cache(cache_key, result, ttl or self.default_ttl)
                
                return result
            return wrapper
        return decorator
    
    def _generate_key(self, prefix, args, kwargs):
        # Create unique key from function arguments
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

# Usage
cache_manager = CacheManager(redis_client)

@cache_manager.cache_result('agent_list', ttl=600)
async def get_available_agents():
    # This expensive query will be cached for 10 minutes
    return Agent.query.filter_by(active=True).all()
```

These implementations address the most critical weaknesses and can be rolled out incrementally without disrupting the existing system.