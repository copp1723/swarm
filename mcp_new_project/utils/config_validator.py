"""Configuration validation utilities"""
import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Make jsonschema optional
try:
    from jsonschema import validate, ValidationError as JsonSchemaValidationError, Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    JsonSchemaValidationError = Exception  # Fallback
    
import requests
from utils.file_io import safe_read_json, safe_read_yaml

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []


def validate_config_schema(config: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    """
    Validate configuration against a JSON schema.
    
    Args:
        config: Configuration dictionary to validate
        schema: JSON schema dictionary
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    if not HAS_JSONSCHEMA:
        return True, ["Warning: jsonschema not installed, skipping validation"]
        
    errors = []
    
    try:
        # Create validator instance for better error messages
        validator = Draft7Validator(schema)
        
        # Validate and collect all errors
        validation_errors = sorted(validator.iter_errors(config), key=lambda e: e.path)
        
        if validation_errors:
            for error in validation_errors:
                # Build path to the error
                path = '.'.join(str(x) for x in error.path) if error.path else 'root'
                
                # Format error message
                if error.validator == 'required':
                    errors.append(f"Missing required field: {error.validator_value[0]}")
                elif error.validator == 'type':
                    errors.append(
                        f"Invalid type at '{path}': expected {error.validator_value}, "
                        f"got {type(error.instance).__name__}"
                    )
                elif error.validator == 'enum':
                    errors.append(
                        f"Invalid value at '{path}': must be one of {error.validator_value}"
                    )
                elif error.validator == 'minLength':
                    errors.append(
                        f"Value at '{path}' too short: minimum length is {error.validator_value}"
                    )
                elif error.validator == 'pattern':
                    errors.append(
                        f"Value at '{path}' doesn't match required pattern: {error.validator_value}"
                    )
                else:
                    errors.append(f"Validation error at '{path}': {error.message}")
            
            return False, errors
        
        return True, []
        
    except JsonSchemaValidationError as e:
        errors.append(f"Schema validation error: {str(e)}")
        return False, errors
    except Exception as e:
        errors.append(f"Unexpected error during validation: {str(e)}")
        return False, errors


def check_required_env_variables(required_vars: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if all required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        Tuple of (all_present, missing_vars)
    """
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value is None or value.strip() == '':
            missing_vars.append(var)
            
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        
    return len(missing_vars) == 0, missing_vars


def validate_api_credentials(credentials: Dict) -> Tuple[bool, Dict[str, str]]:
    """
    Validate API credentials format and basic connectivity.
    
    Args:
        credentials: Dictionary of service credentials
        
    Returns:
        Tuple of (is_valid, service_status_dict)
    """
    service_status = {}
    all_valid = True
    
    # Validate OpenAI credentials
    if 'openai_api_key' in credentials:
        status = _validate_openai_key(credentials['openai_api_key'])
        service_status['openai'] = status
        if status != 'valid':
            all_valid = False
            
    # Validate database URL
    if 'database_url' in credentials:
        status = _validate_database_url(credentials['database_url'])
        service_status['database'] = status
        if status != 'valid':
            all_valid = False
            
    # Validate Redis URL
    if 'redis_url' in credentials:
        status = _validate_redis_url(credentials['redis_url'])
        service_status['redis'] = status
        if status != 'valid':
            all_valid = False
            
    # Validate webhook secrets
    if 'webhook_secret' in credentials:
        status = _validate_webhook_secret(credentials['webhook_secret'])
        service_status['webhook'] = status
        if status != 'valid':
            all_valid = False
            
    # Validate SMTP settings
    if 'smtp_host' in credentials:
        smtp_creds = {
            'host': credentials.get('smtp_host'),
            'port': credentials.get('smtp_port'),
            'username': credentials.get('smtp_username'),
            'password': credentials.get('smtp_password')
        }
        status = _validate_smtp_settings(smtp_creds)
        service_status['smtp'] = status
        if status != 'valid':
            all_valid = False
            
    return all_valid, service_status


def load_and_validate_config(
    config_path: str,
    schema_path: str,
    required_env_vars: List[str] = None
) -> Dict:
    """
    Load configuration file and validate against schema.
    
    Args:
        config_path: Path to configuration file (JSON or YAML)
        schema_path: Path to JSON schema file
        required_env_vars: List of required environment variables
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ConfigValidationError if validation fails
    """
    # Determine file type and load config
    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        raise ConfigValidationError(f"Configuration file not found: {config_path}")
        
    if config_path_obj.suffix in ['.yaml', '.yml']:
        config = safe_read_yaml(config_path)
    elif config_path_obj.suffix == '.json':
        config = safe_read_json(config_path)
    else:
        raise ConfigValidationError(
            f"Unsupported configuration file type: {config_path_obj.suffix}"
        )
        
    if config is None:
        raise ConfigValidationError(f"Failed to load configuration from {config_path}")
        
    # Load schema
    schema = safe_read_json(schema_path)
    if schema is None:
        raise ConfigValidationError(f"Failed to load schema from {schema_path}")
        
    # Validate against schema
    is_valid, errors = validate_config_schema(config, schema)
    if not is_valid:
        raise ConfigValidationError(
            f"Configuration validation failed for {config_path}",
            errors
        )
        
    # Check environment variables if required
    if required_env_vars:
        env_valid, missing_vars = check_required_env_variables(required_env_vars)
        if not env_valid:
            raise ConfigValidationError(
                "Missing required environment variables",
                [f"Environment variable '{var}' is not set" for var in missing_vars]
            )
            
    # Substitute environment variables in config
    config = _substitute_env_vars(config)
    
    logger.info(f"Successfully loaded and validated configuration from {config_path}")
    return config


def validate_config_value(
    value: Any,
    value_type: str,
    constraints: Dict = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a single configuration value against type and constraints.
    
    Args:
        value: Value to validate
        value_type: Expected type ('string', 'integer', 'number', 'boolean', 'array', 'object')
        constraints: Optional constraints (min, max, pattern, etc.)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Type validation
    type_map = {
        'string': str,
        'integer': int,
        'number': (int, float),
        'boolean': bool,
        'array': list,
        'object': dict
    }
    
    expected_type = type_map.get(value_type)
    if expected_type is None:
        return False, f"Unknown type: {value_type}"
        
    if not isinstance(value, expected_type):
        return False, f"Expected {value_type}, got {type(value).__name__}"
        
    # Apply constraints if provided
    if constraints:
        # String constraints
        if value_type == 'string':
            if 'minLength' in constraints and len(value) < constraints['minLength']:
                return False, f"String too short (minimum: {constraints['minLength']})"
            if 'maxLength' in constraints and len(value) > constraints['maxLength']:
                return False, f"String too long (maximum: {constraints['maxLength']})"
            if 'pattern' in constraints:
                import re
                if not re.match(constraints['pattern'], value):
                    return False, f"String doesn't match pattern: {constraints['pattern']}"
                    
        # Number constraints
        elif value_type in ['integer', 'number']:
            if 'minimum' in constraints and value < constraints['minimum']:
                return False, f"Value below minimum: {constraints['minimum']}"
            if 'maximum' in constraints and value > constraints['maximum']:
                return False, f"Value above maximum: {constraints['maximum']}"
                
        # Array constraints
        elif value_type == 'array':
            if 'minItems' in constraints and len(value) < constraints['minItems']:
                return False, f"Array too small (minimum items: {constraints['minItems']})"
            if 'maxItems' in constraints and len(value) > constraints['maxItems']:
                return False, f"Array too large (maximum items: {constraints['maxItems']})"
                
    return True, None


def create_default_config(schema: Dict, include_descriptions: bool = True) -> Dict:
    """
    Create a default configuration based on a JSON schema.
    
    Args:
        schema: JSON schema dictionary
        include_descriptions: Whether to include descriptions as comments
        
    Returns:
        Default configuration dictionary
    """
    def get_default_value(prop_schema: Dict) -> Any:
        """Get default value for a property based on its schema."""
        if 'default' in prop_schema:
            return prop_schema['default']
            
        prop_type = prop_schema.get('type', 'string')
        if prop_type == 'string':
            return prop_schema.get('example', '')
        elif prop_type == 'integer':
            return 0
        elif prop_type == 'number':
            return 0.0
        elif prop_type == 'boolean':
            return False
        elif prop_type == 'array':
            return []
        elif prop_type == 'object':
            return {}
        else:
            return None
            
    config = {}
    
    # Process properties
    properties = schema.get('properties', {})
    for prop_name, prop_schema in properties.items():
        # Add description as comment if requested
        if include_descriptions and 'description' in prop_schema:
            config[f"_{prop_name}_description"] = prop_schema['description']
            
        # Get default value
        config[prop_name] = get_default_value(prop_schema)
        
        # Recursively handle nested objects
        if prop_schema.get('type') == 'object' and 'properties' in prop_schema:
            config[prop_name] = create_default_config(prop_schema, include_descriptions)
            
    return config


# Private helper functions

def _validate_openai_key(api_key: str) -> str:
    """Validate OpenAI API key format."""
    if not api_key or not api_key.startswith('sk-'):
        return 'invalid_format'
    if len(api_key) < 40:
        return 'too_short'
    return 'valid'


def _validate_database_url(db_url: str) -> str:
    """Validate database URL format."""
    if not db_url:
        return 'missing'
    
    valid_prefixes = ['postgresql://', 'postgres://', 'mysql://', 'sqlite:///']
    if not any(db_url.startswith(prefix) for prefix in valid_prefixes):
        return 'invalid_format'
        
    return 'valid'


def _validate_redis_url(redis_url: str) -> str:
    """Validate Redis URL format."""
    if not redis_url:
        return 'missing'
        
    if not redis_url.startswith(('redis://', 'rediss://')):
        return 'invalid_format'
        
    return 'valid'


def _validate_webhook_secret(secret: str) -> str:
    """Validate webhook secret strength."""
    if not secret:
        return 'missing'
    if len(secret) < 16:
        return 'too_weak'
    return 'valid'


def _validate_smtp_settings(smtp_config: Dict) -> str:
    """Validate SMTP configuration."""
    required_fields = ['host', 'port']
    for field in required_fields:
        if not smtp_config.get(field):
            return f'missing_{field}'
            
    # Validate port number
    try:
        port = int(smtp_config['port'])
        if port < 1 or port > 65535:
            return 'invalid_port'
    except (ValueError, TypeError):
        return 'invalid_port'
        
    return 'valid'


def _substitute_env_vars(config: Any) -> Any:
    """Recursively substitute environment variables in configuration."""
    if isinstance(config, dict):
        return {k: _substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Check for environment variable pattern ${VAR_NAME}
        if config.startswith('${') and config.endswith('}'):
            var_name = config[2:-1]
            return os.environ.get(var_name, config)
    return config