"""
Unified Logging Setup
Provides a simple, consistent logging configuration across all modules
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
import json


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
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
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(
    name: Optional[str] = None,
    level: Union[str, int] = 'INFO',
    log_file: Optional[str] = None,
    console: bool = True,
    format_string: Optional[str] = None,
    use_colors: bool = True,
    use_json: bool = False,
    propagate: bool = True
) -> logging.Logger:
    """
    Set up a logger with consistent configuration.
    
    Args:
        name: Logger name (use __name__ in modules)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        console: Whether to log to console
        format_string: Custom format string
        use_colors: Use colored output for console
        use_json: Use JSON formatting
        propagate: Whether to propagate to parent logger
    
    Returns:
        Configured logger instance
    
    Usage:
        # In a module
        logger = setup_logging(__name__)
        
        # For application root
        logger = setup_logging('myapp', level='DEBUG', log_file='app.log')
        
        # With custom format
        logger = setup_logging(
            __name__,
            format_string='%(asctime)s - %(name)s - %(message)s'
        )
    """
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, str(level).upper() if isinstance(level, str) else level))
    logger.propagate = propagate
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Default format
    if not format_string:
        if use_json:
            formatter: Union[StructuredFormatter, logging.Formatter] = StructuredFormatter()
        else:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            formatter = ColoredFormatter(format_string) if use_colors and console else logging.Formatter(format_string)
    else:
        formatter = logging.Formatter(format_string)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        if use_json:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(
                ColoredFormatter(format_string) if use_colors else formatter
            )
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            StructuredFormatter() if use_json else formatter
        )
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Get a logger with the standard configuration.
    
    This is a convenience function that wraps setup_logging.
    
    Args:
        name: Logger name (typically __name__)
        **kwargs: Additional arguments for setup_logging
    
    Returns:
        Configured logger
    
    Usage:
        logger = get_logger(__name__)
    """
    return setup_logging(name, **kwargs)


class LogContext:
    """
    Context manager for adding contextual information to logs.
    
    Usage:
        logger = get_logger(__name__)
        
        with LogContext(logger, user_id=123, request_id='abc'):
            logger.info("Processing request")  # Will include user_id and request_id
    """
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def log_function_call(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG):
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        logger: Logger instance (will create one if not provided)
        level: Logging level for the messages
    
    Usage:
        @log_function_call()
        def calculate(x, y):
            return x + y
        
        # Or with specific logger
        logger = get_logger(__name__)
        
        @log_function_call(logger=logger, level=logging.INFO)
        def process_data(data):
            return transform(data)
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        def wrapper(*args, **kwargs):
            # Log function call
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.log(level, f"Calling {func.__name__}({signature})")
            
            try:
                # Call function
                result = func(*args, **kwargs)
                
                # Log result
                logger.log(level, f"{func.__name__} returned {result!r}")
                return result
            except Exception as e:
                # Log exception
                logger.exception(f"{func.__name__} raised {e.__class__.__name__}: {e}")
                raise
        
        return wrapper
    return decorator


def log_execution_time(logger: Optional[logging.Logger] = None, level: int = logging.INFO):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance
        level: Logging level
    
    Usage:
        @log_execution_time()
        def slow_function():
            time.sleep(1)
    """
    import time
    
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(level, f"{func.__name__} took {elapsed:.3f}s")
                return result
            except Exception:
                elapsed = time.time() - start_time
                logger.log(level, f"{func.__name__} failed after {elapsed:.3f}s")
                raise
        
        return wrapper
    return decorator


# Application-specific logging setup
def setup_app_logging(
    app_name: str = 'mcp_executive',
    log_dir: str = 'logs',
    debug: bool = False
) -> Dict[str, logging.Logger]:
    """
    Set up logging for the entire application with multiple loggers.
    
    Args:
        app_name: Application name
        log_dir: Directory for log files
        debug: Enable debug logging
    
    Returns:
        Dictionary of configured loggers
    
    Usage:
        loggers = setup_app_logging('myapp', debug=True)
        app_logger = loggers['app']
        db_logger = loggers['database']
    """
    level = 'DEBUG' if debug else 'INFO'
    
    # Create log directory
    Path(log_dir).mkdir(exist_ok=True)
    
    loggers = {}
    
    # Main application logger
    loggers['app'] = setup_logging(
        app_name,
        level=level,
        log_file=f"{log_dir}/{app_name}.log",
        use_json=not debug  # JSON in production, readable in debug
    )
    
    # Database logger
    loggers['database'] = setup_logging(
        f"{app_name}.database",
        level='WARNING' if not debug else 'DEBUG',
        log_file=f"{log_dir}/{app_name}_db.log"
    )
    
    # API logger
    loggers['api'] = setup_logging(
        f"{app_name}.api",
        level=level,
        log_file=f"{log_dir}/{app_name}_api.log"
    )
    
    # Error logger (errors only)
    error_logger = setup_logging(
        f"{app_name}.errors",
        level='ERROR',
        log_file=f"{log_dir}/{app_name}_errors.log",
        console=False  # Don't duplicate errors to console
    )
    loggers['errors'] = error_logger
    
    # Performance logger
    loggers['performance'] = setup_logging(
        f"{app_name}.performance",
        level='INFO',
        log_file=f"{log_dir}/{app_name}_performance.log",
        console=False
    )
    
    return loggers


# Convenience function for quick module setup
def module_logger(name: str) -> logging.Logger:
    """
    Quick setup for module-level logging.
    
    Usage:
        # At the top of a module
        logger = module_logger(__name__)
        
        def my_function():
            logger.info("Doing something")
    """
    return setup_logging(
        name,
        level='INFO',
        format_string='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )