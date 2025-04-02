import logging

from src.util import hwnd_util, img_util, screenshot_util

logger = logging.getLogger(__name__)


def test_hwnd_util():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    get_window_info(hwnd)
    hwnd_util.enable_dpi_awareness()
    get_window_info(hwnd)


def test_login_hwnd_official():
    logger.debug("\n")
    hwnd_list_all, hwnd_list_visible = hwnd_util.get_login_hwnd_official()
    # logger.debug("遍历所有登录窗口")
    # if hwnd_list_all is not None and len(hwnd_list_all) > 0:
    #     for login_hwnd in hwnd_list_all:
    #         get_window_info(login_hwnd)
    #         screenshot_util.screenshot(login_hwnd)
    if hwnd_list_visible is not None and len(hwnd_list_visible) > 0:
        logger.debug("遍历所有登录可见窗口")
        for login_hwnd in hwnd_list_visible:
            get_window_info(login_hwnd)
            img = screenshot_util.screenshot(login_hwnd)
            img = img.copy()
            img = img_util.hide_uid(img)
            img_util.save_img_in_temp(img)
            img_util.show_img(img)
    else:
        logger.debug("未找到登录窗口")


def get_window_info(hwnd):
    hwnd_util.get_sys_dpi()
    hwnd_util.get_window_dpi(hwnd)
    hwnd_util.get_window_wh(hwnd)
    hwnd_util.get_client_wh(hwnd)


def test_pid():
    pid = hwnd_util.get_hwnd_by_exe_name(hwnd_util.CLIENT_WIN64_SHIPPING_EXE)
    logger.debug(pid)


