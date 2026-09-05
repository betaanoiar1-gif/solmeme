"""
Logging configuration for Meme Alpha Hunter.
Provides clean console output and persistent file logs.
"""

import logging
import os
import sys
from datetime import datetime


def setup_logger(name: str = "meme_alpha_hunter", log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_to_file:
        os.makedirs("logs", exist_ok=True)
        log_file = os.path.join("logs", f"meme_hunter_{datetime.utcnow().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG in files
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
