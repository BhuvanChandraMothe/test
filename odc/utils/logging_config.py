"""
Centralized logging configuration for SAP OData Connector
Provides clean, structured logging with proper filtering and formatting
Includes colored output for better visibility and debugging
"""

import logging
import logging.handlers
import structlog
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Global flag to ensure logging is configured only once
_logging_configured = False

# Define which loggers should be at which levels to reduce noise
LOGGER_LEVELS = {
    # Our application loggers - keep detailed
    'odc': logging.INFO,
    'odc.connector': logging.INFO,
    'odc.services': logging.INFO,
    'odc.workers': logging.INFO,
    'odc.planning': logging.INFO,
    'odc.storage': logging.INFO,
    
    # Third-party loggers - reduce noise
    'httpx': logging.WARNING,
    'httpcore': logging.WARNING,
    'urllib3': logging.WARNING,
    'requests': logging.WARNING,
    'asyncio': logging.WARNING,
    'pyodata': logging.WARNING,
    
    # Root logger
    '': logging.INFO
}

class ColoredFormatter(logging.Formatter):
    """
    Custom formatter with colors for different log levels
    """
    
    # Color scheme for different log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }
    
    # Special colors for specific message types
    SPECIAL_COLORS = {
        'PHASE': Fore.BLUE + Style.BRIGHT,
        'SUCCESS': Fore.GREEN + Style.BRIGHT,
        'STATS': Fore.CYAN + Style.BRIGHT,
        'FAILURE': Fore.RED + Style.BRIGHT,
        'CONFIG': Fore.MAGENTA,
    }
    
    def format(self, record):
        # Get the base formatted message
        log_message = super().format(record)
        
        # Apply color based on log level
        level_color = self.COLORS.get(record.levelname, '')
        
        # Check for special message types
        message = record.getMessage()
        
        if any(keyword in message for keyword in ['Phase ', 'Step ']):
            # Phase/Step messages in bright blue
            return f"{self.SPECIAL_COLORS['PHASE']}{log_message}{Style.RESET_ALL}"
        elif any(keyword in message for keyword in ['✓', 'SUCCESS', 'Complete', 'successful']):
            # Success messages in bright green
            return f"{self.SPECIAL_COLORS['SUCCESS']}{log_message}{Style.RESET_ALL}"
        elif any(keyword in message for keyword in ['Statistics:', 'Duration:', 'records:', 'Rate:']):
            # Statistics in bright cyan
            return f"{self.SPECIAL_COLORS['STATS']}{log_message}{Style.RESET_ALL}"
        elif any(keyword in message for keyword in ['FAILED', 'ERROR', 'Invalid', 'Authentication failed']):
            # Failures in bright red
            return f"{self.SPECIAL_COLORS['FAILURE']}{log_message}{Style.RESET_ALL}"
        elif any(keyword in message for keyword in ['Configuration', 'Config']):
            # Configuration in magenta
            return f"{self.SPECIAL_COLORS['CONFIG']}{log_message}{Style.RESET_ALL}"
        else:
            # Regular level-based coloring
            return f"{level_color}{log_message}{Style.RESET_ALL}"


def _clean_key_value_processor(logger, method_name, event_dict):
    """
    Custom structlog processor to format key-value pairs in a clean, readable way
    
    This is the magic of structlog - it allows us to add structured data to logs
    and format it consistently across the application.
    """
    # Extract the main message
    message = event_dict.pop('event', '')
    
    # Format key-value pairs cleanly
    kv_pairs = []
    for key, value in event_dict.items():
        if key not in ['timestamp', 'level', 'logger']:
            # Format different types appropriately
            if isinstance(value, (int, float)):
                kv_pairs.append(f"{key}={value}")
            elif isinstance(value, bool):
                kv_pairs.append(f"{key}={str(value).lower()}")
            elif isinstance(value, str) and ' ' in value:
                kv_pairs.append(f'{key}="{value}"')
            else:
                kv_pairs.append(f"{key}={value}")
    
    # Combine message with key-value pairs
    if kv_pairs:
        formatted_message = f"{message} [{', '.join(kv_pairs)}]"
    else:
        formatted_message = message
    
    # Return the cleaned event dict
    return {'event': formatted_message}

def setup_connector_logging(log_level: str = "INFO", log_to_file: bool = True) -> Optional[str]:
    """
    Setup comprehensive logging for the SAP OData Connector
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to files (default: True)
    
    Returns:
        Path to log file if file logging is enabled, None otherwise
    """
    global _logging_configured
    
    if _logging_configured:
        return None
    
    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file_path = None
    
    if log_to_file:
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = log_dir / f"sap_odata_connector_{timestamp}.log"
    
    # Configure handlers
    handlers = []
    
    # Console handler - colored format for terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # File handler - if enabled, with rotation
    if log_to_file and log_file_path:
        # Use rotating file handler to prevent huge files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, 
            maxBytes=10*1024*1024,  # 10MB max file size
            backupCount=5,          # Keep 5 backup files
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)  # Only INFO and above in files
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)-25s - %(levelname)-8s - %(funcName)-20s:%(lineno)-4d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Set specific logger levels to reduce noise
    for logger_name, level in LOGGER_LEVELS.items():
        logging.getLogger(logger_name).setLevel(level)
    
    # Configure structlog with clean, readable output
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Custom processor to format key-value pairs cleanly
        _clean_key_value_processor,
        # Use stdlib renderer to integrate with standard logging
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    _logging_configured = True
    
    # Log the configuration
    logger = structlog.get_logger("logging_config")
    logger.info("SAP OData Connector logging configured",
                log_level=log_level,
                log_to_file=log_to_file,
                log_file=str(log_file_path) if log_file_path else None)
    
    return str(log_file_path) if log_file_path else None

def get_logger(name: str):
    """Get a configured logger instance"""
    # Ensure logging is configured
    setup_connector_logging()
    return structlog.get_logger(name)

def reset_logging_config():
    """Reset logging configuration (for testing purposes)"""
    global _logging_configured
    _logging_configured = False
