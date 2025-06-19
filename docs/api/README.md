# API Reference

## Overview

The MCP Multi-Agent Chat System provides a comprehensive REST API for interacting with AI agents, managing tasks, and monitoring system performance. All endpoints require API key authentication.

## Response Format

All API responses follow a consistent format using the centralized response utilities:

### Success Response
```json
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {...},
    "timestamp": "2024-01-20T10:00:00Z"
}
```

### Error Response
```json
{
    "success": false,
    "error": {
        "message": "Detailed error message",
        "code": "ERROR_CODE",
        "timestamp": "2024-01-20T10:00:00Z",
        "details": {...}
    }
}
```

### Using Response Utilities
```python
from utils.api_response import APIResponse

# Success response
return APIResponse.success(data={"user_id": 123})

# Error response
return APIResponse.error("Invalid input", error_code="VALIDATION_ERROR")

# Paginated response
return APIResponse.paginated(items, page=1, per_page=20, total=100)
```

## Authentication

All API requests must include an API key in the header:

```bash
X-API-Key: your-api-key-here
```

## Base URL

```
http://localhost:5006/api
```

## Core Endpoints

### Agent Chat

#### Chat with Specific Agent
```http
POST /api/agents/chat/{agent_id}
```

**Parameters:**
- `agent_id` (path) - Agent identifier (e.g., `developer_01`, `architect_01`)

**Request Body:**
```json
{
    "message": "Create a REST API endpoint for user authentication",
    "enhance_prompt": true,
    "include_context": true,
    "session_id": "optional-session-id"
}
```

**Response:**
```json
{
    "success": true,
    "response": "I'll help you create a REST API endpoint for user authentication...",
    "agent": "developer_01",
    "timestamp": "2024-01-20T10:30:00Z",
    "enhanced": true,
    "original_message": "Create a REST API endpoint..."
}
```

### Agent Collaboration

#### Multi-Agent Task Execution
```http
POST /api/agents/collaborate
```

**Request Body:**
```json
{
    "task": "Design and implement a secure payment processing system",
    "agents": ["architect_01", "developer_01", "security_01"],
    "workflow": "sequential",
    "context": {
        "priority": "high",
        "deadline": "2024-01-25"
    }
}
```

**Response:**
```json
{
    "success": true,
    "task_id": "task_123abc",
    "status": "in_progress",
    "agents_assigned": ["architect_01", "developer_01", "security_01"],
    "estimated_completion": "2024-01-20T12:00:00Z"
}
```

### Agent Suggestions

#### Get Agent Recommendations
```http
POST /api/agents/suggest
```

**Request Body:**
```json
{
    "task": "Fix memory leak in the application",
    "include_details": true
}
```

**Response:**
```json
{
    "suggested_roles": ["bug", "developer"],
    "reasoning": "Memory leak issues require debugging expertise and code analysis",
    "confidence": 0.92,
    "agent_details": {
        "bug": {
            "name": "Bug Hunter",
            "expertise": ["debugging", "performance", "memory management"]
        },
        "developer": {
            "name": "Senior Developer",
            "expertise": ["code optimization", "profiling", "refactoring"]
        }
    }
}
```

## NLU & Orchestration

### Task Analysis

#### Analyze Task with NLU
```http
POST /api/agents/analyze
```

**Request Body:**
```json
{
    "task": "Review the authentication module for security vulnerabilities and fix any issues found"
}
```

**Response:**
```json
{
    "success": true,
    "analysis": {
        "intent": {
            "primary": "security_analysis",
            "secondary": ["code_review", "bug_fixing"],
            "confidence": 0.88
        },
        "entities": {
            "modules": ["authentication module"],
            "actions": ["review", "fix"],
            "focus": ["security vulnerabilities"]
        },
        "structured_task": {
            "task_type": "security_analysis",
            "recommended_agents": ["security", "developer", "qa"],
            "priority": "high",
            "complexity": "medium",
            "estimated_effort": "high"
        }
    }
}
```

### Intelligent Orchestration

#### Execute Task with Orchestration
```http
POST /api/agents/orchestrate
```

**Request Body:**
```json
{
    "task": "Create a comprehensive test suite for the payment module",
    "working_directory": "/path/to/project",
    "priority": "medium",
    "emergency": false,
    "dry_run": false,
    "context": {
        "coverage_target": 80,
        "include_integration_tests": true
    }
}
```

