#!/usr/bin/env python3
"""
Centralized Environment Variable Validator

Validates required and optional environment variables at application boot.
Aborts with explicit logging if required variables are missing or empty.
Warns about optional variables only when related features are enabled.
"""

import os
import sys
import logging
from typing import List, Dict, Optional, Any

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variable schema
REQUIRED = [
    "OPENROUTER_API_KEY",
    "SECRET_KEY", 
    "DATABASE_URL"
]

OPTIONAL = [
    "MAILGUN_API_KEY",
    "MAILGUN_DOMAIN", 
    "MAILGUN_SIGNING_KEY"
]

# Feature flags that control when optional variables are needed
FEATURE_FLAGS = {
    'email_notifications': ['MAILGUN_API_KEY', 'MAILGUN_DOMAIN', 'MAILGUN_SIGNING_KEY'],
}


def validate_env(exit_on_error: bool = True) -> bool:
    """
    Validate environment variables according to the defined schema.
    
    Args:
        exit_on_error: Whether to exit the application on required variable errors
        
    Returns:
        bool: True if all required variables are present, False otherwise
        
    Raises:
        SystemExit: If exit_on_error is True and required variables are missing
    """
    logger.info("Starting environment variable validation...")
    
    validation_errors = []
    validation_warnings = []
    
    # Check required environment variables
    missing_required = []
    empty_required = []
    
    for var_name in REQUIRED:
        value = os.environ.get(var_name)
        if value is None:
            missing_required.append(var_name)
            validation_errors.append(f"REQUIRED variable '{var_name}' is not set")
        elif not value.strip():
            empty_required.append(var_name)
            validation_errors.append(f"REQUIRED variable '{var_name}' is empty")
        else:
            logger.info(f"✓ Required variable '{var_name}' is present and non-empty")
    
    # Check optional environment variables with feature detection
    missing_optional = []
    feature_warnings = []
    
    for var_name in OPTIONAL:
        value = os.environ.get(var_name)
        if value is None or not value.strip():
            missing_optional.append(var_name)
            validation_warnings.append(f"Optional variable '{var_name}' is not set")
        else:
            logger.info(f"✓ Optional variable '{var_name}' is present and non-empty")
    
    # Check if missing optional variables are needed for enabled features
    for feature, required_vars in FEATURE_FLAGS.items():
        feature_enabled = _is_feature_enabled(feature)
        if feature_enabled:
            missing_for_feature = [var for var in required_vars if var in missing_optional]
            if missing_for_feature:
                feature_warnings.append(
                    f"Feature '{feature}' is enabled but missing required variables: {missing_for_feature}"
                )
    
    # Log all validation results
    if validation_errors:
        logger.error("=" * 80)
        logger.error("ENVIRONMENT VALIDATION FAILED - MISSING REQUIRED VARIABLES")
        logger.error("=" * 80)
        for error in validation_errors:
            logger.error(f"❌ {error}")
        logger.error("=" * 80)
        logger.error("Application cannot start without required environment variables!")
        logger.error("Please set the following variables in your .env file or environment:")
        for var in missing_required + empty_required:
            logger.error(f"  - {var}")
        logger.error("=" * 80)
        
        if exit_on_error:
            logger.error("Exiting application due to missing required environment variables.")
            sys.exit(1)
        return False
    
    # Log warnings for optional variables
    if validation_warnings:
        logger.warning("=" * 80)
        logger.warning("ENVIRONMENT VALIDATION WARNINGS - OPTIONAL VARIABLES")
        logger.warning("=" * 80)
        for warning in validation_warnings:
            logger.warning(f"⚠️  {warning}")
        
        if feature_warnings:
            logger.warning("-" * 40)
            logger.warning("FEATURE-SPECIFIC WARNINGS:")
            for warning in feature_warnings:
                logger.warning(f"⚠️  {warning}")
        
        logger.warning("=" * 80)
        logger.warning("Application will continue but some features may be disabled.")
        logger.warning("=" * 80)
    
    # Success message
    logger.info("=" * 80) 
    logger.info("✅ ENVIRONMENT VALIDATION SUCCESSFUL")
    logger.info(f"✅ All {len(REQUIRED)} required variables are present and valid")
    
    optional_present = len(OPTIONAL) - len(missing_optional)
    logger.info(f"✅ {optional_present}/{len(OPTIONAL)} optional variables are present")
    logger.info("=" * 80)
    
    return True


