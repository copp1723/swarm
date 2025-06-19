"""
Configuration Loader
Centralized configuration management for the Email Agent system
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import logging
from utils.file_io import safe_read_json, safe_read_yaml

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for agent assignment"""
    agent_id: str
    name: str
    role: str
    capabilities: List[str]
    specialties: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        return cls(
            agent_id=data.get('agent_id', ''),
            name=data.get('name', ''),
            role=data.get('role', ''),
            capabilities=data.get('capabilities', []),
            specialties=data.get('specialties', [])
        )


class ConfigLoader:
    """Loads and manages configuration from multiple sources"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'config'
        )
        self._config_cache = {}
        self._agents_config = {}
        self._email_config = {}
        
        # Load configurations on init
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        # Load agents.json
        self._load_agents_config()
        
        # Load email_agent_config.yaml
        self._load_email_config()
        
        # Load environment overrides
        self._apply_env_overrides()
    
    def _load_agents_config(self):
        """Load agent profiles from agents.json"""
        agents_path = os.path.join(self.config_dir, 'agents.json')
        data = safe_read_json(agents_path, default_value={'AGENT_PROFILES': {}})
        self._agents_config = data.get('AGENT_PROFILES', {})
        logger.info(f"Loaded {len(self._agents_config)} agent profiles")
    
    def _load_email_config(self):
        """Load email agent configuration from YAML"""
        email_config_path = os.path.join(self.config_dir, 'email_agent_config.yaml')
        self._email_config = safe_read_yaml(email_config_path, default_value={})
        if self._email_config:
            logger.info("Loaded email agent configuration")
        else:
            logger.warning("Using default email agent configuration")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Override webhook timestamp max age
        if 'EMAIL_AGENT_MAX_TIMESTAMP_AGE' in os.environ:
            try:
                max_age = int(os.environ['EMAIL_AGENT_MAX_TIMESTAMP_AGE'])
                self._email_config.setdefault('integrations', {}).setdefault('webhooks', {}).setdefault('mailgun', {})['timestamp_max_age'] = max_age
            except ValueError:
                logger.warning("Invalid EMAIL_AGENT_MAX_TIMESTAMP_AGE value")
        
        # Override auto-dispatch setting
        if 'EMAIL_AGENT_AUTO_DISPATCH' in os.environ:
            auto_dispatch = os.environ['EMAIL_AGENT_AUTO_DISPATCH'].lower() == 'true'
            self._email_config.setdefault('features', {})['auto_dispatch'] = auto_dispatch
    
    def get_agent_profile(self, agent_role: str) -> Optional[Dict[str, Any]]:
        """Get agent profile by role"""
        return self._agents_config.get(agent_role)
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent profile by ID"""
        for role, profile in self._agents_config.items():
            if profile.get('agent_id') == agent_id:
                return profile
        return None
    
    def get_task_assignment(self, task_type: str) -> Dict[str, Any]:
        """Get agent assignment for a task type"""
        mapping = self._email_config.get('agent_assignment', {}).get('task_type_mapping', {})
        return mapping.get(task_type, mapping.get('general', {}))
    
    def get_priority_keywords(self, priority: str) -> List[str]:
        """Get keywords for priority detection"""
        return self._email_config.get('email_parsing', {}).get('priority_keywords', {}).get(priority, [])
    
    def get_task_type_keywords(self, task_type: str) -> List[str]:
        """Get keywords for task type detection"""
        return self._email_config.get('email_parsing', {}).get('task_type_keywords', {}).get(task_type, [])
    
    def get_notification_channels(self, priority: str) -> List[str]:
        """Get notification channels for a priority level"""
        return self._email_config.get('notifications', {}).get('channel_priority', {}).get(priority, ['email'])
    
    def get_feature_flag(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        features = self._email_config.get('features', {})
        if feature in features:
            return features[feature]
        
        # Check experimental features
        experimental = features.get('experimental', {})
        return experimental.get(feature, False)
    
    def get_retry_policy(self) -> Dict[str, Any]:
        """Get retry policy configuration"""
        return self._email_config.get('task_processing', {}).get('retry_policy', {
            'max_attempts': 3,
            'backoff_multiplier': 2,
            'initial_delay_seconds': 60
        })
    
    def get_supermemory_config(self) -> Dict[str, Any]:
        """Get Supermemory configuration"""
        return self._email_config.get('supermemory', {})
    
    def get_performance_setting(self, category: str, setting: str) -> Any:
        """Get performance configuration"""
        return self._email_config.get('performance', {}).get(category, {}).get(setting)
    
    def get_all_agent_ids(self) -> List[str]:
        """Get list of all agent IDs"""
        agent_ids = []
        for profile in self._agents_config.values():
            if 'agent_id' in profile:
                agent_ids.append(profile['agent_id'])
        return agent_ids
    
    def get_webhook_config(self, webhook_type: str) -> Dict[str, Any]:
        """Get webhook configuration"""
        return self._email_config.get('integrations', {}).get('webhooks', {}).get(webhook_type, {})
    
    def reload_configs(self):
        """Reload all configuration files"""
        logger.info("Reloading configurations...")
        self._config_cache.clear()
        self._load_all_configs()


# Singleton instance
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """Get or create the configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


# Convenience functions
def get_agent_assignment(task_type: str) -> Dict[str, Any]:
    """Get agent assignment for a task type"""
    return get_config_loader().get_task_assignment(task_type)


def get_agent_profile(agent_role: str) -> Optional[Dict[str, Any]]:
    """Get agent profile by role"""
    return get_config_loader().get_agent_profile(agent_role)


def get_feature_flag(feature: str) -> bool:
    """Check if a feature is enabled"""
    return get_config_loader().get_feature_flag(feature)


def get_retry_policy() -> Dict[str, Any]:
    """Get retry policy configuration"""
    return get_config_loader().get_retry_policy()