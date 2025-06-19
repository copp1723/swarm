#!/bin/bash

# Convoy Route Configuration Script
# This script sets up the webhook routes in Convoy for the Email Agent

set -e

# Configuration
CONVOY_URL="${CONVOY_URL:-http://localhost:8080}"
CONVOY_USERNAME="${CONVOY_USERNAME:-admin}"
CONVOY_PASSWORD="${CONVOY_PASSWORD:-changeme}"
EMAIL_AGENT_URL="${EMAIL_AGENT_URL:-http://mcp-executive:5006}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Convoy Route Configuration${NC}"
echo "================================"

# Wait for Convoy to be ready
echo -e "\n${YELLOW}Waiting for Convoy to be ready...${NC}"
for i in {1..30}; do
    if curl -s -f "${CONVOY_URL}/health" > /dev/null; then
        echo -e "${GREEN}Convoy is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Function to create a route
create_route() {
    local name=$1
    local path=$2
    local destination=$3
    local description=$4
    
    echo -e "\n${YELLOW}Creating route: ${name}${NC}"
    echo "Path: ${path}"
    echo "Destination: ${destination}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "${CONVOY_URL}/api/v1/routes" \
        -u "${CONVOY_USERNAME}:${CONVOY_PASSWORD}" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
    "name": "${name}",
    "description": "${description}",
    "match": {
        "type": "http_path",
        "value": "${path}"
    },
    "destinations": [
        {
            "url": "${destination}",
            "method": "POST",
            "headers": {
                "X-Convoy-Source": "convoy",
                "X-Original-Path": "${path}"
            }
        }
    ],
    "retries": {
        "count": 5,
        "backoff": {
            "type": "exponential",
            "initial": "1s",
            "max": "30s"
        }
    },
    "timeout": "30s",
    "rate_limit": {
        "requests_per_second": 100
    }
}
EOF
    )
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Route created successfully${NC}"
    else
        echo -e "${RED}✗ Failed to create route (HTTP ${http_code})${NC}"
        echo "Response: $body"
    fi
}

# Create routes

# 1. Mailgun Webhook Route
create_route \
    "mailgun-webhook" \
    "/webhooks/mailgun" \
    "${EMAIL_AGENT_URL}/api/email-agent/webhooks/mailgun" \
    "Route for Mailgun email webhooks to Email Agent"

# 2. Email Agent Health Check Route (for monitoring)
create_route \
    "email-agent-health" \
    "/webhooks/email-agent/health" \
    "${EMAIL_AGENT_URL}/api/email-agent/health" \
    "Health check route for Email Agent monitoring"

# 3. Fan-out route for audit logging (example)
if [ "${ENABLE_AUDIT:-false}" = "true" ]; then
    echo -e "\n${YELLOW}Creating fan-out route with audit logging...${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "${CONVOY_URL}/api/v1/routes" \
        -u "${CONVOY_USERNAME}:${CONVOY_PASSWORD}" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
    "name": "mailgun-webhook-with-audit",
    "description": "Mailgun webhooks with audit logging",
    "match": {
        "type": "http_path",
        "value": "/webhooks/mailgun-audit"
    },
    "destinations": [
        {
            "url": "${EMAIL_AGENT_URL}/api/email-agent/webhooks/mailgun",
            "method": "POST",
            "headers": {
                "X-Convoy-Source": "convoy",
                "X-Route-Type": "primary"
            }
        },
        {
            "url": "${AUDIT_SERVICE_URL:-http://audit-service:4000}/events",
            "method": "POST",
            "headers": {
                "X-Convoy-Source": "convoy",
                "X-Route-Type": "audit"
            }
        }
    ],
    "retries": {
        "count": 3,
        "backoff": {
            "type": "exponential",
            "initial": "2s",
            "max": "60s"
        }
    }
}
EOF
    )
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Fan-out route created successfully${NC}"
    else
        echo -e "${RED}✗ Failed to create fan-out route${NC}"
    fi
fi

# List all routes
echo -e "\n${YELLOW}Listing all configured routes:${NC}"
curl -s -X GET "${CONVOY_URL}/api/v1/routes" \
    -u "${CONVOY_USERNAME}:${CONVOY_PASSWORD}" | jq -r '.data[] | "\(.name): \(.match.value) -> \(.destinations[0].url)"' || echo "Failed to list routes"

echo -e "\n${GREEN}Route configuration complete!${NC}"
echo -e "\nTo test the Mailgun webhook route:"
echo -e "${YELLOW}curl -X POST ${CONVOY_URL}/webhooks/mailgun \\
  -H 'Content-Type: application/json' \\
  -d '{your-webhook-payload}'${NC}"