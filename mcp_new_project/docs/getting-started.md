# Getting Started Guide

This guide will help you get the MCP Multi-Agent System up and running in minutes.

## Prerequisites

Before you begin, ensure you have:

### Required
- **Python 3.11 or higher** - [Download Python](https://www.python.org/downloads/)
- **Node.js 16 or higher** - [Download Node.js](https://nodejs.org/) (for MCP servers)
- **Git** - [Download Git](https://git-scm.com/)
- **OpenRouter API Key** - [Get API Key](https://openrouter.ai/)

### Optional (for advanced features)
- **Redis 6.0+** - [Download Redis](https://redis.io/download) (for background tasks)
- **PostgreSQL 13+** - [Download PostgreSQL](https://www.postgresql.org/download/) (for production)

## Installation

### 1. Clone the Repository

```bash
# Navigate to your projects directory
cd ~/Desktop

# Clone the repository (if not already present)
git clone https://github.com/your-org/swarm.git
cd swarm/mcp_new_project
```

### 2. Set Up Python Environment

We recommend using a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file from the template:

```bash
# Copy the example file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

Essential configuration:

```env
# Required - Your OpenRouter API key
OPENROUTER_API_KEY=your_api_key_here

# Optional but recommended
PORT=5006
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/mcp_executive.db

# For background tasks (optional)
REDIS_URL=redis://localhost:6379/0
```

### 4. Initialize the Database

The database will be created automatically on first run, but you can initialize it manually:

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 5. Optional: Start Redis (for background tasks)

If you want to use background task processing:

```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Or run manually
redis-server
```

### 6. Start the Application

For development:
```bash
python app.py
```

For production:
```bash
# Using the startup script
python run_server.py

# Or directly with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
```

You should see:
```
INFO - All databases initialized successfully
INFO - MCP server filesystem initialized successfully
 * Running on http://127.0.0.1:5006
 * Debug mode: on
```

### 7. Access the Interface

Open your web browser and navigate to: **http://localhost:5006**

### 8. Verify Installation

Check the health endpoint:
```bash
curl http://localhost:5006/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "async_database": "connected",
  "mcp_servers": "initialized"
}
```

## First Steps

### Your First Agent Chat {#first-chat}

1. **Select an Agent** - Click on any agent window (e.g., "Developer")
2. **Choose a Model** - Select from the dropdown (e.g., "DeepSeek R1")
3. **Type a Message** - Enter your query in the input field
4. **Send** - Press Enter or click the send button

Example first message:
```
Can you explain what this project does and how it's structured?
```

### Uploading Files

1. Click the **"Upload File"** button in any agent window
2. Select a file from your computer
3. The agent will automatically analyze it

### Running a Collaborative Task {#first-collaboration}

1. Navigate to the **Collaboration Hub** at the bottom of the page
2. Select a **Workflow Template** or enter a custom task
3. Choose which agents should participate
4. Specify the working directory (default: `/Users/copp1723/Desktop`)
5. Click **"Start Collaboration"**

Example collaborative task:
```
Review the Python files in this directory for code quality, 
security issues, and suggest improvements
```

## Keyboard Shortcuts

The interface supports several keyboard shortcuts for power users:

- **Ctrl/Cmd + K** - Quick search
- **Ctrl/Cmd + Enter** - Send message
- **Alt + 1-6** - Focus specific agent
- **Alt + C** - Focus collaboration hub
- **Alt + T** - Toggle dark/light theme
- **Ctrl + /** - Show keyboard shortcuts help

## Common Issues

### "Connection Refused" Error

If you see this error:
1. Ensure the server is running (`python app.py`)
2. Check the port isn't already in use
3. Try a different port: `PORT=5007 python app.py`

### "API Key Invalid" Error

1. Verify your OpenRouter API key is correct
2. Ensure the `.env` file is in the project root
3. Restart the server after adding the API key

### MCP Filesystem Access Issues

If agents can't access files:
1. Ensure Node.js is installed: `node --version`
2. Check MCP configuration in `config/mcp_config.json`
3. Verify directory permissions

## Next Steps

Now that you have the system running:

1. **Explore Agent Capabilities** - Read the [Agent Reference](./agents/README.md)
2. **Try Workflow Templates** - See [Workflow Templates Guide](./user-guide.md#workflows)
3. **Customize Settings** - Check [Configuration Options](./configuration.md)
4. **Learn the API** - Review [API Documentation](./api/README.md)

## Getting Help

- **Quick Test**: Run `python test_agents.py` to verify setup
- **Logs**: Check `logs/mcp_server.log` for detailed errors
- **Support**: See [Troubleshooting Guide](./troubleshooting.md)