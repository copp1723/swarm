# Multi-stage build for MCP Executive Platform
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY config/requirements/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install Node.js and runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp -d /app -s /sbin/nologin mcp

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=mcp:mcp . .

# Install MCP filesystem server
RUN npm install -g @modelcontextprotocol/server-filesystem@latest

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/instance && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.local/bin:${PATH}"

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/ready || exit 1

# Run the application
CMD ["gunicorn", "-w", "${WEB_CONCURRENCY:-2}", "--worker-class", "gevent", "--bind", "0.0.0.0:${PORT:-10000}", "--timeout", "120", "app_production:app"]
