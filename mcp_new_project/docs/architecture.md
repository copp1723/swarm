# System Architecture Guide

## Overview

The MCP Multi-Agent Chat System is built on a modern, scalable architecture that combines Flask for web services, SQLAlchemy for data persistence, Celery for background tasks, and a sophisticated multi-agent AI system powered by various LLM providers.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐        │
│  │   Web UI    │  │   REST API   │  │   WebSocket   │        │
│  └─────────────┘  └──────────────┘  └───────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                       Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Flask App  │  │   Blueprints │  │   Middleware  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │     NLU      │  │ Orchestrator │  │  Multi-Agent  │        │
│  │   Service    │  │   Service    │  │   Executor    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │     MCP      │  │    Audit     │  │    Plugin     │        │
│  │   Manager    │  │   System     │  │    System     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Database   │  │    Redis     │  │   Celery     │        │
│  │  (SQLAlchemy)│  │   (Cache)    │  │  (Workers)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Application Core (`app.py`)

The main Flask application with optimized configuration:

```python
# Centralized configuration
from core.database_config import DatabaseConfig
from core.blueprint_registry import BlueprintRegistry
from middleware.security_headers import init_security_headers
from utils.logging_setup import setup_logging
from utils.db_connection import init_db

# Initialize logging first
setup_logging()

# Initialize Flask app
app = Flask(__name__)

# Configure database
DatabaseConfig.configure(app)
init_db(app)

# Security headers
init_security_headers(app)

# Register blueprints
BlueprintRegistry.register_all_blueprints(app)
```

**Key Features:**
- Centralized blueprint registration
- Unified database configuration with connection pooling
- Automatic security headers on all responses
- Centralized logging configuration
- Session management
- Error handling middleware

### 2. Service Layer

#### Multi-Agent Executor (`services/multi_agent_executor.py`)
Coordinates AI agents for task execution:
- Agent selection and routing
- Conversation management
- Task orchestration
- Result aggregation

#### NLU Service (`services/nlu_service.py`)
Natural Language Understanding for intelligent routing:
- Intent classification (12 types)
- Entity extraction
- Context analysis
- Technology detection

#### Orchestrator Service (`services/orchestrator_service.py`)
Intelligent task planning and execution:
- Workflow generation
- Agent assignment
- Progress tracking
- Error recovery

#### MCP Manager (`services/mcp_manager.py`)
Model Context Protocol integration:
- Filesystem access
- Tool execution
- Server lifecycle management
- Resource pooling

### 3. Infrastructure Components

#### Dependency Injection (`core/simple_di.py`)
Simplified DI container with:
- Singleton pattern
- Factory pattern
- Service locator
- Lifecycle management

#### Async Bridge (`utils/async_bridge.py`)
Standardized async/sync operations:
- Event loop detection
- Thread pool caching
- Route decorators
- Resource cleanup

#### Database Layer (`utils/db_connection.py`)
Centralized database management:
```python
from utils.db_connection import get_db_manager

db = get_db_manager()
# Automatic connection pooling
# Transaction management
# Both sync and async support
```

#### Logging System (`utils/logging_setup.py`)
Unified logging configuration:
```python
from utils.logging_setup import get_logger

logger = get_logger(__name__)
# Colored console output
# JSON formatting option
# Automatic rotation
# Performance logging
```

#### Response Formatting (`utils/api_response.py`)
Consistent API responses:
```python
from utils.api_response import APIResponse

# Success response
return APIResponse.success(data)
# Error response  
return APIResponse.error("Error message")
# Paginated response
return APIResponse.paginated(items, page, per_page, total)
```

#### Security Middleware (`middleware/security_headers.py`)
Automatic security headers:
- Content Security Policy (CSP)
- HSTS (production)
- XSS Protection
- Frame Options
- Input validation utilities

## Design Patterns

### 1. Repository Pattern
Abstracts data access logic:

```python
class TaskRepository:
    async def create(self, task_data: dict) -> Task:
        async with self.session() as session:
            task = Task(**task_data)
            session.add(task)
            await session.commit()
            return task
    
    async def get_by_id(self, task_id: str) -> Optional[Task]:
        async with self.session() as session:
            return await session.get(Task, task_id)
```

### 2. Strategy Pattern
For agent selection and routing:

```python
class RoutingStrategy:
    def route(self, task_analysis: dict) -> List[str]:
        intent = task_analysis['intent']['primary']
        return self.strategies[intent](task_analysis)
```

### 3. Observer Pattern
Event-driven architecture:

```python
@event_bus.on('task.completed')
def handle_task_completion(task_id, result):
    # Audit the completion
    auditor.record_completion(task_id, result)
    # Notify plugins
    plugin_registry.notify('task.completed', task_id, result)
```

### 4. Factory Pattern
For service creation:

```python
class ServiceFactory:
    @staticmethod
    def create_agent(agent_type: str) -> Agent:
        return {
            'architect': ArchitectAgent,
            'developer': DeveloperAgent,
            'qa': QAAgent
        }[agent_type]()
```

