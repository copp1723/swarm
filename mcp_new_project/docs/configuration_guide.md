# Configuration Management Guide

## Overview

The Email Agent system uses a centralized configuration management approach to avoid hardcoded values and enable easy customization. Configuration is loaded from YAML files and can be overridden with environment variables.

## Configuration Files

### 1. `config/email_agent_config.yaml`

The main configuration file for the Email Agent system. This file controls:

- **Agent Assignment Rules**: Maps task types to specific agents
- **Priority Detection**: Keywords used to determine email priority
- **Task Type Detection**: Keywords used to classify email content
- **Notification Channels**: Priority-based notification routing
- **Integration Settings**: Webhook endpoints, timeouts, and security settings
- **Feature Flags**: Enable/disable system features
- **Performance Settings**: Rate limits, timeouts, and batch sizes

### 2. `config/agents.json`

Contains agent profiles with their capabilities, tools, and specialties. Each agent has:

- `agent_id`: Unique identifier
- `name`: Display name
- `role`: Agent role/type
- `capabilities`: List of things the agent can do
- `tools`: Available tools for the agent
- `specialties`: Areas of expertise
- `preferred_models`: AI models the agent uses

## Configuration Loader

The `config/config_loader.py` module provides a centralized way to access configuration:

```python
from config.config_loader import get_config_loader

config = get_config_loader()

# Get agent assignment for a task type
assignment = config.get_task_assignment('bug_report')

# Get priority keywords
urgent_keywords = config.get_priority_keywords('urgent')

# Check feature flags
if config.get_feature_flag('auto_dispatch'):
    # Auto-dispatch is enabled
    pass
```

## Environment Variable Overrides

You can override specific configuration values using environment variables:

- `EMAIL_AGENT_MAX_TIMESTAMP_AGE`: Override webhook timestamp validation (seconds)
- `EMAIL_AGENT_AUTO_DISPATCH`: Enable/disable auto-dispatch (true/false)

## Key Configuration Sections

### Agent Assignment

```yaml
agent_assignment:
  task_type_mapping:
    code_review:
      primary: coder_01
      supporting: [tester_01]
      reason: "Code review requires coding expertise"
```

### Priority Keywords

```yaml
email_parsing:
  priority_keywords:
    urgent:
      - urgent
      - asap
      - critical
      - emergency
```

### Notification Routing

```yaml
notifications:
  channel_priority:
    urgent: [pagerduty, slack, email]
    high: [slack, email]
    normal: [email]
```

### Feature Flags

```yaml
features:
  auto_dispatch: true
  email_parsing_ml: false
  collaborative_tasks: true
```

## Adding New Configuration

1. **Add to YAML**: Update `email_agent_config.yaml` with new settings
2. **Add Accessor Method**: Add a method to `ConfigLoader` class if needed
3. **Update Code**: Replace hardcoded values with config calls
4. **Document**: Update this guide with the new configuration

## Configuration Best Practices

1. **Group Related Settings**: Keep related configuration together
2. **Use Clear Names**: Configuration keys should be self-documenting
3. **Provide Defaults**: Always have sensible defaults in the YAML
4. **Document Purpose**: Add comments in YAML explaining each section
5. **Validate Early**: Validate configuration on startup, not runtime

## Example: Adding a New Agent

1. Update `config/agents.json`:
```json
{
  "AGENT_PROFILES": {
    "new_agent": {
      "agent_id": "new_01",
      "name": "New Agent",
      "role": "new_role",
      "capabilities": ["task1", "task2"],
      "tools": ["tool1", "tool2"],
      "specialties": ["SPECIALTY1"]
    }
  }
}
```

2. Update `config/email_agent_config.yaml`:
```yaml
agent_assignment:
  task_type_mapping:
    new_task_type:
      primary: new_01
      supporting: []
      reason: "New agent handles this type"
```

3. Use in code:
```python
config = get_config_loader()
agent = config.get_agent_by_id('new_01')
```

## Troubleshooting

### Configuration Not Loading

1. Check file paths are correct
2. Verify YAML syntax is valid
3. Check file permissions
4. Look for error messages in logs

### Environment Variables Not Working

1. Ensure variables are exported
2. Check variable names match exactly
3. Restart the application after changes

### Missing Configuration

If a configuration key is missing:

1. The system will use defaults where possible
2. Check logs for warnings about missing config
3. Add the missing configuration to the YAML file

## Configuration Reload

To reload configuration without restarting:

```python
config = get_config_loader()
config.reload_configs()
```

This is useful for development but should be used carefully in production.