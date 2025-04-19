import logging
import os

from src.core import environs

environs.load_env()

from src.config import logging_config

logging_config.setup_logging()

from src import application

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("https://github.com/wakening/WutheringWavesAssistant")
    logger.debug(os.environ)
    application.run()
    logger.info("https://github.com/wakening/WutheringWavesAssistant")
    logger.info("结束")