def _is_feature_enabled(feature_name: str) -> bool:
    """
    Check if a specific feature is enabled based on environment variables or configuration.
    
    Args:
        feature_name: Name of the feature to check
        
    Returns:
        bool: True if the feature is enabled, False otherwise
    """
    # Map feature names to their enable flags
    feature_env_map = {
        'email_notifications': 'ENABLE_EMAIL_NOTIFICATIONS',
    }
    
    env_var = feature_env_map.get(feature_name)
    if env_var:
        # Check if explicitly enabled
        return os.environ.get(env_var, 'false').lower() in ('true', '1', 'yes', 'on')
    
    # For email notifications, also check if any Mailgun variables are set
    # This implies the user intends to use email features
    if feature_name == 'email_notifications':
        mailgun_vars = ['MAILGUN_API_KEY', 'MAILGUN_DOMAIN']
        return any(os.environ.get(var) for var in mailgun_vars)
    
    return False


def get_env_status() -> Dict[str, Any]:
    """
    Get the current status of environment variables for monitoring/debugging.
    
    Returns:
        Dict containing environment variable status information
    """
    status = {
        'required': {},
        'optional': {},
        'features': {},
        'validation_passed': True
    }
    
    # Check required variables
    for var_name in REQUIRED:
        value = os.environ.get(var_name)
        status['required'][var_name] = {
            'present': value is not None,
            'non_empty': value is not None and value.strip() != '',
            'valid': value is not None and value.strip() != ''
        }
        if not status['required'][var_name]['valid']:
            status['validation_passed'] = False
    
    # Check optional variables
    for var_name in OPTIONAL:
        value = os.environ.get(var_name)
        status['optional'][var_name] = {
            'present': value is not None,
            'non_empty': value is not None and value.strip() != '',
            'valid': value is not None and value.strip() != ''
        }
    
    # Check feature enablement
    for feature_name in FEATURE_FLAGS.keys():
        status['features'][feature_name] = {
            'enabled': _is_feature_enabled(feature_name),
            'requirements_met': all(
                status['optional'].get(var, {}).get('valid', False)
                for var in FEATURE_FLAGS[feature_name]
            )
        }
    
    return status


def validate_specific_vars(var_names: List[str]) -> bool:
    """
    Validate a specific set of environment variables.
    
    Args:
        var_names: List of variable names to validate
        
    Returns:
        bool: True if all specified variables are present and non-empty
    """
    all_valid = True
    
    for var_name in var_names:
        value = os.environ.get(var_name)
        if value is None or not value.strip():
            logger.error(f"Variable '{var_name}' is missing or empty")
            all_valid = False
        else:
            logger.info(f"Variable '{var_name}' is valid")
    
    return all_valid


if __name__ == "__main__":
    """
    Command-line interface for environment validation.
    
    Usage:
        python utils/env_check.py              # Validate all variables
        python utils/env_check.py --no-exit   # Don't exit on errors
        python utils/env_check.py --status    # Show status only
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate environment variables")
    parser.add_argument(
        '--no-exit', 
        action='store_true', 
        help="Don't exit on validation errors"
    )
    parser.add_argument(
        '--status', 
        action='store_true', 
        help="Show environment status and exit"
    )
    
    args = parser.parse_args()
    
    if args.status:
        import json
        status = get_env_status()
        print(json.dumps(status, indent=2))
        sys.exit(0)
    
    exit_on_error = not args.no_exit
    success = validate_env(exit_on_error=exit_on_error)
    
    if not success and not exit_on_error:
        sys.exit(1)

