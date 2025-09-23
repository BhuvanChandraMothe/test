"""
Centralized logging configuration for SAP OData Connector
Automatically logs to both console and files for all operations
"""

import logging
import structlog
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Global flag to ensure logging is configured only once
_logging_configured = False

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
    
    # Console handler - always present
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # File handler - if enabled
    if log_to_file and log_file_path:
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG level in files
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
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
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add console renderer for terminal output
    if sys.stdout.isatty():
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    
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
