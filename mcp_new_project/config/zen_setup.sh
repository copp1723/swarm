#!/bin/bash
# Zen MCP Server Setup Script

echo "Setting up Zen MCP Server for Multi-Agent System"
echo "================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    echo "Visit: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✓ Docker is installed and running"

# Login to Docker Hub
echo ""
echo "Logging into Docker Hub..."
docker login -u copp1723

# Pull the Zen MCP Server image
echo ""
echo "Pulling Zen MCP Server image..."
docker pull beehiveinnovations/zen-mcp-server

# Create environment file for Zen
echo ""
echo "Creating Zen environment configuration..."
cat > .env.zen << EOF
# Zen MCP Server Configuration
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Add more model keys if needed
# ANTHROPIC_API_KEY=your_key_here
# GROQ_API_KEY=your_key_here
EOF

# Create docker-compose file for easier management
echo ""
echo "Creating docker-compose configuration..."
cat > docker-compose.zen.yml << 'EOF'
version: '3.8'

services:
  zen-mcp:
    image: beehiveinnovations/zen-mcp-server
    container_name: zen-mcp-server
    ports:
      - "3000:3000"
    env_file:
      - .env.zen
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    volumes:
      - ./zen-data:/app/data
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge
EOF

# Create data directory
mkdir -p zen-data

echo ""
echo "✅ Zen MCP Server setup complete!"
echo ""
echo "To start the Zen MCP Server, run:"
echo "  docker-compose -f docker-compose.zen.yml up -d"
echo ""
echo "To stop the server:"
echo "  docker-compose -f docker-compose.zen.yml down"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.zen.yml logs -f"
echo ""
echo "The server will be available at http://localhost:3000"