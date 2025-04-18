import logging

from src.util import windows_util

logger = logging.getLogger(__name__)


def test_show_windows_notification():
    logger.debug("\n")
    windows_util.show_windows_notification("这是一条测试消息")
