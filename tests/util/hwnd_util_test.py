import logging
import time

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

def test_hung():
    import ctypes
    hwnd_util.enable_dpi_awareness()
    hwnd = hwnd_util.get_hwnd()
    def is_window_hung(hwnd):
        return ctypes.windll.user32.IsHungAppWindow(hwnd) != 0  # 非 0 代表卡死

    import psutil

    def is_process_hung(process_name):
        for proc in psutil.process_iter(['name', 'cpu_percent']):
            if proc.info['name'].lower() == process_name.lower():
                return proc.info['cpu_percent'] < 0.5  # CPU 长时间接近 0 说明卡死
        return False  # 进程未找到

    for i in range(10):
        if is_window_hung(hwnd):
            print("窗口卡死")
        else:
            print("窗口正常运行")

        if is_process_hung(hwnd_util.CLIENT_WIN64_SHIPPING_EXE):  # 进程名可用 task manager 查
            print("游戏可能卡死")
        else:
            print("游戏正常运行")
        time.sleep(2)
