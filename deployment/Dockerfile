# Multi-stage build for MCP Executive Platform
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    gnupg \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm for npx
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY config/requirements/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt gunicorn gevent

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    nodejs \
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

# Make startup script executable before switching users
RUN chmod +x scripts/render_start.sh

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/instance && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.local/bin:${PATH}"

# Expose port (Render will assign the actual port via PORT env var)
EXPOSE $PORT

# Health check - use PORT env var for dynamic port
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Run the application with the startup script
CMD ["./scripts/render_start.sh"]
