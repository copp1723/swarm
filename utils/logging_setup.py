"""
Centralized Logging Configuration
Eliminates duplicate logging setup across modules
"""
import os
import sys
import logging
import logging.handlers
from typing import Optional, Dict, Any
from datetime import datetime
import json


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        if not sys.stdout.isatty():
            return super().format(record)
            
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'message', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread', 'threadName',
                          'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
                
        return json.dumps(log_data)


class LoggerManager:
    """Centralized logger configuration manager"""
    
    _initialized = False
    _loggers: Dict[str, logging.Logger] = {}
    
    @classmethod
    def setup_logging(
        cls,
        log_level: Optional[str] = None,
        log_file: Optional[str] = None,
        log_format: Optional[str] = None,
        use_json: bool = False,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """Setup logging configuration once for the entire application"""
        if cls._initialized:
            return
            
        # Get configuration from environment or parameters
        log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
        log_file = log_file or os.getenv('LOG_FILE', 'logs/app.log')
        log_format = log_format or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create logs directory if needed
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        root_logger.handlers = []
        
        # Console handler with color support
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        if use_json:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter(log_format))
            
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            
            if use_json:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(log_format))
                
            root_logger.addHandler(file_handler)
        
        # Set specific log levels for noisy libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        
        cls._initialized = True
        
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger with the given name"""
        if not cls._initialized:
            cls.setup_logging()
            
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
            
        return cls._loggers[name]
    
    @classmethod
    def add_file_handler(
        cls,
        logger_name: str,
        log_file: str,
        level: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ):
        """Add a file handler to a specific logger"""
        logger = cls.get_logger(logger_name)
        
        # Create directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
        if level:
            handler.setLevel(getattr(logging, level.upper()))
            
        # Use same formatter as root logger
        if logger.handlers and logger.handlers[0].formatter:
            handler.setFormatter(logger.handlers[0].formatter)
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            
        logger.addHandler(handler)
        return handler


# Convenience functions
def setup_logging(**kwargs):
    """Setup logging for the application"""
    LoggerManager.setup_logging(**kwargs)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return LoggerManager.get_logger(name)


# Context manager for temporary log level changes
class log_level:
    """Context manager to temporarily change log level"""
    
    def __init__(self, logger: logging.Logger, level: str):
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.old_level = logger.level
        
    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)


# Decorators for logging
def log_execution(level: str = 'INFO'):
    """Decorator to log function execution"""
    def decorator(func):
        logger = get_logger(func.__module__)
        
        def wrapper(*args, **kwargs):
            logger.log(
                getattr(logging, level.upper()),
                f"Executing {func.__name__} with args={args}, kwargs={kwargs}"
            )
            try:
                result = func(*args, **kwargs)
                logger.log(
                    getattr(logging, level.upper()),
                    f"Completed {func.__name__} successfully"
                )
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise
                
        return wrapper
    return decorator


def log_errors(func):
    """Decorator to log function errors"""
    logger = get_logger(func.__module__)
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
            
    return wrapper