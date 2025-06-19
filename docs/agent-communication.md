# Agent-to-Agent Communication Feature

## Overview

The Agent-to-Agent Communication feature enables MCP agents to collaborate by sending requests and receiving responses from other agents during task execution. This creates a more dynamic and intelligent multi-agent system where agents can leverage each other's expertise.

## How It Works

### Backend Architecture

1. **Communication Protocol**
   - Agents can request help using the format: `@AgentName: your question or request`
   - The system parses these requests and routes them to the appropriate agent
   - Responses are captured and appended to the requesting agent's output

2. **Data Structure**
   ```python
   AgentMessage:
   - from_agent: str
   - to_agent: str  
   - message: str
   - timestamp: datetime
   - task_id: str
   - message_id: str
   - response: Optional[str]
   - response_timestamp: Optional[datetime]
   ```

3. **Real-time Updates**
   - WebSocket integration provides live updates as agents communicate
   - Messages are broadcast to connected clients via Socket.IO

### Frontend Features

1. **Visual Indicators**
   - Special styling for agent communication messages
   - Animated "LIVE" indicator during active communications
   - Arrow indicators showing communication flow

2. **Collaboration Window**
   - Displays agent communications in chronological order
   - Shows both requests and responses
   - Updates in real-time via WebSocket

## Usage

### For Agents

Agents can request help from other agents by including messages in this format:

```
@Developer: Can you review this code structure?
@Security: What vulnerabilities do you see in this authentication flow?
@QA: What edge cases should I consider for this feature?
```

### Available Agents

The system automatically maps these agent names:
- Developer (coder_01)
- Architect (planner_01) 
- QA Engineer (tester_01)
- Security Expert (security_01)
- DevOps Engineer (devops_01)
- General Assistant (general_01)

### Example Communication Flow

1. **Architect** analyzing system design sees authentication concerns
2. Sends: `@Security: Please review the authentication flow in auth.py`
3. **Security Expert** receives the request and analyzes auth.py
4. Responds with security recommendations
5. Response is appended to Architect's analysis

## API Endpoints

### WebSocket Events

**Client -> Server:**
- `join_task`: Join a task room for real-time updates
- `get_agent_communications`: Retrieve all communications for a task

**Server -> Client:**
- `agent_communication`: New agent-to-agent message
- `system_notification`: General system updates including communications
- `task_progress`: Task execution progress updates

### REST API

The multi-agent executor returns agent communications in the task conversation:

```python
GET /api/agents/conversation/{task_id}

Response:
{
    "conversations": [...],
    "agent_communications": [...],
    "all_communications": [...]  # Merged and sorted by timestamp
}
```

## Configuration

Agent communication is enabled by default in collaborative tasks. Agents are informed about available colleagues through their system prompts.

### Prompt Enhancement

The system automatically adds communication instructions to agent prompts:

```
AGENT COMMUNICATION: You can request help from other agents using the format: @AgentName: your question or request
Available agents: developer, architect, qa engineer, security expert, devops engineer, general assistant
```

## Benefits

1. **Enhanced Collaboration**: Agents can leverage each other's specialized knowledge
2. **Better Analysis**: Security experts can review code identified by developers
3. **Comprehensive Coverage**: QA can get context from architects about intended behavior
4. **Real-time Visibility**: Users can see agents collaborating in real-time

## Technical Details

### WebSocket Integration

The feature uses Flask-SocketIO for real-time bidirectional communication:
- Clients join task-specific rooms
- Agent communications are broadcast to room members
- Updates include both the request and response phases

### Storage

Agent communications are stored with the task:
- In-memory storage during task execution
- Persisted to database for historical analysis
- Retrieved via task conversation API

## Future Enhancements

- Agent communication analytics
- Communication patterns visualization
- Multi-hop communications (Agent A -> B -> C)
- Priority-based message routing
- Agent expertise matching for optimal routing