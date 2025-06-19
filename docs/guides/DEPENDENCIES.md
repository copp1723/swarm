# Dependencies Documentation

This document provides a comprehensive overview of all dependencies used in the MCP Multi-Agent System.

## Core Dependencies

### Web Framework
- **Flask** (3.0.0)
  - Purpose: Core web framework
  - License: BSD-3-Clause
  - Documentation: https://flask.palletsprojects.com/

- **Flask-SQLAlchemy** (3.1.1)
  - Purpose: SQLAlchemy integration for Flask
  - License: BSD-3-Clause
  - Documentation: https://flask-sqlalchemy.palletsprojects.com/

- **Flask-CORS** (4.0.0)
  - Purpose: Cross-Origin Resource Sharing support
  - License: MIT
  - Documentation: https://flask-cors.readthedocs.io/

### Database
- **SQLAlchemy[asyncio]** (2.0.23)
  - Purpose: SQL toolkit and ORM with async support
  - License: MIT
  - Features: Async queries, connection pooling, migrations
  - Documentation: https://docs.sqlalchemy.org/

- **asyncpg** (0.29.0)
  - Purpose: PostgreSQL async driver
  - License: Apache-2.0
  - Performance: High-performance native PostgreSQL driver
  - Documentation: https://magicstack.github.io/asyncpg/

- **aiosqlite** (0.19.0)
  - Purpose: SQLite async driver for development
  - License: MIT
  - Documentation: https://aiosqlite.omnilib.dev/

### Production Server
- **Gunicorn** (21.2.0)
  - Purpose: WSGI HTTP Server
  - License: MIT
  - Configuration: 4 workers by default
  - Documentation: https://gunicorn.org/

- **Uvicorn[standard]** (0.24.0.post1)
  - Purpose: ASGI server for async support
  - License: BSD-3-Clause
  - Includes: uvloop, httptools, websockets
  - Documentation: https://www.uvicorn.org/

### Real-time Communication
- **Flask-SocketIO** (5.3.6)
  - Purpose: WebSocket support for Flask
  - License: MIT
  - Features: Room support, broadcasting, namespaces
  - Documentation: https://flask-socketio.readthedocs.io/

- **python-socketio** (5.11.0)
  - Purpose: Socket.IO server implementation
  - License: MIT
  - Documentation: https://python-socketio.readthedocs.io/

- **eventlet** (0.33.3)
  - Purpose: Concurrent networking library
  - License: MIT
  - Features: Green threads, non-blocking I/O
  - Documentation: https://eventlet.net/

### Background Tasks
- **Celery** (5.3.4)
  - Purpose: Distributed task queue
  - License: BSD-3-Clause
  - Features: Task scheduling, retries, monitoring
  - Documentation: https://docs.celeryproject.org/

- **Redis** (5.0.1)
  - Purpose: Message broker and cache
  - License: MIT
  - Python client for Redis server
  - Documentation: https://redis-py.readthedocs.io/

- **Flower** (2.0.1) *Optional*
  - Purpose: Celery monitoring and management
  - License: BSD-3-Clause
  - Features: Real-time monitoring, task history, worker control
  - Documentation: https://flower.readthedocs.io/

### Utilities
- **python-dotenv** (1.0.0)
  - Purpose: Environment variable management
  - License: BSD-3-Clause
  - Documentation: https://pypi.org/project/python-dotenv/

- **requests** (2.31.0)
  - Purpose: HTTP client library
  - License: Apache-2.0
  - Documentation: https://requests.readthedocs.io/

- **aiofiles** (23.2.1)
  - Purpose: Async file operations
  - License: Apache-2.0
  - Documentation: https://github.com/Tinche/aiofiles

- **greenlet** (3.0.1)
  - Purpose: Lightweight concurrent programming
  - License: MIT
  - Required for SQLAlchemy async support

## System Requirements

### Runtime Dependencies
- **Python** 3.11+
  - Required for async features and type hints
  - Download: https://www.python.org/downloads/

- **Node.js** 16+
  - Required for MCP (Model Context Protocol) servers
  - Download: https://nodejs.org/

- **Redis Server** 6.0+
  - Required for Celery background tasks
  - Optional for basic functionality
  - Download: https://redis.io/download

- **PostgreSQL** 13+ (Production)
  - Recommended for production deployments
  - SQLite used for development
  - Download: https://www.postgresql.org/download/

### NPM Dependencies (via npx)
- **@modelcontextprotocol/server-filesystem**
  - Purpose: MCP server for filesystem access
  - Installed automatically via npx

## Optional Performance Enhancements

These can be uncommented in requirements.txt for additional performance:

- **ujson** (5.9.0)
  - Purpose: Ultra-fast JSON parsing
  - License: BSD-3-Clause
  - Performance: 2-3x faster than standard json

- **orjson** (3.9.10)
  - Purpose: Even faster JSON parsing
  - License: Apache-2.0/MIT
  - Performance: 3-4x faster than standard json

- **msgpack** (1.0.7)
  - Purpose: Efficient binary serialization
  - License: Apache-2.0
  - Use case: Celery message serialization

## Security Considerations

1. **Dependencies are pinned** to specific versions for reproducibility
2. **Regular updates** recommended for security patches
3. **Virtual environment** strongly recommended to isolate dependencies
4. **Production dependencies** should be audited with `pip-audit`

## Updating Dependencies

### Check for updates:
```bash
pip list --outdated
```

### Update specific package:
```bash
pip install --upgrade package-name
```

### Update all packages (careful in production):
```bash
pip install --upgrade -r requirements.txt
```

### Security audit:
```bash
pip install pip-audit
pip-audit
```

## License Compatibility

All dependencies use permissive licenses compatible with commercial use:
- MIT
- BSD (2-Clause and 3-Clause)
- Apache-2.0

No GPL or LGPL dependencies are included.