**Response (Execution):**
```json
{
    "success": true,
    "task_id": "task_456def",
    "orchestration": {
        "plan_id": "orch_789ghi",
        "routing_decision": {
            "workflow_type": "testing_workflow",
            "agents_used": ["qa", "developer"],
            "confidence": 0.91
        },
        "execution_summary": {
            "steps_completed": 5,
            "steps_total": 5,
            "duration": 420,
            "status": "completed"
        }
    },
    "result": {
        "tests_created": 25,
        "coverage_achieved": 85.3,
        "files_modified": ["tests/test_payment.py", "tests/integration/test_payment_flow.py"]
    }
}
```

**Response (Dry Run):**
```json
{
    "success": true,
    "plan": {
        "task_id": "orch_dry_789",
        "priority": "medium",
        "estimated_duration": 480,
        "routing": {
            "primary_agents": ["qa", "developer"],
            "workflow_type": "testing_workflow",
            "reasoning": "Comprehensive test suite requires QA expertise with developer support"
        },
        "execution_steps": [
            {
                "step_number": 1,
                "step": "Analyze payment module structure",
                "agent": "qa",
                "action": "analyze",
                "estimated_duration": 120
            },
            {
                "step_number": 2,
                "step": "Create unit test framework",
                "agent": "qa",
                "action": "implement",
                "estimated_duration": 180
            }
        ]
    }
}
```

## Task Management

### Task Status

#### Get Task Status
```http
GET /api/tasks/{task_id}/status
```

**Response:**
```json
{
    "task_id": "task_123abc",
    "status": "completed",
    "progress": 100,
    "created_at": "2024-01-20T10:00:00Z",
    "completed_at": "2024-01-20T10:30:00Z",
    "result": {
        "success": true,
        "summary": "Payment processing system designed and implemented"
    }
}
```

### Task History

#### Get Task History
```http
GET /api/tasks
```

**Query Parameters:**
- `limit` (int) - Number of tasks to return (default: 20)
- `offset` (int) - Pagination offset (default: 0)
- `status` (string) - Filter by status (pending, in_progress, completed, failed)

**Response:**
```json
{
    "tasks": [
        {
            "id": "task_123abc",
            "title": "Design payment system",
            "status": "completed",
            "created_at": "2024-01-20T10:00:00Z"
        }
    ],
    "total": 150,
    "limit": 20,
    "offset": 0
}
```

## MCP Integration

### MCP Server Management

#### List MCP Servers
```http
GET /api/mcp/servers
```

**Response:**
```json
{
    "success": true,
    "data": {
        "servers": {
            "total": 2,
            "running": 2,
            "servers": {
                "swarm_mcp": {
                    "status": "running",
                    "pid": 12345,
                    "tools": 15,
                    "tool_names": ["read_file", "write_file", "search_files"]
                }
            }
        }
    }
}
```

#### Execute MCP Tool
```http
POST /api/mcp/tools/{server_id}/execute
```

**Request Body:**
```json
{
    "tool": "read_file",
    "arguments": {
        "path": "/path/to/file.py"
    }
}
```

## Plugin System

### Plugin Management

#### List Plugins
```http
GET /api/plugins/
```

**Response:**
```json
{
    "success": true,
    "plugin_count": 2,
    "plugins": {
        "AnalyticsPlugin": {
            "info": {
                "name": "Analytics Plugin",
                "version": "1.0.0",
                "description": "Tracks system metrics"
            },
            "status": "active",
            "loaded_at": "2024-01-20T09:00:00Z"
        }
    }
}
```

#### Reload Plugin
```http
POST /api/plugins/{plugin_id}/reload
```

**Response:**
```json
{
    "success": true,
    "message": "Plugin reloaded successfully",
    "plugin_id": "AnalyticsPlugin"
}
```

## Audit System

### Audit Statistics

#### Get Audit Statistics
```http
GET /api/audit/statistics
```

**Query Parameters:**
- `agent_id` (string) - Filter by specific agent
- `start_date` (ISO date) - Start date for statistics
- `end_date` (ISO date) - End date for statistics

**Response:**
```json
{
    "success": true,
    "statistics": {
        "total_records": 1523,
        "success_rate": 94.5,
        "agents": {
            "developer_01": {
                "tasks": 234,
                "success_rate": 96.2,
                "avg_duration": 45.3
            }
        },
        "by_intent": {
            "code_development": 450,
            "bug_fixing": 312,
            "testing": 198
        }
    }
}
```

