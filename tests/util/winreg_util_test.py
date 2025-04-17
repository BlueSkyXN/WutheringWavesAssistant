import logging

from src.util import winreg_util

logger = logging.getLogger(__name__)


def test_get_install_path():
    logger.debug("\n")
    path = winreg_util.get_install_path()
    logger.debug(path)
