import logging

from src.util import hwnd_util, img_util, mss_util

logger = logging.getLogger(__name__)


hwnd_util.enable_dpi_awareness()


def test_mss_util():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    hwnd_util.get_sys_dpi()
    hwnd_util.get_window_dpi(hwnd)
    hwnd_util.get_window_wh(hwnd)
    hwnd_util.get_client_wh(hwnd)

    client = mss_util.create_mss()
    region = hwnd_util.get_client_rect(hwnd)
    logger.debug(region)
    img = mss_util.screenshot(client, region)
    img = img.copy()
    img = img_util.hide_uid(img)
    img_util.save_img_in_temp(img)
    img_util.show_img(img)
