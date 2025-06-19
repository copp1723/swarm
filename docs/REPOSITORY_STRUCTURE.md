# Repository Structure

## Overview
This document describes the organized structure of the MCP Multi-Agent Chat System repository.

## Root Directory Structure

```
mcp_new_project/
├── app.py                          # Main Flask application entry point
├── README.md                       # Project documentation
├── .gitignore                      # Git ignore rules
│
├── config/                         # Configuration files
│   ├── .env                        # Environment variables (not in git)
│   ├── .env.example               # Environment template
│   ├── pytest.ini                 # Pytest configuration
│   ├── pyproject.toml             # Python project configuration
│   └── requirements/              # Python dependencies
│       ├── requirements.txt       # Core dependencies
│       ├── requirements-dev.txt   # Development dependencies
│       ├── requirements-test.txt  # Testing dependencies
│       └── requirements_email_agent.txt  # Email agent specific deps
│
├── core/                          # Core application components
│   ├── plugins/                   # Plugin system
│   └── service_registry.py       # Service dependency injection
│
├── deployment/                    # Deployment configurations
│   ├── Dockerfile                 # Docker container definition
│   ├── docker-compose.yml        # Docker compose services
│   └── .dockerignore             # Docker ignore rules
│
├── docs/                         # Documentation
│   ├── API_KEY.txt               # API key documentation
│   ├── CHANGELOG.md              # Change log
│   ├── CODE_CLEANUP_SUMMARY.md   # Code cleanup report
│   ├── PRIORITY_FIXES_IMPLEMENTATION.md  # Implementation notes
│   ├── REPOSITORY_STRUCTURE.md   # This file
│   ├── TEST_SUMMARY.md           # Testing documentation
│   ├── UI_INTEGRATION_SUMMARY.md # UI integration notes
│   └── WEAKNESS_ANALYSIS.md      # Code analysis report
│
├── init/                         # Initialization scripts
│   └── init_database.py         # Database initialization
│
├── logs/                         # Application logs
│   ├── app.log                   # Application logs
│   ├── celery.log               # Celery worker logs
│   ├── flask_app.log            # Flask application logs
│   └── server.log               # Server logs
│
├── models/                       # Database models
│   ├── core.py                   # Core database setup
│   ├── email_models.py          # Email-related models
│   └── ...                      # Other model files
│
├── routes/                       # API route handlers
│   ├── agents.py                # Agent management routes
│   ├── email.py                 # Email API routes
│   ├── memory_api.py            # Memory API routes
│   └── ...                     # Other route files
│
├── schemas/                      # Data validation schemas
│   ├── email_schemas.py         # Email validation schemas
│   └── ...                     # Other schema files
│
├── scripts/                      # Utility scripts
│   ├── clean_logs.py            # Log cleanup utility
│   ├── run_production.py        # Production runner
│   ├── run_server.py            # Development server
│   ├── start_simple.py          # Simple server start
│   ├── start_server.sh          # Server startup script
│   ├── verify_runtime.py        # Runtime verification
│   ├── verify_ui_integration.sh # UI integration test
│   └── fixes/                   # Fix scripts
│       ├── fix_chat_system.py   # Chat system fixes
│       └── quick_fix.py         # Quick fixes
│
├── services/                     # Business logic services
│   ├── auditing/                # Audit services
│   ├── email_service.py         # Email service
│   ├── supermemory_service.py   # Memory service
│   └── ...                     # Other service files
│
├── static/                       # Static web assets
│   ├── css/                     # Stylesheets
│   ├── js/                      # JavaScript files
│   └── ...                     # Other static files
│
├── tasks/                        # Background task definitions
│   ├── agent_tasks.py           # Agent-related tasks
│   ├── email_tasks.py           # Email tasks
│   └── ...                     # Other task files
│
├── tests/                        # Test suite
│   ├── integration/             # Integration tests
│   │   ├── test_chat.json       # Chat test data
│   │   ├── test_collab.json     # Collaboration test data
│   │   ├── test_integration.py  # Integration test suite
│   │   ├── test_mcp_chat.py     # MCP chat tests
│   │   ├── test_nlu_orchestrator.py  # NLU tests
│   │   ├── test_plugin_audit.py # Plugin audit tests
│   │   └── test_plugin_audit_simple.py  # Simple audit tests
│   ├── e2e/                     # End-to-end tests
│   └── ...                     # Other test directories
│
└── utils/                        # Utility functions
    ├── api_response.py           # API response helpers
    ├── db_context.py             # Database context managers
    ├── error_handling.py         # Error handling utilities
    ├── unified_logging.py        # Logging utilities
    └── ...                      # Other utility files
```

## Directory Purposes

### Core Application
- **app.py**: Main Flask application entry point
- **core/**: Core application components and dependency injection
- **models/**: SQLAlchemy database models
- **routes/**: Flask route handlers and API endpoints
- **services/**: Business logic and service layer
- **utils/**: Shared utility functions and helpers

### Configuration & Setup
- **config/**: All configuration files and environment setup
- **init/**: Database and application initialization scripts
- **deployment/**: Docker and deployment configurations

### Development & Testing
- **tests/**: Comprehensive test suite with integration and e2e tests
- **scripts/**: Development and utility scripts
- **logs/**: Application log files (generated at runtime)

### Documentation & Schema
- **docs/**: Project documentation and analysis reports
- **schemas/**: Data validation and API schemas

### Web Assets
- **static/**: Frontend CSS, JavaScript, and other static files

### Background Processing
- **tasks/**: Celery task definitions for background processing

## File Organization Principles

1. **Separation of Concerns**: Each directory has a single, clear purpose
2. **Logical Grouping**: Related files are grouped together
3. **Standard Conventions**: Follows Python/Flask project conventions
4. **Easy Navigation**: Clear hierarchy for finding specific functionality
5. **Scalability**: Structure supports growth and additional features

## Benefits of This Structure

- **Maintainability**: Easy to locate and modify specific functionality
- **Collaboration**: Clear structure helps team members navigate the code
- **Testing**: Dedicated test directory with proper organization
- **Deployment**: Separate deployment configuration management
- **Development**: Development tools and scripts are clearly separated

## Usage Guidelines

- Keep root directory minimal (only essential files)
- Use appropriate subdirectories for new files
- Follow naming conventions within each directory
- Update this documentation when adding new major directories
- Ensure imports reflect the organized structure