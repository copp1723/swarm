# Installation Guide

This guide provides detailed installation instructions for different operating systems and deployment scenarios.

## Table of Contents
- [System Requirements](#system-requirements)
- [Quick Install](#quick-install)
- [Detailed Installation](#detailed-installation)
- [Production Setup](#production-setup)
- [Docker Installation](#docker-installation)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 2GB free space
- **Python**: 3.11 or higher
- **Node.js**: 16 or higher (for MCP servers)

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 10GB free space
- **OS**: Ubuntu 20.04+, macOS 12+, Windows 10+

## Quick Install

```bash
# Clone repository
git clone https://github.com/your-org/swarm.git
cd swarm/mcp_new_project

# Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OpenRouter API key

# Start application
python app.py
```

## Detailed Installation

### macOS Installation

1. **Install Homebrew** (if not installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. **Install Python 3.11+**:
```bash
brew install python@3.11
```

3. **Install Node.js**:
```bash
brew install node
```

4. **Install Redis** (optional, for background tasks):
```bash
brew install redis
brew services start redis
```

5. **Clone and setup project**:
```bash
cd ~/Desktop
git clone https://github.com/your-org/swarm.git
cd swarm/mcp_new_project

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Ubuntu/Debian Installation

1. **Update system packages**:
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Install Python 3.11**:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

3. **Install Node.js**:
```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
```

4. **Install Redis** (optional):
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

5. **Install PostgreSQL** (optional, for production):
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

6. **Clone and setup project**:
```bash
cd ~
git clone https://github.com/your-org/swarm.git
cd swarm/mcp_new_project

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Windows Installation

1. **Install Python 3.11**:
   - Download from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Install Node.js**:
   - Download from [nodejs.org](https://nodejs.org/)
   - Use LTS version

3. **Install Git**:
   - Download from [git-scm.com](https://git-scm.com/)

4. **Install Redis** (optional):
   - Download from [Redis Windows](https://github.com/microsoftarchive/redis/releases)
   - Or use WSL2 for native Redis

5. **Clone and setup project**:
```powershell
cd C:\Users\YourName\Desktop
git clone https://github.com/your-org/swarm.git
cd swarm\mcp_new_project

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Production Setup

### 1. Environment Configuration

Create production `.env`:
```env
# Production settings
PRODUCTION=true
DEBUG=false
FLASK_ENV=production

# API Keys
OPENROUTER_API_KEY=your_production_key

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/mcp_production

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
FLASK_SECRET_KEY=generate-a-secure-random-key

# Performance
GUNICORN_WORKERS=4
ASYNC_DB_POOL_SIZE=20
```

### 2. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres createdb mcp_production
sudo -u postgres createuser mcp_user -P

# Grant permissions
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE mcp_production TO mcp_user;
\q

# Run migrations
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 3. Systemd Service

Create `/etc/systemd/system/mcp-agent.service`:
```ini
[Unit]
Description=MCP Multi-Agent System
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/swarm/mcp_new_project
Environment="PATH=/opt/swarm/venv/bin"
ExecStart=/opt/swarm/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5006 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mcp-agent
sudo systemctl start mcp-agent
```

### 4. Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Static files
    location /static {
        alias /opt/swarm/mcp_new_project/static;
        expires 1d;
    }
}
```

## Docker Installation

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5006:5006"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/mcp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=mcp
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A app.celery worker --loglevel=info
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/mcp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p uploads logs instance

# Expose port
EXPOSE 5006

# Start command
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5006", "app:app"]
```

Run with Docker:
```bash
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall requirements
pip install -r requirements.txt
```

2. **Redis Connection Error**:
```bash
# Check if Redis is running
redis-cli ping

# Start Redis
redis-server  # or brew services start redis
```

3. **Database Connection Error**:
```bash
# Check database URL in .env
echo $DATABASE_URL

# Test connection
python -c "from app import db; print(db.engine.url)"
```

4. **Port Already in Use**:
```bash
# Find process using port
lsof -i :5006  # macOS/Linux
netstat -ano | findstr :5006  # Windows

# Use different port
PORT=5007 python app.py
```

### Verification Steps

1. **Check Installation**:
```bash
python test_imports.py
```

2. **Check Health**:
```bash
curl http://localhost:5006/health
```

3. **Run Diagnostics**:
```bash
python diagnose.py
```

### Getting Help

- Check logs: `tail -f logs/mcp_server.log`
- Run tests: `python test_agents.py`
- See [Troubleshooting Guide](./docs/troubleshooting.md)
- Report issues: [GitHub Issues](https://github.com/your-org/swarm/issues)