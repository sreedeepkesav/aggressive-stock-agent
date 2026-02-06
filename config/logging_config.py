"""Structured logging with file rotation."""

import logging
import logging.handlers
import os


def setup_logging(level: str = None) -> logging.Logger:
    """Configure application logging with console + rotating file output."""
    level = level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("stock_agent")
    if logger.handlers:
        return logger

    logger.setLevel(numeric_level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler (5 MB, 3 backups)
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "stock_agent.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
