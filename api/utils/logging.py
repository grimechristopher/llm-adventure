"""
Logging configuration for LLM Adventure API

Dual output logging: detailed JSON to file, clean messages to console.
"""

import json
import logging
import sys
import os
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for detailed file logging"""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add ALL extra fields from record.__dict__
        # Skip internal logging fields that start with specific prefixes
        excluded_keys = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName',
            'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info', 'taskName'
        }

        for key, value in record.__dict__.items():
            if key not in excluded_keys:
                log_entry[key] = value

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Simple console formatter - message only for INFO/DEBUG, full for errors"""
    
    def format(self, record):
        if record.levelno >= logging.ERROR:
            # Full details for errors
            return f"ERROR [{record.name}:{record.funcName}:{record.lineno}] {record.getMessage()}"
        elif record.levelno >= logging.WARNING:
            # Moderate details for warnings
            return f"WARN [{record.name}] {record.getMessage()}"
        else:
            # Just the message for info/debug
            return record.getMessage()


def setup_logging(level=logging.INFO, log_file='logs/app.log'):
    """Setup dual logging configuration"""

    # Get the absolute path to the log file relative to the api directory
    # This ensures logs go in the correct location regardless of where the script is run from
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file = os.path.join(script_dir, log_file)

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters
    json_formatter = JSONFormatter()
    console_formatter = ConsoleFormatter()
    
    # Create file handler for detailed JSON logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.DEBUG)  # Capture everything to file
    
    # Create console handler for clean output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('hypercorn').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name):
    """Get a logger with the given name"""
    return EnhancedLogger(logging.getLogger(name))


class EnhancedLogger:
    """Enhanced logger wrapper with convenience methods"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def info(self, message, **kwargs):
        """Log info message with optional extra fields"""
        self.logger.info(message, extra=kwargs)
        
    def error(self, message, error=None, **kwargs):
        """Log error message with automatic error handling"""
        if error:
            kwargs.update({
                'error': str(error),
                'error_type': type(error).__name__
            })
        self.logger.error(message, extra=kwargs)
        
    def warning(self, message, **kwargs):
        """Log warning message with optional extra fields"""
        self.logger.warning(message, extra=kwargs)
        
    def debug(self, message, **kwargs):
        """Log debug message with optional extra fields"""
        self.logger.debug(message, extra=kwargs)
        
    def exception(self, message, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, extra=kwargs)