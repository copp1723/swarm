# Natural Language Understanding & Intelligent Orchestration

## Overview

The NLU and Orchestration system provides intelligent task analysis and routing, automatically determining the best agents and workflow for any given task. This system eliminates the need for manual agent selection and provides optimal execution strategies.

## Architecture

### Components

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Input    │────▶│   NLU Service    │────▶│  Orchestrator   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐          ┌──────────────┐
                        │Intent/Entity │          │ Agent Router │
                        │  Extraction  │          │   Workflow   │
                        └──────────────┘          └──────────────┘
```

### NLU Service (`services/nlu_service.py`)

The NLU service provides:
- **Intent Classification** - Determines the primary purpose of the task
- **Entity Extraction** - Identifies key components (files, functions, errors)
- **Context Analysis** - Assesses urgency, complexity, and scope
- **Technology Detection** - Recognizes programming languages and frameworks

### Orchestrator Service (`services/orchestrator_service.py`)

The orchestrator handles:
- **Agent Selection** - Chooses optimal agents based on task analysis
- **Workflow Generation** - Creates execution plans with ordered steps
- **Resource Allocation** - Estimates time and computational requirements
- **Progress Tracking** - Monitors execution and handles failures

## Intent Types

### Supported Intents

| Intent | Description | Example | Primary Agents |
|--------|-------------|---------|----------------|
| `CODE_DEVELOPMENT` | Creating new features | "Build a REST API" | Developer, Architect |
| `BUG_FIXING` | Resolving issues | "Fix login crash" | Bug, Developer |
| `CODE_REVIEW` | Analyzing code quality | "Review auth module" | Code Reviewer, Security |
| `TESTING` | Creating/running tests | "Write unit tests" | QA, Developer |
| `DOCUMENTATION` | Writing docs | "Document the API" | General, Developer |
| `ARCHITECTURE` | System design | "Design microservices" | Architect |
| `SECURITY_ANALYSIS` | Security review | "Check for vulnerabilities" | Security |
| `PERFORMANCE` | Optimization | "Improve query speed" | Developer, DevOps |
| `REFACTORING` | Code improvement | "Refactor user service" | Developer |
| `DEPLOYMENT` | Release management | "Deploy to production" | DevOps |
| `DEBUGGING` | Issue investigation | "Debug memory leak" | Bug, Developer |
| `GENERAL_QUERY` | Information requests | "How does X work?" | General |

## Entity Recognition

### Extracted Entities

```python
{
    "file_paths": ["src/auth.py", "tests/test_auth.py"],
    "functions": ["login", "validate_token"],
    "classes": ["UserAuth", "TokenManager"],
    "modules": ["authentication", "authorization"],
    "errors": ["NullPointerException", "timeout"],
    "technologies": ["Python", "Flask", "PostgreSQL"],
    "urls": ["https://api.example.com"],
    "issues": ["crash", "memory leak", "slow performance"]
}
```

### Pattern Matching

The system uses regex patterns to identify:
- **File Paths** - `/path/to/file.ext`, `module/component.py`
- **Code Elements** - `functionName()`, `ClassName`, `variable_name`
- **Error Patterns** - `XxxError`, `XxxException`, stack traces
- **Tech Stack** - Language names, framework mentions, tools

## Orchestration Workflows

### Workflow Types

#### 1. Sequential Workflow
Tasks executed one after another
```python
{
    "workflow_type": "sequential",
    "steps": [
        {"agent": "architect", "action": "design"},
        {"agent": "developer", "action": "implement"},
        {"agent": "qa", "action": "test"}
    ]
}
```

#### 2. Parallel Workflow
Multiple agents work simultaneously
```python
{
    "workflow_type": "parallel",
    "groups": [
        {
            "agents": ["security", "qa"],
            "action": "analyze",
            "sync_point": true
        }
    ]
}
```

#### 3. Conditional Workflow
Branching based on results
```python
{
    "workflow_type": "conditional",
    "condition": "if_tests_fail",
    "true_branch": ["bug", "developer"],
    "false_branch": ["devops"]
}
```

### Workflow Templates

#### Bug Fix Template
```python
BUG_FIX_WORKFLOW = {
    "steps": [
        {
            "step_number": 1,
            "step": "Reproduce and analyze the bug",
            "agent": "bug",
            "action": "analyze",
            "estimated_duration": 300
        },
        {
            "step_number": 2,
            "step": "Develop fix",
            "agent": "developer",
            "action": "fix",
            "estimated_duration": 600
        },
        {
            "step_number": 3,
            "step": "Test the fix",
            "agent": "qa",
            "action": "test",
            "estimated_duration": 300
        },
        {
            "step_number": 4,
            "step": "Validate no regressions",
            "agent": "qa",
            "action": "regression_test",
            "estimated_duration": 200
        }
    ]
}
```

## API Usage

### Task Analysis Endpoint

```bash
POST /api/agents/analyze
Content-Type: application/json
X-API-Key: your-api-key

{
    "task": "Fix the critical bug in payment processing that's causing transactions to fail"
}
```

**Response:**
```json
{
    "success": true,
    "analysis": {
        "intent": {
            "primary": "bug_fixing",
            "confidence": 0.95,
            "secondary": ["debugging", "testing"]
        },
        "entities": {
            "modules": ["payment processing"],
            "issues": ["transactions fail"],
            "urgency": "critical"
        },
        "structured_task": {
            "task_type": "bug_fixing",
            "recommended_agents": ["bug", "developer", "qa"],
            "priority": "high",
            "entities": {
                "modules": ["payment processing"],
                "issues": ["critical bug", "transactions fail"]
            },
            "context": {
                "urgency": "critical",
                "complexity": "high",
                "estimated_effort": "medium"
            }
        }
    }
}
```

### Orchestration Endpoint

```bash
POST /api/agents/orchestrate
Content-Type: application/json
X-API-Key: your-api-key

