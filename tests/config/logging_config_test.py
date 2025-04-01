import logging

logger = logging.getLogger(__name__)


def test_logging_config():
    logger.info("\n")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
