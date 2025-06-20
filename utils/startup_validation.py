"""
Startup validation utilities
Validates configuration and environment before application starts
"""
import os
import sys
import logging
from typing import List, Tuple, Dict, Any
from utils.config_validator import (
    check_required_env_variables,
    validate_api_credentials,
    load_and_validate_config,
    ConfigValidationError
)
from utils.file_io import file_exists

logger = logging.getLogger(__name__)


class StartupValidator:
    """Handles all startup validation checks"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all critical validations pass, False otherwise
        """
        logger.info("Starting application validation...")
        
        # Check required environment variables
        self._check_environment()
        
        # Validate API credentials
        self._validate_credentials()
        
        # Check required directories
        self._check_directories()
        
        # Validate configuration files
        self._validate_configs()
        
        # Check database connectivity
        self._check_database()
        
        # Check Redis connectivity
        self._check_redis()
        
        # Report results
        self._report_results()
        
        return len(self.errors) == 0
    
    def _check_environment(self):
        """Check required environment variables"""
        required_vars = [
            'FLASK_ENV',
            'DATABASE_URL',
            'REDIS_URL',
            'OPENROUTER_API_KEY',
            'SECRET_KEY'
        ]
        
        # Additional optional vars for production (warnings only)
        optional_production_vars = [
            'SENTRY_DSN',
            'MAILGUN_API_KEY',
            'MAILGUN_DOMAIN'
        ]
        
        # Check optional production vars separately
        if os.getenv('FLASK_ENV') == 'production':
            for var in optional_production_vars:
                if not os.getenv(var):
                    self.warnings.append(f"Optional production environment variable not set: {var}")
        
        all_present, missing = check_required_env_variables(required_vars)
        
        if not all_present:
            for var in missing:
                self.errors.append(f"Missing required environment variable: {var}")
    
    def _validate_credentials(self):
        """Validate API credentials format"""
        credentials = {
            'openai_api_key': os.getenv('OPENROUTER_API_KEY', ''),
            'database_url': os.getenv('DATABASE_URL', ''),
            'redis_url': os.getenv('REDIS_URL', ''),
            'webhook_secret': os.getenv('WEBHOOK_SECRET', '')
        }
        
        if os.getenv('FLASK_ENV') == 'production':
            credentials.update({
                'smtp_host': os.getenv('SMTP_HOST', ''),
                'smtp_port': os.getenv('SMTP_PORT', ''),
                'smtp_username': os.getenv('SMTP_USERNAME', ''),
                'smtp_password': os.getenv('SMTP_PASSWORD', '')
            })
        
        valid, status = validate_api_credentials(credentials)
        
        for service, status_msg in status.items():
            if status_msg != 'valid':
                if service in ['openai', 'database', 'redis']:
                    self.errors.append(f"{service} configuration invalid: {status_msg}")
                else:
                    self.warnings.append(f"{service} configuration warning: {status_msg}")
    
    def _check_directories(self):
        """Check required directories exist"""
        required_dirs = [
            'logs',
            'config',
            'static',
            'templates'
        ]
        
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                try:
                    os.makedirs(dir_name, exist_ok=True)
                    self.warnings.append(f"Created missing directory: {dir_name}")
                except Exception as e:
                    self.errors.append(f"Failed to create directory {dir_name}: {e}")
    
    def _validate_configs(self):
        """Validate configuration files against schemas"""
        config_validations = [
            ('config/agents.json', 'config/schemas/agents_schema.json', []),
            ('config/models.json', 'config/schemas/models_schema.json', []),
            ('config/email_agent_config.yaml', 'config/schemas/email_config_schema.json', [])
        ]
        
        for config_file, schema_file, required_env_vars in config_validations:
            if file_exists(config_file) and file_exists(schema_file):
                try:
                    load_and_validate_config(
                        config_file,
                        schema_file,
                        required_env_vars
                    )
                    logger.info(f"Successfully validated {config_file}")
                except ConfigValidationError as e:
                    self.warnings.append(f"Config validation warning for {config_file}: {e}")
                    if e.errors:
                        for error in e.errors:
                            self.warnings.append(f"  - {error}")
            else:
                if not file_exists(config_file):
                    self.warnings.append(f"Configuration file not found: {config_file}")
                if not file_exists(schema_file):
                    self.warnings.append(f"Schema file not found: {schema_file}")
    
    def _check_database(self):
        """Check database connectivity"""
        try:
            from sqlalchemy import create_engine, text
            db_url = os.getenv('DATABASE_URL')
            if db_url:
                engine = create_engine(db_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Database connectivity check passed")
            else:
                self.errors.append("DATABASE_URL not configured")
        except Exception as e:
            self.errors.append(f"Database connection failed: {e}")
    
    def _check_redis(self):
        """Check Redis connectivity"""
        try:
            import redis
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                r = redis.from_url(redis_url)
                r.ping()
                logger.info("Redis connectivity check passed")
            else:
                if os.getenv('FLASK_ENV') == 'production':
                    self.warnings.append("REDIS_URL not configured - some features may be limited")
                else:
                    self.errors.append("REDIS_URL not configured")
        except Exception as e:
            if os.getenv('FLASK_ENV') == 'production':
                self.warnings.append(f"Redis connection failed: {e} - falling back to in-memory cache")
            else:
                self.errors.append(f"Redis connection failed: {e}")
    
    def _report_results(self):
        """Report validation results"""
        if self.errors:
            logger.error("=== STARTUP VALIDATION ERRORS ===")
            for error in self.errors:
                logger.error(f"❌ {error}")
                
        if self.warnings:
            logger.warning("=== STARTUP VALIDATION WARNINGS ===")
            for warning in self.warnings:
                logger.warning(f"⚠️  {warning}")
                
        if not self.errors and not self.warnings:
            logger.info("✅ All startup validations passed!")


def validate_startup(exit_on_error: bool = True) -> bool:
    """
    Run startup validation.
    
    Args:
        exit_on_error: Whether to exit the process on validation errors
        
    Returns:
        True if validation passes, False otherwise
    """
    validator = StartupValidator()
    valid = validator.validate_all()
    
    if not valid and exit_on_error:
        logger.error("Application startup aborted due to validation errors")
        sys.exit(1)
        
    return valid


# Optional: Create a Click command for validation
def create_validation_command():
    """Create a Click command for running validation standalone"""
    try:
        import click
        
        @click.command()
        @click.option('--exit-on-error/--no-exit-on-error', default=False,
                      help='Exit with error code if validation fails')
        def validate(exit_on_error):
            """Validate application configuration and environment"""
            valid = validate_startup(exit_on_error)
            if valid:
                click.echo("✅ All validations passed!")
            else:
                click.echo("❌ Validation failed! Check logs for details.")
                if exit_on_error:
                    sys.exit(1)
                    
        return validate
    except ImportError:
        # Click not available
        return None