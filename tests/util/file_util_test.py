import logging

from src.util import file_util

logger = logging.getLogger(__name__)


def test_file_util():
    logger.debug("\n")
    logger.debug(file_util.get_project_root())
    logger.debug(file_util.get_scripts())
    logger.debug(file_util.get_temp())
    logger.debug(file_util.get_temp_screenshot())
    logger.debug(file_util.get_assets())
    logger.debug(file_util.get_assets_model())
    logger.debug(file_util.get_assets_screenshot())
    logger.debug(file_util.get_logs())

    logger.debug(file_util.get_log_file())
    logger.debug(file_util.get_test_log_file())

    logger.debug(file_util.create_img_path())
