"""
Centralized logging configuration for the Customer Success Swarm application.

Provides structured logging with consistent formatting, color-coded output,
and module-specific loggers.
"""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color-coded log levels for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Emoji icons for different log levels
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{self.BOLD}"
                f"{self.ICONS.get(levelname, '')} {levelname}{self.RESET}"
            )
        
        # Add color to module name
        record.name = f"{self.BOLD}{record.name}{self.RESET}"
        
        return super().format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Set format
    if format_string is None:
        format_string = (
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
    
    formatter = ColoredFormatter(
        format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for the specified module.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Logger instance
    """
    return setup_logger(name)


# Convenience function for logging separator lines
def log_separator(logger: logging.Logger, char: str = "=", length: int = 80):
    """Log a separator line for visual clarity."""
    logger.info(char * length)
