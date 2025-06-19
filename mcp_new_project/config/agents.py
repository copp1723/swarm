"""
Agent Configuration Module
Loads agent profiles from agents.json
"""

import json
import os
from typing import Dict, Any

# Load agent profiles from JSON file
def load_agent_profiles() -> Dict[str, Any]:
    """Load agent profiles from agents.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'agents.json')
    
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    return data.get('AGENT_PROFILES', {})


# Export agent profiles
AGENT_PROFILES = load_agent_profiles()

# Agent IDs for easy reference (derived from config)
AGENT_IDS = {
    profile['role'].upper(): agent_id
    for agent_id, profile in AGENT_PROFILES.items()
}

# Agent roles
AGENT_ROLES = list(AGENT_PROFILES.keys())

# Get agent by role
def get_agent_by_role(role: str) -> Dict[str, Any]:
    """Get agent profile by role"""
    return AGENT_PROFILES.get(role, {})

# Get agent by ID
def get_agent_by_id(agent_id: str) -> Dict[str, Any]:
    """Get agent profile by agent_id"""
    for profile in AGENT_PROFILES.values():
        if profile.get('agent_id') == agent_id:
            return profile
    return {}

# Get agent specialties
def get_agent_specialties(agent_role: str) -> list:
    """Get specialties for an agent"""
    agent = AGENT_PROFILES.get(agent_role, {})
    return agent.get('specialties', [])

# Get preferred models for agent
def get_agent_models(agent_role: str) -> list:
    """Get preferred models for an agent"""
    agent = AGENT_PROFILES.get(agent_role, {})
    return agent.get('preferred_models', ['openai/gpt-4'])

# Get agent tools
def get_agent_tools(agent_role: str) -> list:
    """Get available tools for an agent"""
    agent = AGENT_PROFILES.get(agent_role, {})
    return agent.get('tools', [])