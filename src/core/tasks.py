import logging
import math
import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from multiprocessing import Process, Event
from typing import Iterable, Any, TypeVar, Callable, Mapping

import psutil
import win32gui
from pynput.mouse import Controller

from src.config import logging_config
from src.config.gui_config import ParamConfig
from src.core.contexts import Context
from src.core.exceptions import ScreenshotError
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
        self._restart_time_list: list[datetime] = []
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
        # task._process = Process(target=task.get_task(), args=args, kwargs=kwargs, name=task.name, daemon=task.daemon)
        return task

    def start(self):
        self._process = Process(
            target=self.get_task(), args=self.args, kwargs=self.kwargs, name=self.name, daemon=self.daemon)
        self._start_time = datetime.now()
        self._process.start()
        return self

    def stop(self, timeout=3):
        self._end_time = datetime.now()
        elapsed_time = (self._end_time - self._start_time).total_seconds()
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        logger.info(f"[{self.name}] 任务结束，已运行: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
        self._stop(timeout=timeout)
        return self

    def _stop(self, timeout=3):
        if self._process is None:
            return
        try:
            if not self._process.is_alive():
                return self
            self._process.terminate()
            if timeout > 0:
                self._process.join(timeout)
        except Exception:
            logger.exception(f"任务[{self.name}]结束失败")
        return self

    def join(self):
        self._process.join()

    def is_alive(self):
        return self._process.is_alive()

    def restart(self, timeout=3):
        self._stop(timeout=timeout)
        if len(self._restart_time_list) > 0:
            start_time_last = self._restart_time_list[-1]
        else:
            start_time_last = self._start_time
        restart_time = datetime.now()
        logger.warning(f"[{self.name}] 任务重启，上次重启时间: {start_time_last.strftime("%Y-%m-%d %H:%M:%S")}")
        self._restart_time_list.append(restart_time)
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


def create_parent_monitor(event: Event, parent_pid: str):
    if not parent_pid:
        return

    def run():
        try:
            pid = int(parent_pid)
            # 获取父进程
            parent_process = psutil.Process(pid)
        except Exception as e:
            logger.error(e)
            return
        while event.is_set():
            try:
                if not parent_process.is_running():
                    event.clear()
                    logger.info("检测到父进程结束，退出任务")
                    break  # 父进程退出后，子进程退出
            except Exception as e:
                logger.exception(e)
                return
            time.sleep(5)
        logger.info("父进程监控结束")

    monitor_thread = threading.Thread(target=run, name="ParentPidMonitorThread")
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor_thread


def create_mouse_reset_monitor(event: Event, parent_pid: str, **kwargs):
    if not parent_pid:  # pid不存在就不用启动
        return

    def run(**run_kwargs):
        mouse_reset_task_run(event, **run_kwargs)

    monitor_thread = threading.Thread(target=run, kwargs=kwargs, name="MouseResetMonitorThread")
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor_thread


def mouse_reset_task_run(event: Event, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.info("鼠标重置任务开始运行")
    mouse = Controller()
    last_position = mouse.position
    hwnd = None
    try:
        while event.is_set():
            time.sleep(0.05)
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
        pass
    finally:
        logger.info("鼠标重置任务结束")


def auto_boss_task_run(event: Event, **kwargs):
    try:
        from src.core.injector import Container

        for k, v in kwargs.items():
            if isinstance(v, str):
                os.environ[k] = v
        logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
        # logging_config.setup_logging_test(kwargs.get("LOG_QUEUE"))
        logger.debug("kwargs: %s", kwargs)
        logger.debug(os.environ)
        logger.info("刷boss任务进程开始运行")

        context = Context()
        # 从快照还原配置
        if param_config_snapshot := kwargs.get("PARAM_CONFIG_SNAPSHOT"):
            context.param_config = ParamConfig.build(content=param_config_snapshot)
        if game_path := kwargs.get("GAME_PATH"):
            context.param_config.gamePath = game_path
        # 新旧配置兼容
        context.app_config.TargetBoss = context.param_config.get_boss_name_list()
        logger.info("Boss Rush: %s", context.app_config.TargetBoss)
        context.app_config.DungeonWeeklyBossLevel = context.param_config.get_boss_level_int()

        container = Container.build(context)
        logger.debug("Create application context")
        window_service: WindowService = container.window_service()
        img_service: ImgService = container.img_service()
        ocr_service: OCRService = container.ocr_service()
        control_service: ControlService = container.control_service()

        hwnd_util.set_hwnd_left_top(window_service.window)
        time.sleep(0.2)
        logger.debug(game_path)
        parent_pid = kwargs.get("PARENT_PID")
        create_parent_monitor(event, parent_pid)
        create_mouse_reset_monitor(event, parent_pid, **kwargs)
        clock_action = ClockAction(control_service.activate, 3.0)

        logger.debug("-------- run ----------")
        count = 0

        page_event_service: PageEventService = container.auto_boss_service()

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
                    try:
                        logger.warning("截图异常，关闭游戏")
                        hwnd_util.force_close_process(window_service.window)
                    except Exception:
                        logger.error("关闭游戏时异常")
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
    except Exception as e:
        logger.exception(e)


def auto_pickup_task_run(event: Event, **kwargs):
    from src.core.injector import Container

    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("自动拾取任务进程开始运行")

    context = Context()
    # 从快照还原配置
    if param_config_snapshot := kwargs.get("PARAM_CONFIG_SNAPSHOT"):
        context.param_config = ParamConfig.build(content=param_config_snapshot)
    if game_path := kwargs.get("GAME_PATH"):
        context.param_config.gamePath = game_path
    # 新旧配置兼容
    context.app_config.TargetBoss = context.param_config.get_boss_name_list()
    logger.debug("TargetBoss: %s", context.app_config.TargetBoss)
    context.app_config.DungeonWeeklyBossLevel = context.param_config.get_boss_level_int()

    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    # img_service: ImgService = container.img_service()
    # ocr_service: OCRService = container.ocr_service()
    control_service: ControlService = container.control_service()

    # hwnd_util.set_hwnd_left_top(window_service.window)
    # time.sleep(0.2)
    logger.debug(game_path)
    parent_pid = kwargs.get("PARENT_PID")
    create_parent_monitor(event, parent_pid)
    # create_mouse_reset_monitor(event, parent_pid, **kwargs)
    clock_action = ClockAction(control_service.activate, 3.0)

    page_event_service: PageEventService = container.auto_pickup_service()

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
    from src.core.injector import Container

    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("自动剧情任务进程开始运行")

    context = Context()
    # 从快照还原配置
    if param_config_snapshot := kwargs.get("PARAM_CONFIG_SNAPSHOT"):
        context.param_config = ParamConfig.build(content=param_config_snapshot)
    if game_path := kwargs.get("GAME_PATH"):
        context.param_config.gamePath = game_path
    # 新旧配置兼容
    context.app_config.TargetBoss = context.param_config.get_boss_name_list()
    logger.debug("TargetBoss: %s", context.app_config.TargetBoss)
    context.app_config.DungeonWeeklyBossLevel = context.param_config.get_boss_level_int()

    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    # img_service: ImgService = container.img_service()
    # ocr_service: OCRService = container.ocr_service()
    control_service: ControlService = container.control_service()

    # hwnd_util.set_hwnd_left_top(window_service.window)
    # time.sleep(0.2)
    logger.debug(game_path)
    parent_pid = kwargs.get("PARENT_PID")
    create_parent_monitor(event, parent_pid)
    # create_mouse_reset_monitor(event, parent_pid, **kwargs)
    clock_action = ClockAction(control_service.activate, 3.0)

    page_event_service: PageEventService = container.auto_story_service()
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
    from src.core.injector import Container

    for k, v in kwargs.items():
        if isinstance(v, str):
            os.environ[k] = v
    logging_config.setup_logging(kwargs.get("LOG_QUEUE"))
    logger.debug("kwargs: %s", kwargs)
    logger.debug(os.environ)
    logger.info("每日任务进程开始运行")

    context = Context()
    # 从快照还原配置
    if param_config_snapshot := kwargs.get("PARAM_CONFIG_SNAPSHOT"):
        context.param_config = ParamConfig.build(content=param_config_snapshot)
    if game_path := kwargs.get("GAME_PATH"):
        context.param_config.gamePath = game_path
    # 新旧配置兼容
    context.app_config.TargetBoss = context.param_config.get_boss_name_list()
    logger.debug("TargetBoss: %s", context.app_config.TargetBoss)
    context.app_config.DungeonWeeklyBossLevel = context.param_config.get_boss_level_int()

    container = Container.build(context)
    logger.debug("Create application context")
    window_service: WindowService = container.window_service()
    # img_service: ImgService = container.img_service()
    # ocr_service: OCRService = container.ocr_service()
    control_service: ControlService = container.control_service()

    hwnd_util.set_hwnd_left_top(window_service.window)
    time.sleep(0.2)
    logger.debug(game_path)
    parent_pid = kwargs.get("PARENT_PID")
    create_parent_monitor(event, parent_pid)
    create_mouse_reset_monitor(event, parent_pid, **kwargs)
    # clock_action = ClockAction(control_service.activate, 3.0)

    page_event_service: PageEventService = container.daily_activity_service()

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
