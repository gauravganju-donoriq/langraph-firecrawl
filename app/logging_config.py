"""
Logging configuration for the regulatory extraction pipeline.
"""

import logging
import sys

# Flag to prevent multiple setup calls
_logging_configured = False


def setup_logging(level: str = "DEBUG") -> None:
    """
    Configure logging for the application.
    Only runs once to prevent duplicate handlers.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    global _logging_configured
    
    # Prevent duplicate setup
    if _logging_configured:
        return
    
    _logging_configured = True
    
    # Create formatter with detailed output
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger - clear existing handlers first
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
