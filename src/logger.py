import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(log_dir: Path, log_level: str = "INFO") -> logging.Logger:
    """
    Setup dual logger (console + file) with different formats.

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("crm_helper")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers (if any)
    logger.handlers.clear()

    # Console Handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File Handler (detailed format)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"crm_automation_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s,%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Log the log file location
    logger.info(f"Log file created: {log_file}")

    return logger
