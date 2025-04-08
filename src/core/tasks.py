import logging
import math
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from multiprocessing import Process, Event
from typing import Iterable, Any, TypeVar, Callable, Mapping

import psutil
import win32gui
from pynput.mouse import Controller

from src.config import logging_config
from src.core.contexts import Context
from src.core.exceptions import ScreenshotError
from src.core.injector import Container
from src.core.interface import ImgService, OCRService, ControlService, PageEventService, WindowService
from src.util import hwnd_util, keymouse_util

logger = logging.getLogger(__name__)

Task = TypeVar('Task', bound='ProcessTask')


class ProcessTask(ABC):

    def __init__(self, name: str | None, args: Iterable[Any] | None, kwargs: Mapping[str, Any], daemon: bool | None):
        self.name: str | None = name
        self.args: Iterable[Any] | None = args
        self.kwargs: Mapping[str, Any] = kwargs
        self.daemon: bool | None = daemon

        self._start_time: datetime | None = None
        self._end_time: datetime | None = None
        self._restart_time: list[datetime] = []
        self._process: Process | None = None

    @abstractmethod
    def get_task(self, *args) -> Callable[..., None] | None:
        pass

    @classmethod
    def build(cls: type[Task],
              args: Iterable[Any] = (),
              kwargs: Mapping[str, Any] = None,
              name: str | None = None,
              daemon: bool | None = None) -> Task:
        name = name if name is not None else cls.__qualname__
        task = cls(args=args, kwargs=kwargs, name=name, daemon=daemon)
        task._process = Process(target=task.get_task(), args=args, kwargs=kwargs, name=task.name, daemon=task.daemon)
        return task

    def start(self):
        self._start_time = datetime.now()
        self._process.start()
        return self

    def stop(self, timeout=5):
        self._end_time = datetime.now()
        elapsed_time = (self._end_time - self._start_time).total_seconds()
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        logger.info(f"[{self.name}] 任务结束，已运行: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
        self._stop(timeout=timeout)
        return self

    def _stop(self, timeout=5):
        try:
            if not self._process.is_alive():
                return self
            self._process.terminate()
            self._process.join(timeout)
        except Exception:
            logger.error(f"任务[{self.name}]结束失败", exc_info=True)
        return self

    def join(self):
        self._process.join()

    def is_alive(self):
        return self._process.is_alive()

    def restart(self, timeout=5):
        self._stop(timeout=timeout)
        restart_time = datetime.now()
        elapsed_time = (restart_time - self._start_time).total_seconds()
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        logger.warning(f"[{self.name}] 任务重启，已运行: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
        self._restart_time.append(restart_time)
        self._process = Process(
            target=self.get_task(), args=self.args, kwargs=self.kwargs, name=self.name, daemon=self.daemon)
        self._process.start()


class MouseResetProcessTask(ProcessTask):
    def get_task(self, *args) -> Callable[[...], None] | None:
        return mouse_reset_task_run


class AutoBossProcessTask(ProcessTask):
    def get_task(self, *args) -> Callable[..., None] | None:
        return auto_boss_task_run


class AutoPickupProcessTask(ProcessTask):
    def get_task(self, *args) -> Callable[..., None] | None:
        return auto_pickup_task_run


class AutoStoryProcessTask(ProcessTask):
    def get_task(self, *args) -> Callable[..., None] | None:
        return auto_story_task_run


class DailyActivityProcessTask(ProcessTask):
    def get_task(self, *args) -> Callable[..., None] | None:
        return daily_activity_task_run


class ClockAction:
    """定时执行函数"""

    def __init__(self, _callable: Callable[[], None], seconds: float):
        self.callable = _callable
        self.seconds = seconds
        self.start_time = datetime.now()
        self.monotonic = None

    def action(self):
        if self.monotonic is None or time.monotonic() - self.monotonic > self.seconds:
            self.monotonic = time.monotonic()
            try:
                self.callable()
            except Exception:
                pass


def is_gui_process_alive():
    """ 用于修复主动关闭gui时，触发退出异常进入重启游戏流程，判断gui是否还存活 """
    parent_pid = os.getppid()  # 获取 GUI 进程的 PID
    if parent_pid == 1:  # 如果父进程变成 `init`，说明 GUI 进程已退出
        return False
    try:
        parent = psutil.Process(parent_pid)
        return parent.is_running()  # GUI 进程是否仍然在运行
    except psutil.NoSuchProcess:
        return False  # GUI 进程已退出


def mouse_reset_task_run(event: Event, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.info("鼠标重置进程开始运行")
    mouse = Controller()
    last_position = mouse.position
    hwnd = None
    try:
        while event.is_set():
            time.sleep(0.2)
            try:
                if not hwnd or not win32gui.IsWindow(hwnd):
                    time.sleep(0.5)
                    hwnd = hwnd_util.get_hwnd()
                    continue
            except Exception:
                logger.warning("MouseReset: 获取窗口句柄时异常")
                time.sleep(5)
                continue
            current_position = mouse.position
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            center_position = (left + right) / 2, (top + bottom) / 2
            cur_pos_to_center_distance = math.sqrt(
                (current_position[0] - center_position[0]) ** 2
                + (current_position[1] - center_position[1]) ** 2
            )
            cur_pos_to_last_pos_distance = math.sqrt(
                (current_position[0] - last_position[0]) ** 2
                + (current_position[1] - last_position[1]) ** 2
            )
            if cur_pos_to_last_pos_distance > 200 and cur_pos_to_center_distance < 50:
                mouse.position = last_position
            else:
                last_position = current_position
    except KeyboardInterrupt:
        logger.info("鼠标重置进程结束")


def auto_boss_task_run(event: Event, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    # logging_config.setup_logging_test(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("刷boss任务进程开始运行")
    hwnd_util.set_hwnd_left_top()

    context = Context()
    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    img_service: ImgService = container.img_service()
    ocr_service: OCRService = container.ocr_service()
    control_service: ControlService = container.control_service()
    page_event_service: PageEventService = container.auto_boss_service()

    logger.debug("-------- run ----------")
    count = 0
    clock_action = ClockAction(control_service.activate, 3.0)

    def close_game():
        try:
            logger.info("定时关闭游戏")
            hwnd_util.force_close_process(window_service.window)
        except Exception:
            logger.exception("关闭游戏时异常")

    try:
        while event.is_set():
            try:
                count += 1
                # logger.info("count %s", count)
                clock_action.action()

                src_img = img_service.screenshot()
                img = img_service.resize(src_img)
                result = ocr_service.ocr(img)
                page_event_service.execute(src_img=src_img, img=img, ocr_results=result)
            except ScreenshotError:
                close_game()
                raise
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt")
    except Exception as e:
        logger.exception(e)
    finally:
        try:
            keymouse_util.key_up(window_service.window, "W")
            keymouse_util.key_up(window_service.window, "LSHIFT")
        except Exception:
            pass
        logger.info("刷boss任务进程结束")


def auto_pickup_task_run(event: Event, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("自动拾取任务进程开始运行")
    context = Context()
    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    control_service: ControlService = container.control_service()
    page_event_service: PageEventService = container.auto_pickup_service()
    clock_action = ClockAction(control_service.activate, 3.0)
    try:
        while event.is_set():
            clock_action.action()
            try:
                page_event_service.execute()
            except ScreenshotError:
                logger.exception("截图失败")
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("自动拾取任务进程结束")
    except Exception as e:
        logger.exception(e)
    finally:
        try:
            keymouse_util.key_up(window_service.window, "W")
            keymouse_util.key_up(window_service.window, "LSHIFT")
        except Exception:
            pass


def auto_story_task_run(event: Event, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("自动剧情任务进程开始运行")
    context = Context()
    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    control_service: ControlService = container.control_service()
    page_event_service: PageEventService = container.auto_story_service()
    clock_action = ClockAction(control_service.activate, 3.0)
    count = 0
    try:
        while event.is_set():
            logger.debug("count: %s", count)
            count += 1
            clock_action.action()
            try:
                page_event_service.execute()
            except ScreenshotError as e:
                logger.exception("截图失败")
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("自动剧情任务进程结束")
    except Exception as e:
        logger.exception(e)
    finally:
        try:
            keymouse_util.key_up(window_service.window, "W")
            keymouse_util.key_up(window_service.window, "LSHIFT")
        except Exception:
            pass


def daily_activity_task_run(event: Event, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("每日任务进程开始运行")
    hwnd_util.set_hwnd_left_top()
    context = Context()
    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    control_service: ControlService = container.control_service()
    page_event_service: PageEventService = container.daily_activity_service()
    # clock_action = ClockAction(control_service.activate, 3.0)
    try:
        # while event.is_set():
        #     clock_action.action()
        page_event_service.execute()
    except KeyboardInterrupt:
        logger.info("每日任务进程结束")
    except Exception as e:
        logger.exception(e)
    finally:
        try:
            keymouse_util.key_up(window_service.window, "W")
            keymouse_util.key_up(window_service.window, "LSHIFT")
        except Exception:
            pass


if __name__ == '__main__':
    _stop_event = Event()
    _stop_event.set()
    # AutoBossProcessTask.build(args=(_stop_event,), daemon=True).start()
    MouseResetProcessTask.build(args=(_stop_event,), daemon=True).start().join()
