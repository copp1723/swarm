# Development Guide

This guide covers development setup, workflow, and best practices for contributing to the SWARM project.

## 🛠️ Development Setup

### Prerequisites
- Python 3.11+
- Git
- Redis (for background tasks)
- PostgreSQL (optional, for production-like testing)
- Node.js/npm (for MCP servers)

### Initial Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd swarm/mcp_new_project

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Set up pre-commit hooks
pre-commit install

# 5. Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# 6. Initialize the database
python init_database.py

# 7. Run tests to verify setup
pytest
```

## 📁 Project Structure

```
mcp_new_project/
├── app.py                  # Main Flask application
├── core/                   # Core system components
│   ├── blueprint_registry.py    # Centralized route registration
│   ├── database_config.py       # Database configuration
│   ├── service_registry.py      # Service registration
│   └── plugins/                 # Plugin system
├── services/               # Business logic layer
│   ├── multi_agent_executor.py  # Agent orchestration
│   ├── nlu_service.py           # Natural language understanding
│   └── auditing/                # Audit system
├── routes/                 # API endpoints
├── models/                 # Database models
├── utils/                  # Shared utilities
│   ├── api_response.py          # Response formatting
│   ├── db_connection.py         # Database management
│   └── logging_setup.py         # Logging configuration
├── middleware/             # Flask middleware
├── static/                 # Frontend assets
├── tests/                  # Test suites
└── docs/                   # Documentation
```

## 🔧 Development Workflow

### 1. Feature Development

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes and test
pytest tests/test_your_feature.py

# Run linting
black .
flake8 .
pylint **/*.py

# Commit with conventional commits
git commit -m "feat: add new feature description"
```

### 2. Using Development Tools

#### Code Formatting
```bash
# Format all Python files
black .

# Check without modifying
black --check .
```

#### Linting
```bash
# Run flake8
flake8 --max-line-length=100

# Run pylint
pylint services/ routes/ utils/
```

#### Type Checking
```bash
# Run mypy
mypy --ignore-missing-imports .
```

### 3. Testing

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_nlu_service.py

# Run with verbose output
pytest -v

# Run only marked tests
pytest -m "not slow"
```

#### Writing Tests
```python
# tests/test_example.py
import pytest
from utils.api_response import APIResponse

def test_api_response_success():
    response, status = APIResponse.success({"id": 1})
    assert status == 200
    assert response.json["success"] is True

@pytest.mark.slow
def test_heavy_operation():
    # Test that might take time
    pass
```

## 🏗️ Architecture Guidelines

### 1. Using Centralized Utilities

#### API Responses
```python
from utils.api_response import APIResponse

@app.route('/api/example')
def example_endpoint():
    try:
        # Your logic here
        return APIResponse.success(data=result)
    except ValueError as e:
        return APIResponse.error(str(e), error_code="VALIDATION_ERROR")
```

#### Database Access
```python
from utils.db_connection import get_db_manager

def get_user(user_id: int):
    db = get_db_manager()
    with db.session_scope() as session:
        return session.query(User).filter_by(id=user_id).first()
```

#### Logging
```python
from utils.logging_setup import get_logger

logger = get_logger(__name__)

def process_task():
    logger.info("Starting task processing")
    try:
        # Process
        logger.debug("Task details", extra={"task_id": 123})
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
```

### 2. Creating New Services

```python
# services/example_service.py
from typing import Dict, Any
from utils.logging_setup import get_logger

logger = get_logger(__name__)

class ExampleService:
    """Service documentation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with proper error handling"""
        logger.info(f"Processing data: {data.get('id')}")
        
        try:
            # Your logic here
            result = await self._internal_process(data)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
            
    async def _internal_process(self, data: Dict[str, Any]) -> Any:
        """Internal processing logic"""
        pass
```

### 3. Adding New Routes

```python
# routes/example.py
from flask import Blueprint, request
from utils.api_response import APIResponse
from utils.logging_setup import get_logger
from services.example_service import ExampleService

example_bp = Blueprint('example', __name__, url_prefix='/api/example')
logger = get_logger(__name__)
service = ExampleService(config={})

@example_bp.route('/', methods=['POST'])
async def create_example():
    """Create a new example"""
    try:
        data = request.get_json()
        result = await service.process(data)
        return APIResponse.created(result)
    except ValueError as e:
        return APIResponse.validation_error({"field": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return APIResponse.internal_error()
```

## 🔌 Plugin Development

### Creating a Plugin

```python
# plugins/my_plugin.py
from core.plugins import ServicePlugin
from core.interfaces import IService

class MyService(IService):
    async def initialize(self):
        """Initialize the service"""
        pass
        
    async def process(self, data):
        """Process data"""
        return {"processed": data}

class MyPlugin(ServicePlugin):
    def get_plugin_info(self):
        return {
            "name": "My Plugin",
            "version": "1.0.0",
            "description": "Example plugin"
        }
    
    def register_services(self, container):
        container.register_singleton("my_service", MyService())
```

## 🐛 Debugging

### 1. Enable Debug Mode
```bash
# In .env
FLASK_DEBUG=1
FLASK_ENV=development
```

### 2. Using the Debugger
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use ipdb (better interface)
import ipdb; ipdb.set_trace()
```

### 3. Logging
```python
# Set log level to DEBUG
from utils.logging_setup import get_logger, log_level

logger = get_logger(__name__)

with log_level(logger, "DEBUG"):
    # Debug logging enabled here
    logger.debug("Detailed debug info")
```

### 4. Performance Profiling
```bash
# Profile a specific function
python -m cProfile -s cumulative app.py

# Use py-spy for production profiling
py-spy record -o profile.svg -- python app.py
```

## 📋 Code Style Guide

### Python Style
- Follow PEP 8 with 100 character line limit
- Use type hints for function parameters and returns
- Write docstrings for all public functions and classes
- Use f-strings for string formatting

### Naming Conventions
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Imports
```python
# Standard library
import os
import sys
from typing import Dict, List, Optional

# Third party
import flask
from sqlalchemy import create_engine

# Local application
from utils.logging_setup import get_logger
from services.example_service import ExampleService
```

## 🚀 Deployment

### Development Server
```bash
# Using Flask development server
python app.py

# With auto-reload
FLASK_DEBUG=1 python app.py
```

### Production Server
```bash
# Using Gunicorn with Uvicorn workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

# Or use the startup script
python run_production.py
```

## 📝 Documentation

### Writing Documentation
- Update README.md for user-facing changes
- Add docstrings to all new functions
- Update API documentation for new endpoints
- Add ADRs for architectural decisions

### Generating API Documentation
```bash
# Future: Generate OpenAPI spec
python scripts/generate_openapi.py
```

## 🤝 Contributing

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation
7. Submit pull request

### Commit Messages
Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Build process/auxiliary changes

## 🆘 Getting Help

- Check existing documentation
- Search closed issues
- Ask in discussions
- Create a new issue with:
  - Clear description
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details