# API Versioning Strategy

## Overview

This document outlines the API versioning strategy for the MCP Multi-Agent Chat System, ensuring backward compatibility while allowing for continuous improvement and evolution of the API.

## Versioning Principles

### 1. Semantic Versioning
We follow Semantic Versioning (SemVer) for our API:
- **MAJOR.MINOR.PATCH** (e.g., 2.1.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### 2. Backward Compatibility
- Minor and patch updates maintain full backward compatibility
- Breaking changes are only introduced in major versions
- Deprecated features are maintained for at least one major version

### 3. Version Lifecycle
- **Alpha**: Experimental features, may change
- **Beta**: Feature complete, stabilizing
- **Stable**: Production ready
- **Deprecated**: Will be removed in future
- **Sunset**: No longer supported

## Versioning Implementation

### URL Path Versioning

**Current Format:**
```
/api/v{major}/resource
```

**Examples:**
```
GET /api/v1/agents/list          # Version 1
GET /api/v2/agents/list          # Version 2
GET /api/agents/list             # Latest stable (alias)
```

### Version Header Support

Clients can also specify version via headers:
```http
GET /api/agents/list
X-API-Version: 2.0
```

### Response Version Information

All responses include version metadata:
```json
{
    "api_version": "2.0.0",
    "deprecated_features": [],
    "data": {...}
}
```

## Version Migration Strategy

### 1. Introduction Phase (3 months)
- New version available at `/api/v{new}/`
- Previous version remains default
- Documentation updated
- Migration guides published

### 2. Transition Phase (6 months)
- New version becomes default
- Previous version available at `/api/v{old}/`
- Deprecation warnings added
- Active customer outreach

### 3. Deprecation Phase (3 months)
- Previous version in maintenance mode
- Only critical fixes applied
- Sunset date announced
- Final migration reminders

### 4. Sunset Phase
- Previous version removed
- Redirects to migration guide
- Support ends

## API Version Compatibility Matrix

| Feature | v1.0 | v1.5 | v2.0 | v3.0 (planned) |
|---------|------|------|------|----------------|
| Basic Chat | ✅ | ✅ | ✅ | ✅ |
| Agent Suggestions | ✅ | ✅ | ✅ | ✅ |
| Multi-Agent Collab | ❌ | ✅ | ✅ | ✅ |
| NLU Analysis | ❌ | ❌ | ✅ | ✅ |
| Orchestration | ❌ | ❌ | ✅ | ✅ |
| Plugin System | ❌ | ❌ | ✅ | ✅ |
| GraphQL API | ❌ | ❌ | ❌ | ✅ |

## Breaking Change Guidelines

### What Constitutes a Breaking Change

1. **Removing endpoints**
   ```diff
   - DELETE /api/v1/agents/delete/{id}
   ```

2. **Changing response structure**
   ```diff
   # v1
   {
     "agent": "developer",
     "message": "Hello"
   }
   
   # v2 (breaking)
   {
     "data": {
       "agent": "developer",
       "content": "Hello"  # renamed field
     }
   }
   ```

3. **Changing parameter requirements**
   ```diff
   # v1
   POST /api/agents/chat
   {
     "message": "required"
   }
   
   # v2 (breaking)
   POST /api/agents/chat
   {
     "message": "required",
     "agent_id": "now required"  # new required field
   }
   ```

### Non-Breaking Changes

1. **Adding optional parameters**
   ```diff
   POST /api/agents/chat
   {
     "message": "required",
   + "enhance_prompt": false  # optional, default provided
   }
   ```

2. **Adding new endpoints**
   ```diff
   + POST /api/v1/agents/analyze
   ```

3. **Adding response fields**
   ```diff
   {
     "success": true,
     "data": {...},
   + "metadata": {...}  # new field
   }
   ```

## Version-Specific Documentation

### Documentation Structure
```
docs/api/
├── current/           # Latest stable
├── v2/                # Version 2.x docs
├── v1/                # Version 1.x docs (deprecated)
└── migration/         # Migration guides
    ├── v1-to-v2.md
    └── v2-to-v3.md
```

### API Reference Generation

Using OpenAPI/Swagger specification:

```yaml
openapi: 3.0.0
info:
  title: MCP Multi-Agent Chat API
  version: 2.0.0
  description: AI-powered multi-agent collaboration system
servers:
  - url: https://api.example.com/v2
    description: Version 2 (current)
  - url: https://api.example.com/v1
    description: Version 1 (deprecated)
paths:
  /agents/chat/{agent_id}:
    post:
      summary: Chat with specific agent
      deprecated: false
      x-available-since: "1.0.0"
      x-modified-in: ["1.5.0", "2.0.0"]
```

## Client Libraries

### Version Support Policy

Each client library supports:
- **Current major version**: Full support
- **Previous major version**: Security updates only
- **Older versions**: Community support only

### Version Compatibility

```python
# Python client example
from mcp_client import Client

# Explicit version
client = Client(api_key="...", version="2.0")

# Auto-detect latest
client = Client(api_key="...")

# Check compatibility
if client.supports_feature("orchestration"):
    result = client.orchestrate(task="...")
else:
    # Fallback for older versions
    result = client.suggest_agents(task="...")
```

## Feature Flags and Gradual Rollout

### Feature Flag Implementation

```python
# Server-side feature flags
FEATURE_FLAGS = {
    "v2_orchestration": {
        "enabled": True,
        "rollout_percentage": 100,
        "allowlist": ["beta_users"]
    },
    "v3_graphql": {
        "enabled": False,
        "rollout_percentage": 0,
        "allowlist": ["internal_testing"]
    }
}
```

### Client Feature Detection

```http
GET /api/features
X-API-Key: your-key

Response:
{
    "available_features": [
        "orchestration",
        "nlu_analysis",
        "plugin_system"
    ],
    "experimental_features": [
        "graphql_api"
    ],
    "deprecated_features": [
        "legacy_chat_format"
    ]
}
```

## Deprecation Process

### 1. Deprecation Announcement

Add deprecation headers:
```http
X-Deprecation-Date: 2024-12-31
X-Deprecation-Info: Use /api/v2/agents/chat instead
Warning: 299 - "Endpoint deprecated, see docs for migration"
```

### 2. Deprecation in Documentation

```yaml
/api/v1/agents/suggest:
  post:
    deprecated: true
    x-deprecation-date: "2024-12-31"
    x-replacement: "/api/v2/agents/orchestrate"
    description: |
      **DEPRECATED**: This endpoint will be removed on 2024-12-31.
      Please use `/api/v2/agents/orchestrate` for intelligent routing.
```

### 3. Runtime Warnings

```json
{
    "success": true,
    "data": {...},
    "_warnings": [
        {
            "code": "DEPRECATION",
            "message": "This endpoint is deprecated and will be removed on 2024-12-31",
            "migration_guide": "https://docs.example.com/migration/v1-to-v2"
        }
    ]
}
```

## Version Negotiation

### Content Negotiation

```http
GET /api/agents/list
Accept: application/vnd.mcp.v2+json

Response:
Content-Type: application/vnd.mcp.v2+json
{
    "api_version": "2.0.0",
    "agents": [...]
}
```

### Version Discovery

```http
OPTIONS /api/
Response:
{
    "supported_versions": ["1.0", "1.5", "2.0"],
    "current_version": "2.0",
    "minimum_version": "1.0",
    "sunset_schedule": {
        "1.0": "2024-12-31",
        "1.5": "2025-06-30"
    }
}
```

## Testing Strategy

### Version Compatibility Tests

```python
# tests/test_api_versions.py
import pytest
from tests.api_clients import v1_client, v2_client

class TestVersionCompatibility:
    def test_v1_basic_chat(self):
        """Ensure v1 chat still works"""
        response = v1_client.post('/api/v1/agents/chat/developer')
        assert response.status_code == 200
        
    def test_v2_orchestration(self):
        """Test v2-specific features"""
        response = v2_client.post('/api/v2/agents/orchestrate')
        assert response.status_code == 200
        
    def test_version_header_negotiation(self):
        """Test version selection via headers"""
        response = client.get('/api/agents/list', 
                            headers={'X-API-Version': '1.0'})
        assert response.json()['api_version'].startswith('1.')
```

### Backward Compatibility Tests

```python
def test_backward_compatibility():
    """Ensure v2 accepts v1 request format"""
    v1_request = {
        "message": "Hello"  # v1 format
    }
    
    response = v2_client.post('/api/v2/agents/chat/dev_01', 
                            json=v1_request)
    assert response.status_code == 200
```

## Monitoring and Analytics

### Version Usage Metrics

Track API version adoption:
```python
# Metrics to track
metrics = {
    "api_version_usage": {
        "v1": {"requests": 10000, "unique_clients": 50},
        "v2": {"requests": 50000, "unique_clients": 200}
    },
    "deprecated_endpoint_usage": {
        "/api/v1/agents/suggest": 500  # Still being used
    },
    "version_migration_progress": {
        "v1_to_v2": {
            "total_clients": 250,
            "migrated": 200,
            "pending": 50
        }
    }
}
```

### Client Version Distribution

Monitor client library versions:
```sql
SELECT 
    client_version,
    COUNT(DISTINCT client_id) as unique_clients,
    COUNT(*) as total_requests
FROM api_requests
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY client_version
ORDER BY total_requests DESC;
```

## Communication Strategy

### Version Change Notifications

1. **Email notifications** to registered developers
2. **In-app banners** for deprecated features
3. **API response headers** with migration info
4. **Blog posts** for major version releases
5. **SDK console warnings** during development

### Documentation Updates

- Changelog updates for every version
- Migration guides for major versions
- API reference updates
- Example code updates
- Video tutorials for complex migrations

## Emergency Procedures

### Rolling Back API Versions

In case of critical issues:

1. **Immediate rollback** via load balancer
2. **Feature flag disable** for gradual rollback
3. **Client notification** via status page
4. **Hotfix deployment** for critical issues

### Version Pinning for Stability

Allow clients to pin specific versions:
```python
# Client configuration
client = Client(
    api_key="...",
    version="2.0.3",  # Pin to specific version
    strict_version=True  # Fail if version unavailable
)
```

## Future Considerations

### GraphQL API Versioning

For future GraphQL implementation:
```graphql
type Query {
  # Version info in schema
  apiVersion: String!
  
  # Deprecated field with reason
  agents: [Agent!]! @deprecated(reason: "Use agentsV2")
  
  # New versioned field
  agentsV2(filter: AgentFilter): AgentConnection!
}
```

### WebSocket Versioning

For real-time connections:
```javascript
const socket = io('https://api.example.com', {
    auth: { apiKey: 'your-key' },
    query: { version: '2.0' }
});

socket.on('version:deprecated', (data) => {
    console.warn('API version deprecated:', data.message);
});
```

## Conclusion

This versioning strategy ensures:
- **Stability** for existing clients
- **Innovation** through new features
- **Clear communication** about changes
- **Smooth migrations** between versions
- **Long-term maintainability** of the API