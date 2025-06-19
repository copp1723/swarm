"""
Shared constants for the MCP Executive application.
This file centralizes magic strings and configuration values used across the application.
"""
# File extensions allowed for upload
ALLOWED_EXTENSIONS = {
    'txt', 'py', 'js', 'ts', 'json', 'yaml', 'yml', 'md', 
    'html', 'css', 'jsx', 'tsx'
}

# Agent specialties
class AgentSpecialty:
    PRODUCT_MANAGEMENT = "PRODUCT_MANAGEMENT"
    SOFTWARE_DEVELOPMENT = "SOFTWARE_DEVELOPMENT"
    TESTING = "TESTING"
    INCIDENT_MANAGEMENT = "INCIDENT_MANAGEMENT"
    DEVOPS = "DEVOPS"
    CLOUD = "CLOUD"
    DATA_SCIENCE = "DATA_SCIENCE"
    GENERAL = "GENERAL"