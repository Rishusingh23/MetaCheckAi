import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configures centralized logging format and log levels for the application.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("metacheck")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