### Explainability

#### Get Task Explanation
```http
GET /api/audit/explain/{task_id}
```

**Response:**
```json
{
    "success": true,
    "explanation": {
        "task_id": "task_123abc",
        "intent_analysis": {
            "detected_intent": "bug_fixing",
            "confidence": 0.92,
            "reasoning": "Keywords 'fix' and 'crash' indicate bug fixing task"
        },
        "agent_selection": {
            "selected": ["bug", "developer"],
            "reasoning": "Bug agent for analysis, developer for implementation"
        },
        "execution_trace": [
            {
                "step": 1,
                "agent": "bug",
                "action": "analyze_crash",
                "duration": 120,
                "result": "Identified null pointer exception"
            }
        ],
        "performance_analysis": {
            "total_duration": 300,
            "efficiency_score": 0.85,
            "suggestions": ["Consider caching analysis results"]
        }
    }
}
```

### Audit Configuration

#### Set Audit Level
```http
POST /api/audit/level
```

**Request Body:**
```json
{
    "level": "detailed"
}
```

**Levels:**
- `minimal` - Basic action logging
- `standard` - Actions + decisions
- `detailed` - Full context including prompts
- `debug` - Complete trace

## Monitoring

### Health Check

#### System Health
```http
GET /api/monitoring/health
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-20T10:00:00Z",
    "services": {
        "database": "ok",
        "redis": "ok",
        "mcp_servers": "ok",
        "celery": "ok"
    },
    "metrics": {
        "uptime_seconds": 86400,
        "active_tasks": 3,
        "queue_size": 12
    }
}
```

### Performance Metrics

#### Get Performance Metrics
```http
GET /api/monitoring/metrics
```

**Response:**
```json
{
    "metrics": {
        "request_rate": 125.5,
        "average_response_time": 234,
        "error_rate": 0.5,
        "active_connections": 45,
        "cpu_usage": 34.2,
        "memory_usage": 67.8
    }
}
```

## WebSocket Events

### Connection
```javascript
const socket = io('http://localhost:5006', {
    auth: {
        apiKey: 'your-api-key'
    }
});
```

### Events

#### Task Updates
```javascript
socket.on('task.update', (data) => {
    console.log('Task updated:', data);
    // { task_id: 'task_123', status: 'in_progress', progress: 50 }
});
```

#### Agent Messages
```javascript
socket.on('agent.message', (data) => {
    console.log('Agent message:', data);
    // { agent_id: 'developer_01', message: 'Analyzing code...', task_id: 'task_123' }
});
```

#### System Notifications
```javascript
socket.on('system.notification', (data) => {
    console.log('System notification:', data);
    // { type: 'info', message: 'New plugin loaded', details: {...} }
});
```

## Error Responses

All endpoints return consistent error responses:

```json
{
    "success": false,
    "error": {
        "code": "INVALID_REQUEST",
        "message": "Task description is required",
        "details": {
            "field": "task",
            "requirement": "non-empty string"
        }
    },
    "timestamp": "2024-01-20T10:00:00Z"
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `UNAUTHORIZED` | Invalid or missing API key | 401 |
| `FORBIDDEN` | Insufficient permissions | 403 |
| `NOT_FOUND` | Resource not found | 404 |
| `INVALID_REQUEST` | Invalid request parameters | 400 |
| `AGENT_ERROR` | Agent execution failed | 500 |
| `RATE_LIMITED` | Too many requests | 429 |
| `SERVICE_UNAVAILABLE` | Service temporarily down | 503 |

## Rate Limiting

API requests are rate limited:
- **Default**: 100 requests per minute
- **Authenticated**: 500 requests per minute
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Reset timestamp

## Pagination

List endpoints support pagination:

```http
GET /api/tasks?limit=20&offset=40
```

Response includes pagination metadata:
```json
{
    "data": [...],
    "pagination": {
        "total": 150,
        "limit": 20,
        "offset": 40,
        "has_next": true,
        "has_prev": true
    }
}
```

## Versioning

API version is included in responses:
```json
{
    "api_version": "1.0.0",
    "data": {...}
}
```

Future versions will use URL versioning:
```
/api/v2/agents/chat/{agent_id}
```