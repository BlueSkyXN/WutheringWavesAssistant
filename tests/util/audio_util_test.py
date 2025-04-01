import logging
import time

from src.util import audio_util, hwnd_util

logger = logging.getLogger(__name__)


def test_audio_util():
    logger.debug("\n")
    target_exe = hwnd_util.CLIENT_WIN64_SHIPPING_EXE
    audio_util.mute_program(target_exe, mute=True)  # 静音
    time.sleep(3)
    audio_util.mute_program(target_exe, mute=False)  # 取消静音
    time.sleep(1)
    audio_util.is_muted(target_exe)


def test_open_audio():
    logger.debug("\n")
    target_exe = hwnd_util.CLIENT_WIN64_SHIPPING_EXE
    audio_util.mute_program(target_exe, mute=False)  # 取消静音
    audio_util.is_muted(target_exe)


def test_close_audio():
    logger.debug("\n")
    target_exe = hwnd_util.CLIENT_WIN64_SHIPPING_EXE
    audio_util.mute_program(target_exe, mute=True)  # 静音
    audio_util.is_muted(target_exe)
