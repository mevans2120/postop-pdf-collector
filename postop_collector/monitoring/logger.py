"""Advanced logging configuration with multiple handlers and formatters."""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "collection_run_id"):
            log_data["collection_run_id"] = record.collection_run_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class ErrorFileHandler(logging.handlers.RotatingFileHandler):
    """Custom file handler that only logs errors and above."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLevel(logging.ERROR)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "standard",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_syslog: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """Setup comprehensive logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        log_format: Format type (standard, json, colored)
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_syslog: Enable syslog logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Standard format
    standard_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        if log_format == "colored" and sys.stdout.isatty():
            console_handler.setFormatter(ColoredFormatter(standard_format))
        elif log_format == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(standard_format))
        
        root_logger.addHandler(console_handler)
    
    # File handler
    if enable_file and log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Main log file (all levels)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        if log_format == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(standard_format))
        
        root_logger.addHandler(file_handler)
        
        # Error log file (errors only)
        error_log_file = log_path.parent / f"{log_path.stem}_errors{log_path.suffix}"
        error_handler = ErrorFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_handler.setFormatter(logging.Formatter(standard_format))
        root_logger.addHandler(error_handler)
    
    # Syslog handler (for production)
    if enable_syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(
                address=('localhost', 514)
            )
            syslog_handler.setLevel(logging.WARNING)
            syslog_handler.setFormatter(
                logging.Formatter('postop-collector: %(levelname)s - %(message)s')
            )
            root_logger.addHandler(syslog_handler)
        except Exception as e:
            root_logger.warning(f"Failed to setup syslog handler: {e}")
    
    # Configure specific loggers
    configure_module_loggers(log_level)
    
    root_logger.info(
        f"Logging configured - Level: {log_level}, "
        f"Format: {log_format}, "
        f"Handlers: console={enable_console}, file={enable_file}, syslog={enable_syslog}"
    )


def configure_module_loggers(log_level: str) -> None:
    """Configure logging levels for specific modules."""
    # Reduce verbosity of third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    # Set specific levels for our modules
    logging.getLogger("postop_collector.core").setLevel(log_level)
    logging.getLogger("postop_collector.api").setLevel(log_level)
    logging.getLogger("postop_collector.analysis").setLevel(log_level)
    logging.getLogger("postop_collector.storage").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding context to logs."""
    
    def __init__(self, **kwargs):
        """Initialize with context values."""
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and add values to log records."""
        self.old_factory = logging.getLogRecordFactory()
        context = self.context
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory."""
        logging.setLogRecordFactory(self.old_factory)


def log_performance(func):
    """Decorator to log function performance."""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(
                f"{func.__name__} completed in {duration:.3f}s",
                extra={"duration_ms": duration * 1000}
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{func.__name__} failed after {duration:.3f}s: {e}",
                extra={"duration_ms": duration * 1000}
            )
            raise
    
    return wrapper