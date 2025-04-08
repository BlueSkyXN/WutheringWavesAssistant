import logging
from threading import RLock

from src.core.contexts import Context
from src.core.exceptions import HwndError, raise_as
from src.core.interface import WindowService
from src.util import hwnd_util

logger = logging.getLogger(__name__)


class HwndServiceImpl(WindowService):
    """"Windows Handle to a Window"（窗口句柄）"""

    def __init__(self, context: Context):
        hwnd_util.enable_dpi_awareness()
        super().__init__()
        self._context: Context = context
        self._window = hwnd_util.get_hwnd()
        self._rlock: RLock = RLock()

    @property
    def window(self):
        with self._rlock:
            if not self._window:
                raise HwndError("hwnd is None")
            return self._window

    @raise_as(HwndError)
    def get_client_wh(self) -> tuple[int, int]:
        return hwnd_util.get_client_wh(self.window)

    def refresh(self) -> bool:
        with self._rlock:
            try:
                self._window = hwnd_util.get_hwnd()
                return True
            except Exception:
                logger.exception("Get hwnd error!")
                return False

    @raise_as(HwndError)
    def get_ratio(self):
        """窗口大小与1280px的比例"""
        return 1280 / hwnd_util.get_client_wh(self.window)[0]

    @raise_as(HwndError)
    def get_client_rect_on_screen(self) -> tuple[int, int, int, int]:
        return hwnd_util.get_client_rect_on_screen(self.window)

    @raise_as(HwndError)
    def get_window_rect(self) -> tuple[int, int, int, int]:
        return hwnd_util.get_window_rect(self.window)

    @raise_as(HwndError)
    def get_focus_rect_on_screen(self, region: tuple[float, float, float, float] | None = None) -> tuple[
        int, int, int, int]:
        return hwnd_util.get_focus_rect_on_screen(self.window, region)

    @raise_as(HwndError)
    def is_foreground_window(self) -> bool:
        return hwnd_util.is_foreground_window(self.window)

    @raise_as(HwndError)
    def close_window(self):
        hwnd_util.force_close_process(self.window)

# class NSWindowServiceImpl(WindowService):
#     pass