{
    "task": "Create a new authentication system with JWT tokens",
    "working_directory": "/path/to/project",
    "priority": "medium",
    "dry_run": true
}
```

**Response (Dry Run):**
```json
{
    "success": true,
    "plan": {
        "task_id": "orch_123abc",
        "priority": "medium",
        "estimated_duration": 1800,
        "nlu_analysis": {
            "intent": {
                "primary": "code_development",
                "confidence": 0.92
            }
        },
        "routing": {
            "primary_agents": ["architect", "developer"],
            "supporting_agents": ["security", "qa"],
            "workflow_type": "feature_development",
            "confidence": 0.88,
            "reasoning": "New authentication system requires architecture design followed by secure implementation"
        },
        "execution_steps": [
            {
                "step_number": 1,
                "step": "Design authentication architecture",
                "agent": "architect",
                "action": "design",
                "dependencies": []
            },
            {
                "step_number": 2,
                "step": "Implement JWT token system",
                "agent": "developer",
                "action": "implement",
                "dependencies": ["step_1"]
            }
        ]
    }
}
```

### Execution Response

When `dry_run: false`, the system executes the plan:

```json
{
    "success": true,
    "task_id": "task_456def",
    "orchestration": {
        "plan_id": "orch_123abc",
        "routing_decision": {
            "workflow_type": "feature_development",
            "agents_used": ["architect", "developer", "security", "qa"]
        },
        "execution_summary": {
            "steps_completed": 4,
            "steps_total": 4,
            "duration": 1650
        },
        "estimated_vs_actual": {
            "estimated_duration": 1800,
            "actual_duration": 1650,
            "variance_percentage": -8.33
        }
    },
    "conversations": [
        {
            "agent": "architect",
            "role": "Software Architect",
            "content": "I'll design a secure JWT authentication system..."
        }
    ]
}
```

## Configuration

### Confidence Thresholds

```python
# In nlu_service.py
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for intent detection

# In orchestrator_service.py
ROUTING_CONFIDENCE_THRESHOLD = 0.7  # Minimum for automatic routing
```

### Workflow Customization

Add custom workflows in `orchestrator_service.py`:

```python
CUSTOM_WORKFLOW = {
    "name": "custom_analysis",
    "trigger_intents": ["performance", "security_analysis"],
    "steps": [
        {
            "agent": "security",
            "action": "scan",
            "parallel": True
        },
        {
            "agent": "developer",
            "action": "profile",
            "parallel": True
        }
    ]
}
```

## Best Practices

### 1. Task Description
- Be specific about the problem or goal
- Include relevant file names or module names
- Mention any error messages or symptoms
- Specify urgency with words like "critical", "urgent"

### 2. Context Provision
```python
# Good
"Fix the authentication bug in login.py causing 500 errors"

# Better
"Fix the critical authentication bug in login.py where JWT validation fails and returns 500 errors for expired tokens"
```

### 3. Using Dry Run
Always test with `dry_run: true` first to:
- Review the execution plan
- Verify agent selection
- Check estimated duration
- Validate workflow steps

### 4. Priority Levels
- `critical` - Production issues, security vulnerabilities
- `high` - Important features, significant bugs
- `medium` - Standard development tasks
- `low` - Nice-to-have improvements

## Monitoring & Debugging

### Execution Tracking

Monitor orchestrated tasks:
```python
# Get task status
GET /api/tasks/{task_id}/status

# Get execution logs
GET /api/audit/logs?task_id={task_id}

# Get performance metrics
GET /api/audit/statistics?agent=orchestrator
```

### Common Issues

1. **Low Confidence Scores**
   - Task description too vague
   - Multiple conflicting intents
   - Solution: Be more specific

2. **Wrong Agent Selection**
   - Ambiguous task type
   - Missing context
   - Solution: Provide more details

3. **Workflow Failures**
   - Agent errors during execution
   - Dependency issues
   - Solution: Check agent logs

## Advanced Features

### Custom Intent Patterns

Add domain-specific patterns:
```python
# In nlu_service.py
CUSTOM_PATTERNS = {
    'ml_training': r'(train|fit|model|dataset|epoch)',
    'data_pipeline': r'(etl|extract|transform|load|pipeline)'
}
```

### Conditional Routing

```python
# In orchestrator_service.py
if "production" in task_lower and urgency == "critical":
    routing["additional_agents"].append("devops")
    routing["escalation"] = True
```

### Multi-Stage Orchestration

For complex tasks spanning multiple phases:
```python
{
    "phases": [
        {
            "name": "Planning",
            "agents": ["architect"],
            "duration": 1800
        },
        {
            "name": "Implementation", 
            "agents": ["developer", "developer"],
            "parallel": True,
            "duration": 7200
        },
        {
            "name": "Validation",
            "agents": ["qa", "security"],
            "duration": 3600
        }
    ]
}
```

## Integration with Other Systems

### Audit Integration
All orchestrated tasks are automatically audited:
- Intent detection results
- Routing decisions
- Agent interactions
- Performance metrics

### Plugin Integration
Plugins can:
- Add custom intents
- Provide specialized routing
- Extend workflow templates
- Monitor orchestration metrics

### MCP Integration
Orchestrator can leverage MCP tools:
- File system analysis for context
- Code inspection for better routing
- Real-time file monitoring
- Integrated documentation lookup