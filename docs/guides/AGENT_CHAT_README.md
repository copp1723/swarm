# MCP Multi-Agent Chat System

This project implements a multi-agent chat system with individual agent chat windows and collaborative task execution.

## Features

- **Individual Agent Chat Windows**: Chat directly with specialized agents (Architect, Developer, QA Engineer, Security Analyst, DevOps Engineer)
- **Model Selection**: Choose between different AI models for each agent
- **Collaborative Tasks**: Tag multiple agents to work together on complex tasks
- **Real-time Status Updates**: Monitor task progress and agent activity
- **Chat History**: Persistent chat history for each agent

## Project Structure

```
mcp_new_project/
├── app.py                      # Main Flask application
├── models/                     # Database models
├── services/                   # Business logic
│   ├── multi_agent_executor.py # Enhanced with chat functionality
│   └── multi_agent_service.py  # Task orchestration
├── routes/                     # API endpoints
│   └── agents.py              # Agent-related endpoints
├── static/                     # Frontend files
│   └── index.html             # Multi-agent chat interface
└── utils/                      # Utility functions
```

## API Endpoints

### Agent Profiles
- `GET /api/agents/profiles` - Get all available agent profiles

### Individual Agent Chat
- `POST /api/agents/chat/<agent_id>` - Send a message to a specific agent
- `GET /api/agents/chat_history/<agent_id>` - Get chat history for an agent

### Collaborative Tasks
- `POST /api/agents/collaborate` - Start a collaborative task with tagged agents
- `GET /api/agents/conversation/<task_id>` - Get task status and conversation

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   Create a `.env` file with:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access the Interface**:
   Open http://localhost:5006 in your browser

## Usage

### Individual Agent Chat
1. Select an agent window
2. Choose a model from the dropdown
3. Type a message and press Enter
4. The agent will respond based on its specialized role

### Collaborative Tasks
1. Enter a task description in the Collaboration Hub
2. Check the agents you want to involve
3. Specify the working directory
4. Click "Start Collaboration"
5. Monitor progress in real-time

## Testing

Run the test script to verify functionality:
```bash
python test_agents.py
```

## Agent Profiles

- **Architect (Planner)**: Strategic planning and system design
- **Developer (Coder)**: Implementation and code writing
- **QA Engineer (Tester)**: Testing and quality assurance
- **Security Analyst**: Security assessment and vulnerability detection
- **DevOps Engineer**: Infrastructure and deployment

## Next Steps

1. **Persistence**: Implement database storage for chat histories
2. **Real-time Updates**: Add WebSocket support for live updates
3. **Enhanced UI**: Improve the frontend with modern frameworks
4. **Agent Tools**: Integrate MCP tools for agents to use
5. **Custom Agents**: Allow users to create custom agent profiles