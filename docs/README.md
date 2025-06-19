# MCP Multi-Agent System Documentation

Welcome to the MCP Multi-Agent System documentation. This system provides a powerful interface for coordinating multiple AI agents to work collaboratively on complex software engineering tasks.

## 📚 Documentation Structure

### Core Documentation
- **[Getting Started Guide](./getting-started.md)** - Quick setup and first steps
- **[Installation Guide](../INSTALLATION.md)** - Detailed installation instructions
- **[User Guide](./user-guide.md)** - How to use the interface effectively
- **[Agent Reference](./agents/README.md)** - Detailed guide to each agent

### Technical Documentation
- **[Architecture Overview](./architecture.md)** - System design and components
- **[API Documentation](./api/README.md)** - Complete API reference
- **[Performance Optimization](../OPTIMIZATION_GUIDE.md)** - Performance tuning guide
- **[Dependencies](../requirements.txt)** - Complete dependency list

### Development & Operations
- **[Development Guide](./development.md)** - Contributing and extending the system
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions
- **[Environment Configuration](../.env.example)** - Configuration reference

## 🚀 Quick Links

### For New Users
1. [Installation Guide](./getting-started.md#installation)
2. [Your First Agent Chat](./getting-started.md#first-chat)
3. [Running a Collaborative Task](./getting-started.md#first-collaboration)

### For Developers
1. [Setting Up Development Environment](./development.md#setup)
2. [Adding New Agents](./development.md#new-agents)
3. [Extending the API](./development.md#api-extensions)

### For System Administrators
1. [Configuration Options](./configuration.md)
2. [Performance Tuning](./performance.md)
3. [Security Best Practices](./security.md)

## 🎯 What This System Does

The MCP Multi-Agent System is designed to:

- **Orchestrate AI Agents** - Coordinate multiple specialized AI agents working together
- **Analyze Codebases** - Provide deep insights into software projects
- **Automate Development Tasks** - Handle complex multi-step development workflows
- **Ensure Quality** - Built-in testing, security, and code review capabilities
- **Support Real Projects** - Full filesystem access and MCP integration
- **Real-time Collaboration** - WebSocket-powered live updates and progress tracking
- **Background Processing** - Celery-based task queue for long-running operations
- **High Performance** - Async database operations and production-ready server

## 🤝 Getting Help

- **Issues**: Report bugs at [GitHub Issues](https://github.com/anthropics/claude-code/issues)
- **Community**: Join discussions in our forums
- **Support**: Contact support@example.com for enterprise support

## 📖 Version Information

- **Current Version**: 2.0.0
- **Last Updated**: June 2025
- **Python**: 3.11+ required
- **Node.js**: 16+ required (for MCP servers)
- **Database**: PostgreSQL 13+ (production) or SQLite (development)
- **Redis**: 6.0+ (for background tasks)

## 🔧 Key Technologies

- **Backend**: Flask 3.0 with async support
- **Database**: SQLAlchemy 2.0 with async repositories
- **Real-time**: Flask-SocketIO for WebSocket communication
- **Task Queue**: Celery with Redis broker
- **Production Server**: Gunicorn with Uvicorn workers
- **Frontend**: Vanilla JavaScript with Tailwind CSS