## Data Flow

### 1. Request Processing

```
User Request → API Endpoint → Authentication → NLU Analysis
     ↓                                              ↓
Response ← Formatting ← Agent Execution ← Task Orchestration
```

### 2. Task Execution Flow

```
Task Description → NLU Service → Intent/Entity Extraction
        ↓                              ↓
Execution Plan ← Orchestrator ← Agent Selection
        ↓
Multi-Agent Executor → Individual Agents → LLM Providers
        ↓
Result Aggregation → Audit Logging → Response
```

### 3. Real-time Updates

```
WebSocket Connection → Event Subscription
        ↓                    ↑
Client Updates ← Server Push ← Task Events
```

## Security Architecture

### 1. Authentication & Authorization
- API key validation
- Role-based access control
- Request rate limiting
- Session management

### 2. Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF tokens

### 3. Audit Trail
- All actions logged
- Request/response tracking
- Error monitoring
- Performance metrics

## Scalability Considerations

### 1. Horizontal Scaling
- Stateless service design
- Load balancer ready
- Distributed caching
- Database connection pooling

### 2. Performance Optimization
- Async operations throughout
- Lazy loading for circular imports
- Cached thread pool executors
- Efficient query patterns

### 3. Background Processing
- Celery for long-running tasks
- Redis message broker
- Task prioritization
- Result caching

## Plugin Architecture

### Plugin System Design
```
Plugin Discovery → Dynamic Loading → Service Registration
        ↓                ↓                    ↓
File Monitoring → Hot Reload → Dependency Injection
```

### Plugin Integration Points
- Service layer hooks
- Event system integration
- API endpoint extension
- UI component injection

## Database Schema

### Core Tables

```sql
-- Tasks table
CREATE TABLE tasks (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(255) REFERENCES tasks(id),
    agent_id VARCHAR(50),
    role VARCHAR(50),
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id VARCHAR(255) UNIQUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100),
    agent_id VARCHAR(50),
    task_id VARCHAR(255),
    action VARCHAR(255),
    details JSON
);
```

## Deployment Architecture

### Development Environment
```
Flask Development Server
    ├── SQLite Database
    ├── Local Redis
    └── Single Celery Worker
```

### Production Environment
```
Nginx (Reverse Proxy)
    ├── Gunicorn + Uvicorn Workers
    │   └── Flask Application
    ├── PostgreSQL (Primary DB)
    ├── Redis Cluster (Cache + Broker)
    └── Celery Workers (Scaled)
```

### Container Architecture
```yaml
services:
  web:
    build: .
    ports: ["5006:5006"]
    depends_on: [db, redis]
  
  db:
    image: postgres:15
    volumes: ["./data:/var/lib/postgresql/data"]
  
  redis:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
  
  worker:
    build: .
    command: ["celery", "-A", "tasks", "worker"]
    depends_on: [redis]
```

## Monitoring & Observability

### 1. Application Metrics
- Request/response times
- Agent performance
- Task completion rates
- Error rates

### 2. System Metrics
- CPU/Memory usage
- Database connections
- Queue lengths
- Cache hit rates

### 3. Business Metrics
- Agent utilization
- Task types distribution
- User engagement
- Feature adoption

## Error Handling Strategy

### 1. Graceful Degradation
```python
try:
    result = await orchestrator.execute(task)
except OrchestratorError:
    # Fall back to direct agent execution
    result = await executor.execute_single_agent(task)
except Exception:
    # Final fallback
    result = {"error": "Service temporarily unavailable"}
```

### 2. Circuit Breaker Pattern
```python
@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def call_external_service():
    return await external_api.request()
```

### 3. Retry Logic
```python
@retry(max_attempts=3, backoff=exponential)
async def resilient_operation():
    return await risky_operation()
```

## Configuration Management

### Environment-based Configuration
```python
class Config:
    # Base configuration
    DEBUG = False
    TESTING = False
    
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    
class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    REDIS_URL = os.getenv('REDIS_URL')
```

### Feature Flags
```python
FEATURES = {
    'nlu_enabled': True,
    'orchestration_enabled': True,
    'audit_system': True,
    'plugin_system': True,
    'hot_reload': os.getenv('ENABLE_HOT_RELOAD', 'false').lower() == 'true'
}
```

## Future Architecture Considerations

### 1. Microservices Migration
- Extract NLU as separate service
- Independent agent services
- API gateway pattern
- Service mesh for communication

### 2. Event Sourcing
- Store all state changes as events
- Rebuild state from event log
- Time-travel debugging
- Audit trail enhancement

### 3. CQRS Implementation
- Separate read/write models
- Optimized query paths
- Event-driven updates
- Eventual consistency

### 4. GraphQL API
- Flexible data fetching
- Reduced over-fetching
- Real-time subscriptions
- Better mobile support