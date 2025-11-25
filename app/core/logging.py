"""Logging setup"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def setup_logging(log_dir: str = "storage/logs", log_file: str = "app.log") -> None:
    """
    Configures application logging using Loguru.

    This sets up two sinks:
    1. Console output with colorized formatting.
    2. File-based logging with rotation, retention, and compression.

    Args:
        log_dir (str): Directory where log files will be stored. Defaults to "logs".
        log_file (str): Log file name. Defaults to "app.log".

    Returns:
        None
    """
    log_path: Path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()  # Remove any previously configured handlers

    # Console logging
    logger.add(
        sys.stdout,
        level="INFO" if not settings.debug else "DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # File logging with rotation and retention
    logger.add(
        log_path / log_file,
        level="INFO",
        rotation="10 MB",  # Rotate log file after it reaches 10MB
        retention="10 days",  # Keep log files for 10 days
        compression="zip",  # Compress rotated logs
        format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
