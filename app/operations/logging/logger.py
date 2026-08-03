import logging
import socket
import sys

from app.operations.logging.formatter import JSONFormatter


def setup_logger(name: str = "app") -> logging.Logger:
    """
    Setup structured JSON logger for the application.
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        hostname = socket.gethostname()
        formatter = JSONFormatter(hostname=hostname)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


# Create a default structured logger
structured_logger = setup_logger("ai_marketing_suite.operations")
