# Chain-of-Agents Workflow Templates

## Overview
The Chain-of-Agents Templates feature enables sophisticated multi-agent workflows with dependency management, staged execution, and visual progress tracking.

## Key Features
- **Pre-defined Workflow Templates**: Ready-to-use workflows for common tasks
- **Dependency-Based Execution**: Agents execute in optimal order based on dependencies
- **Multiple Execution Modes**: Sequential, parallel, or staged execution
- **Visual Progress Tracking**: Real-time visualization of workflow progress
- **Step Reordering**: Drag-and-drop to reorder steps (when allowed)
- **Detailed Output Formats**: Structured outputs for each step

## Available Templates

### 1. Detailed Code Review Chain
- **Steps**: 4 agents working in sequence
- **Agents**: Product → Coding → QA → Bug
- **Purpose**: Comprehensive code review with requirements alignment

### 2. Feature Development Pipeline
- **Steps**: 5 agents end-to-end
- **Agents**: Product → Coding → QA → Bug → DevOps
- **Purpose**: Complete feature development from story to deployment

### 3. Production Incident Response
- **Steps**: 5 agents with parallel execution
- **Agents**: Bug → Coding → QA/DevOps → Bug (RCA)
- **Purpose**: Rapid incident investigation and resolution

### 4. Code Refactoring Pipeline
- **Steps**: 4 agents with quality gates
- **Agents**: Coding → QA → Coding → Bug
- **Purpose**: Systematic refactoring with test coverage

### 5. API Design and Implementation
- **Steps**: 5 agents for API development
- **Agents**: Product → Coding → QA → Coding → Bug
- **Purpose**: Design-first API development

## Usage

### Via Web Interface
1. Navigate to `/workflows` in your browser
2. Select a template from the grid
3. Configure execution options:
   - Working directory
   - Execution mode (staged/sequential/parallel)
   - Additional context
4. Click "Execute Workflow"
5. Monitor real-time progress

### Via API
```python
# Execute a workflow
POST /api/workflows/execute
{
    "template_id": "code_review_detailed",
    "working_directory": "/path/to/project",
    "execution_mode": "staged",
    "context": {
        "focus": "security and performance"
    }
}

# Check execution status
GET /api/workflows/executions/{execution_id}

# Get available templates
GET /api/workflows/templates
```

## Implementation Details

### File Structure
```
config/
  └── workflows_v2.json     # Template definitions
services/
  └── workflow_engine.py    # Core workflow engine
routes/
  └── workflows.py          # API endpoints
static/
  └── workflows.html        # Web interface
```

### Execution Modes
1. **Sequential**: Steps execute one after another
2. **Parallel**: All steps execute simultaneously
3. **Staged**: Steps execute in dependency-based stages

### Output Formats
- `markdown`: Standard markdown documentation
- `code_diff`: Git-style code differences
- `user_stories`: Formatted user stories with acceptance criteria
- `test_report`: Structured test results
- `incident_report`: Incident timeline and analysis
- `rca_document`: Root cause analysis template

## Testing
Run the test script to verify the implementation:
```bash
./test_workflows.py
```

## Future Enhancements
- Custom workflow builder UI
- Workflow versioning and history
- Conditional execution paths
- Integration with CI/CD pipelines
- Workflow templates marketplace

**Next Action:** Test the workflow functionality by running a code review workflow on the swarm project itself.