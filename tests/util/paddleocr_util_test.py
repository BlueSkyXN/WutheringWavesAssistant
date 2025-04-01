import logging

from src.util import file_util, img_util, paddleocr_util, screenshot_util, hwnd_util

logger = logging.getLogger(__name__)


def test_ocr_from_game():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    paddleocr = paddleocr_util.create_paddleocr()
    img = screenshot_util.screenshot(hwnd)
    results = paddleocr_util.execute_paddleocr(paddleocr, img)
    paddleocr_util.print_paddleocr_result(results)
    img = paddleocr_util.draw_paddleocr_result(results, img)
    img_util.show_img(img)
    img_util.save_img_in_temp(img)


def test_ocr_rec_only_from_game():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    paddleocr = paddleocr_util.create_paddleocr()
    img = screenshot_util.screenshot(hwnd)
    img_util.save_img_in_temp(img)
    results = paddleocr_util.execute_paddleocr(paddleocr, img, det=False, rec=True, cls=False)
    paddleocr_util.print_paddleocr_result(results)
    img = paddleocr_util.draw_paddleocr_result(results, img)
    img_util.show_img(img)
    img_util.save_img_in_temp(img)


def test_login_hwnd():
    logger.debug("\n")
    hwnd_list_all, hwnd_list_visible = hwnd_util.get_login_hwnd_official()
    # logger.debug("遍历所有登录窗口")
    # if hwnd_list_all is not None and len(hwnd_list_all) > 0:
    #     for login_hwnd in hwnd_list_all:
    #         get_window_info(login_hwnd)
    #         screenshot_util.screenshot(login_hwnd)
    paddleocr = paddleocr_util.create_paddleocr()
    if hwnd_list_visible is not None and len(hwnd_list_visible) > 0:
        logger.debug("遍历所有登录可见窗口")
        for login_hwnd in hwnd_list_visible:
            img = screenshot_util.screenshot(login_hwnd)
            results = paddleocr_util.execute_paddleocr(paddleocr, img)
            paddleocr_util.print_paddleocr_result(results)
            img = img.copy()
            img = paddleocr_util.draw_paddleocr_result(results, img)
            img_util.show_img(img)
            img_util.save_img_in_temp(img)
    else:
        logger.debug("未找到登录窗口")


def test_ocr_from_dir():
    logger.debug("\n")
    img_path = file_util.get_assets_screenshot("Dialogue_001.png")
    img = img_util.read_img(img_path)
    paddleocr = paddleocr_util.create_paddleocr()
    results = paddleocr_util.execute_paddleocr(paddleocr, img)
    paddleocr_util.print_paddleocr_result(results)
    img = img.copy()
    # img = img_util.hide_uid(img)
    img = paddleocr_util.draw_paddleocr_result(results, img)
    img_util.show_img(img)
    img_util.save_img_in_temp(img)


def test_ocr_login():
    logger.debug("\n")
    img_path = file_util.get_assets_screenshot("Login_001.png")
    img = img_util.read_img(img_path)
    paddleocr = paddleocr_util.create_paddleocr()
    results = paddleocr_util.execute_paddleocr(paddleocr, img)
    paddleocr_util.print_paddleocr_result(results)
    img = paddleocr_util.draw_paddleocr_result(results, img)
    img_util.show_img(img)
    img_util.save_img_in_temp(img)
