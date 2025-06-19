# Zen MCP Server Setup Guide

## Quick Start

Your API keys are already configured! Here's how to get Zen MCP running:

### 1. Prerequisites
- Docker Desktop installed and running
- Terminal/Command line access

### 2. Run the Setup Script

```bash
cd /Users/copp1723/Desktop/swarm/mcp_new_project
./config/zen_setup.sh
```

### 3. Start Zen MCP Server

```bash
docker-compose -f docker-compose.zen.yml up -d
```

### 4. Verify Installation

Check if Zen is running:
```bash
curl http://localhost:3000/health
```

Or in your browser, visit: http://localhost:5006/api/zen/status

## Features Now Available

### For Coder Agent
- **Code Review**: Professional multi-model code analysis
- **Refactoring**: Intelligent code improvements
- **Analysis**: Deep code understanding
- **Tracing**: Call-flow mapping

### For Bug Agent
- **Debug**: Root cause analysis with fix suggestions
- **Tracing**: Execution path analysis

### For Product Agent
- **Planning**: Step-by-step project planning
- **Consensus**: Multi-model perspective gathering
- **Deep Thinking**: Extended reasoning for complex problems

### For All Agents
- **Multi-Model Chat**: Query multiple AI models simultaneously
- **Enhanced Intelligence**: Combine OpenAI, Gemini, and other models

## Using Zen Features

### 1. In Agent Chat
Agents automatically use Zen when available for enhanced responses.

### 2. Via API
```javascript
// Code review example
const response = await fetch('/api/zen/code-review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        code_path: '/path/to/file.js',
        agent_id: 'coder_01',
        focus_areas: ['security', 'performance']
    })
});
```

### 3. Multi-Model Query
```javascript
const response = await fetch('/api/zen/multi-model', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        query: 'How should I architect a real-time chat system?'
    })
});
```

## Troubleshooting

### Docker Issues
```bash
# Check if Docker is running
docker info

# View Zen logs
docker-compose -f docker-compose.zen.yml logs -f

# Restart Zen
docker-compose -f docker-compose.zen.yml restart
```

### Connection Issues
1. Ensure port 3000 is not in use
2. Check firewall settings
3. Verify API keys are correct

## Managing Zen

### Stop Zen
```bash
docker-compose -f docker-compose.zen.yml down
```

### Update Zen
```bash
docker-compose -f docker-compose.zen.yml pull
docker-compose -f docker-compose.zen.yml up -d
```

### View Resource Usage
```bash
docker stats zen-mcp-server
```

## API Keys Status

✅ **OpenAI**: Configured
✅ **Gemini**: Configured  
✅ **OpenRouter**: Configured

## Next Steps

1. Start the Zen server using the commands above
2. Test the enhanced agents with complex tasks
3. Use code review on your important files
4. Try multi-model consensus for difficult decisions

The combination of Zen (multi-model AI) + Supermemory (persistent knowledge) transforms your agents into highly intelligent, learning assistants!