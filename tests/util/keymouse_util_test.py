import logging
import time

from src.util import hwnd_util, keymouse_util

logger = logging.getLogger(__name__)


def test_keymouse_util():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    keymouse_util.window_activate(hwnd)

    keymouse_util.tap_key(hwnd, "A")
    time.sleep(0.5)
    keymouse_util.tap_key(hwnd, "A")
    time.sleep(1)

    keymouse_util.tap_key(hwnd, "S")
    time.sleep(0.5)
    keymouse_util.tap_key(hwnd, "S")
    time.sleep(1)

    keymouse_util.tap_key(hwnd, "D")
    time.sleep(0.5)
    keymouse_util.tap_key(hwnd, "D")
    time.sleep(1)

    keymouse_util.tap_key(hwnd, "W")
    time.sleep(0.5)
    keymouse_util.tap_key(hwnd, "W")
    time.sleep(1)

    keymouse_util.middle_click(hwnd)
    time.sleep(2)

    for i in range(5):
        keymouse_util.scroll_mouse(hwnd, -5)
        time.sleep(0.01)
    time.sleep(2)
    for i in range(5):
        keymouse_util.scroll_mouse(hwnd, 5)
        time.sleep(0.01)
    time.sleep(2)

    keymouse_util.tap_space(hwnd)
    time.sleep(2)
    keymouse_util.tap_space(hwnd)
    time.sleep(2)

    keymouse_util.tap_esc(hwnd)
    time.sleep(2)
    keymouse_util.tap_esc(hwnd)
    time.sleep(1)


def test_get_set_mouse_position():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    time.sleep(5)
    for i in range(3):
        keymouse_util.window_activate(hwnd)
        keymouse_util.get_mouse_position()
        x1, y1, x2, y2 = hwnd_util.get_client_rect_on_screen(hwnd)
        keymouse_util.set_mouse_position(hwnd, x2, (y1 + y2) // 2)
        time.sleep(0.5)
        keymouse_util.get_mouse_position()
        logger.debug("\n")
        time.sleep(1)

def test_scroll2():
    # .scroll_mouse(20, x, y)
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    hwnd_util.enable_dpi_awareness()
    # hwnd_util.set_hwnd_left_top(hwnd)
    time.sleep(0.5)
    keymouse_util.window_activate(hwnd)
    time.sleep(1)
    x, y = hwnd_util.get_client_wh(hwnd)
    x, y = x // 2, y // 2
    keymouse_util.click(hwnd, x, y)
    time.sleep(2)
    keymouse_util.scroll_mouse(hwnd, 100, x, y)
    time.sleep(2)
    keymouse_util.scroll_mouse(hwnd, -100, x, y)
    time.sleep(2)
    keymouse_util.scroll_mouse(hwnd, 30, x, y)
    time.sleep(2)




