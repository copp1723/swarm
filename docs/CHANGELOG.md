# Changelog

All notable changes to the SWARM Multi-Agent System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2024-12-20

### Added - Deployment Hardening
- **MCP Filesystem Configuration**: 
  - `DISABLE_MCP_FILESYSTEM` environment variable for degraded mode operation
  - `MCP_FILESYSTEM_ALLOWED_DIRS` for directory access control (default: `/app`)
  - `MCP_FILESYSTEM_LOG_OPERATIONS` for comprehensive file operation auditing
- **Render Cloud Platform Support**:
  - Complete Render deployment guide with managed PostgreSQL and Redis
  - Auto-deployment configuration with health checks at `/ready` endpoint
  - Port standardization to `10000` for Render compatibility
- **Performance Optimization**:
  - `WEB_CONCURRENCY` environment variable for worker scaling control
  - `ENABLE_CELERY` toggle for resource-constrained deployments
  - Optimized resource allocation for Basic tier (1GB RAM, 0.5 CPU)
- **Production Monitoring**:
  - MCP filesystem status and operations monitoring endpoints
  - File access logging for security auditing
  - Enhanced health check system with degraded status support
- **Email & Webhook Integration**:
  - Day-one Mailgun configuration for agent email processing
  - Webhook endpoint setup for external integrations
  - Sentry error tracking integration

### Changed
- **Health Check Endpoint**: Updated from `/health` to `/ready` for better deployment compatibility
- **Deployment Architecture**: Migrated from generic cloud deployment to Render-optimized setup
- **Resource Management**: Implemented tiered resource allocation (free/basic/paid)
- **Environment Configuration**: Simplified variable setup with auto-generated database/Redis URLs

### Security
- **Filesystem Access Control**: Configurable directory restrictions for agent file operations
- **Operation Auditing**: Complete logging of file system access and modifications
- **Production Secrets**: Secure environment variable management through Render dashboard
- **CORS Configuration**: Dynamic origin configuration for deployment URLs

### Performance
- **Worker Concurrency**: Configurable based on available resources (2 for basic, 4+ for higher tiers)
- **Database Pooling**: Optimized connection limits for shared database instances
- **Celery Workers**: Optional background processing to save resources on lower tiers

## [Previous Unreleased]

### Added
- Centralized API response formatting utility (`utils/api_response.py`)
- Centralized database connection manager (`utils/db_connection.py`)
- Centralized logging configuration (`utils/logging_setup.py`)
- Security headers middleware (`middleware/security_headers.py`)
- Comprehensive security documentation
- Performance optimization guide
- Architecture Decision Records (ADRs)
- Development requirements separation (`requirements-dev.txt`)

### Changed
- Updated critical dependencies for security:
  - `openai`: 1.3.5 → 1.35.0
  - `anthropic`: 0.7.8 → 0.25.0
  - Replaced `eventlet` with `gevent` (CVE fix)
- Enhanced `.gitignore` with comprehensive patterns
- Improved error handling across all modules

### Security
- Removed hardcoded API keys from test files
- Added JWT support dependencies
- Implemented path traversal protection
- Added input validation utilities

### Removed
- Unused dependencies: `flower`, `apprise`, `sentry-sdk`
- Dead code files and backups
- Duplicate code blocks (~1,200 lines)

## [2.0.0] - 2024-01-20

### Added
- Natural Language Understanding (NLU) service
- Intelligent task orchestration with workflow templates
- Plugin system with hot-reload capability
- Comprehensive audit system with explainability
- WebSocket support for real-time updates
- MCP (Model Context Protocol) integration
- 12 intent types for task classification
- Entity extraction for technical terms

### Changed
- Complete architecture overhaul:
  - Simplified DI container
  - Centralized blueprint registry
  - Optimized service registry
  - Improved async/sync bridge
- Enhanced multi-agent collaboration
- Better error handling and recovery

### Performance
- Connection pooling for databases
- Cached thread pool executors
- Lazy loading to prevent circular imports
- Response caching strategies

## [1.5.0] - 2024-01-10

### Added
- Email service integration
- Supermemory integration for persistent memory
- Background task processing with Celery
- Task prioritization system
- Memory-aware chat service

### Changed
- Improved agent prompts for better responses
- Enhanced file handling security
- Better session management

### Fixed
- WebSocket connection stability
- Memory leak in long-running conversations
- File upload size limitations

## [1.0.0] - 2024-01-01

### Added
- Initial release with 6 specialized AI agents
- Multi-model support (OpenAI, Anthropic, Google, DeepSeek)
- Basic chat interface
- File upload capabilities
- Agent collaboration features
- SQLite database for development
- PostgreSQL support for production

### Security
- API key authentication
- Basic input validation
- CORS configuration

## Migration Guide

### From 1.x to 2.0

1. **Update Dependencies**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

2. **Update Configuration**
   - Copy `.env.example` to `.env`
   - Add new required variables:
     - `JWT_SECRET_KEY`
     - `REDIS_URL` (for Celery)

3. **Database Migration**
   ```bash
   python migrations/add_audit_tables.py
   python migrations/add_performance_indexes.py
   ```

4. **Code Updates**
   - Replace direct JSON responses with `APIResponse` utility
   - Update logging to use centralized configuration
   - Apply security headers middleware

5. **Test**
   ```bash
   python test_nlu_orchestrator.py
   python test_plugin_audit_simple.py
   ```

### Breaking Changes in 2.0

- API responses now use consistent format
- Authentication required on all endpoints
- Some environment variables renamed
- Database schema changes (run migrations)

### Deprecations

- Direct `jsonify()` usage - use `APIResponse` instead
- Manual logging setup - use `get_logger()` instead
- Inline security checks - use middleware instead