import logging
import os
import subprocess
import threading
import time
from enum import Enum
from multiprocessing import Event

from src.config.gui_config import ParamConfig
from src.core import environs
from src.core.contexts import Context
from src.core.exceptions import StopError
from src.core.tasks import ProcessTask
from src.util import hwnd_util

logger = logging.getLogger(__name__)


class TaskOpsEnum(Enum):
    START = "START"
    STOP = "STOP"


class TaskMonitor:

    def __init__(self, running_tasks: dict[str, tuple[ProcessTask, Event]], param_config_path: str, gui_win_id: int):
        self.running_tasks: dict[str, tuple[ProcessTask, Event]] = running_tasks
        self.param_config_path = param_config_path
        self.gui_win_id = gui_win_id

        self.context = Context()

        # 参数快照
        self.param_config_snapshot = ParamConfig.snapshot(self.param_config_path)
        self.param_config = ParamConfig.build(content=self.param_config_snapshot)

        self.game_path = self.get_game_path()  # 先找运行中的游戏
        self.game_path = hwnd_util.get_ww_exe_path(self.game_path)
        logger.info("Path: %s", self.game_path)

        # 游戏定时重启参数
        self.game_restart_duration = self._get_restart_duration()
        self.game_restart_time: float | None = None  # time.monotonic()

        # 任务重启冷却时间，防止异常时一直重启
        self.task_restart_cooldown = 20.0  # seconds
        self.task_restart_time: float | None = None  # time.monotonic()

        self._monitor_event = threading.Event()
        self._monitor_thread = threading.Thread(target=self.run)
        self._monitor_thread.daemon = True

    def start(self):
        self._monitor_event.set()
        self._monitor_thread.start()

    def stop(self, need_join: bool = True):
        self._monitor_event.clear()
        if need_join:
            self._monitor_thread.join()

    def run(self):
        """ 监控任务函数，用于重启异常退出的任务，对于刷boss任务，还会检查和重启游戏 """
        if not self.running_tasks:
            logger.warning("任务列表为空，任务监控线程退出")
            return

        logger.info("任务监控线程开始运行")
        try:
            first_sleep_seconds = 25
            # 检查游戏存活状态(重启游戏)
            if "AutoBossProcessTask" in self.running_tasks:
                is_alive = self._monitor_game()  # 重启游戏，等待直到完全启动
                if not is_alive:  # 游戏不存在任务会失败，立马启动监控拉起失败的任务
                    first_sleep_seconds = 0
            # 启动监控前等一会让任务进程先运行
            self._sleep(first_sleep_seconds)

            duration = 10  # seconds
            duration_before = 5  # seconds
            duration_after = duration - duration_before  # seconds

            while self._monitor_event.is_set():
                self._sleep(duration_before)

                # 定时重启(仅关闭游戏)
                if "AutoBossProcessTask" in self.running_tasks and self.game_restart_duration:
                    if not self.game_restart_time:
                        self.game_restart_time = time.monotonic()
                    elif time.monotonic() - self.game_restart_time > self.game_restart_duration:
                        self._close_game()
                        self.game_restart_time = time.monotonic()
                        self._sleep(5)

                if not self._monitor_event.is_set():
                    break

                # 检查游戏存活状态(重启游戏)
                if "AutoBossProcessTask" in self.running_tasks:
                    self._monitor_game()

                if not self._monitor_event.is_set():
                    break

                # 检查任务存活状态
                for k, v in self.running_tasks.copy().items():
                    if k == "MouseResetProcessTask":
                        continue
                    process_task, event = v
                    if not event.is_set():
                        continue
                    self._sleep(1)
                    if not event.is_set() or process_task.is_alive():
                        continue
                    if self.task_restart_time is None or time.monotonic() - self.task_restart_time > self.task_restart_cooldown:
                        self.task_restart_time = time.monotonic()
                        process_task.restart()

                self._sleep(duration_after)
        except KeyboardInterrupt:
            raise
        except StopError:
            pass
        except Exception:
            logger.exception("任务监控线程异常")
            raise
        finally:
            logger.info("任务监控线程已停止")

    def _monitor_game(self):
        """ 检查游戏状态，异常则触发重启动作 """
        is_alive = False
        try:
            if crash_hwnd := hwnd_util.get_ue4_client_crash_hwnd():
                is_alive = False
                logger.warning("监测到UE4-Client Game已崩溃，关闭弹窗")
                hwnd_util.force_close_process(crash_hwnd)
            elif hwnd_util.get_hwnd(self.game_path, force=True):
                is_alive = True
        except Exception:
            logger.exception("游戏不存在")
        if is_alive:
            return True
        logger.warning("开始重启游戏")
        self._restart_game()
        return False

    def _restart_game(self) -> bool:
        """ 监控到游戏异常时调用用于重启游戏 """
        start_time = time.monotonic()
        while time.monotonic() - start_time < 300:
            self._sleep(2)
            try:
                logger.info("先尝试关闭游戏")
                hwnd = hwnd_util.get_hwnd(self.game_path, force=True)
                if hwnd:
                    hwnd_util.force_close_process(hwnd)
                else:
                    logger.warning("游戏窗口不存在")
            except Exception:
                logger.error("游戏不存在")
            self._sleep(5)
            subprocess.Popen([self.game_path],
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            self._sleep(20)
            for i in range(10):
                try:
                    hwnd = hwnd_util.get_hwnd(self.game_path, force=True)
                    if hwnd:
                        logger.info("游戏已重启")
                        self._sleep(10)
                        return True
                except KeyboardInterrupt:
                    logger.warning("KeyboardInterrupt")
                    raise
                except StopError:
                    raise
                except Exception as e2:
                    logger.exception(e2)
                self._sleep(5)
        logger.error("游戏重启失败")
        return False

    def start_game(self):
        """ 监控任务开始时会调用一次用于启动游戏 """
        try:
            if hwnd_util.get_hwnd(self.game_path, force=True):
                return
            logger.warning("游戏不存在，开始启动游戏")
            subprocess.Popen([self.game_path],
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        except Exception as e:
            logger.exception(e)

    def _close_game(self):
        """ 定时重启游戏时调用，用于关闭游戏 """
        try:
            logger.info("定时关闭游戏")
            hwnd = hwnd_util.get_hwnd(self.game_path, force=True)
            if hwnd:
                hwnd_util.force_close_process(hwnd)
            else:
                logger.warning("游戏窗口不存在")
        except Exception:
            logger.exception("定时关闭游戏时异常")

    def _get_restart_duration(self) -> int | None:
        """ 获取定时重启时间 秒，为空则是关闭定时 """
        try:
            # 定时重启开启时间，格式: 时#分#秒 或 Close
            period = self.param_config.autoRestartPeriod.strip().split("#")
            restart_duration = 3600 * int(period[0]) + 60 * int(period[1]) + int(period[2])
            if restart_duration < 10:
                logger.warning("定时重启周期过短: %ss, 自动关闭定时", restart_duration)
                return None
            logger.info("已开启定时重启游戏，周期: %ss", restart_duration)
            return restart_duration
        except Exception:
            return None

    def get_game_path(self) -> str | None:
        hwnds = hwnd_util.get_hwnds()
        if not hwnds:  # 没有运行中的游戏，则按配置来
            return self.param_config.get_game_path()
        if len(hwnds) == 1:
            hwnd = hwnds[0]  # 运行中的最优先，不管配置
        else:  # 多个游戏同时运行，优先选自定义配置的
            hwnd = None
            if self.param_config.gamePath and self.param_config.gamePath != "Auto":
                hwnd = hwnd_util.filter_hwnds(hwnds, self.param_config.gamePath)
            if not hwnd:
                hwnd = hwnds[0]
        return hwnd_util.get_exe_path_from_hwnd(hwnd)

    def _sleep(self, sleep_seconds: float) -> None:
        if sleep_seconds <= 0:
            return
        while sleep_seconds > 0:
            if not self._monitor_event.is_set():
                raise StopError()
            if sleep_seconds <= 1.0:
                time.sleep(sleep_seconds)
            else:
                time.sleep(1)
            sleep_seconds -= 1


class MainController:

    def __init__(self):
        logger.debug("Initializing %s", self.__class__.__name__)

        from src.core.tasks import MouseResetProcessTask, AutoBossProcessTask, AutoPickupProcessTask, \
            AutoStoryProcessTask, DailyActivityProcessTask, ProcessTask

        self.tasks = {
            "MouseResetProcessTask": MouseResetProcessTask,
            "AutoBossProcessTask": AutoBossProcessTask,
            "AutoPickupProcessTask": AutoPickupProcessTask,
            "AutoStorySkipProcessTask": AutoStoryProcessTask,
            "AutoStoryEnjoyProcessTask": AutoStoryProcessTask,
            "DailyActivityProcessTask": DailyActivityProcessTask,
        }
        self.running_tasks: dict[str, tuple[ProcessTask, Event]] = {}
        self._lock = threading.Lock()

        self.task_monitor = None

        self.param_config_path = None
        self.gui_win_id = None

    def execute(self, task_name: str, task_ops: str):
        logger.debug("task_name: %s, task_ops: %s", task_name, task_ops)
        with self._lock:
            if task_ops == TaskOpsEnum.START.value:
                logger.info("准备开启任务: %s", task_name)
                if self.running_tasks.get(task_name):
                    logger.warning("任务已存在，请勿重复提交")
                    return False, "任务已存在，请勿重复提交"
                event = Event()
                event.set()
                task_builder = self.tasks.get(task_name)

                from src.config import logging_config
                from src.core import environs
                # TODO Manager
                kwargs = {}
                kwargs["PARENT_PID"] = str(os.getpid())
                kwargs["GUI_WIN_ID"] = str(self.gui_win_id)
                kwargs["LOG_QUEUE"] = logging_config.get_log_queue()
                if task_name == "AutoStorySkipProcessTask":
                    kwargs["SKIP_IS_OPEN"] = "True"
                elif task_name == "AutoStoryEnjoyProcessTask":
                    kwargs["SKIP_IS_OPEN"] = "False"
                # if task_name in ["AutoBossProcessTask", "AutoPickupProcessTask"]:
                if task_name in ["AutoBossProcessTask"]:
                    kwargs[environs.ENV_WWA_OCR_USE_GPU] = "True"
                else:
                    kwargs[environs.ENV_WWA_OCR_USE_GPU] = "False"

                task = task_builder.build(args=(event,), kwargs=kwargs, daemon=True)
                self.running_tasks[task_name] = (task, event)

                self.task_monitor = TaskMonitor(self.running_tasks.copy(), self.param_config_path, self.gui_win_id)
                kwargs["GAME_PATH"] = self.task_monitor.game_path
                kwargs["PARAM_CONFIG_SNAPSHOT"] = self.task_monitor.param_config_snapshot

                # self.task_monitor.start_game()

                task.start()

                # if task_name in ["AutoBossProcessTask", "DailyActivityProcessTask"]:
                #     from src.core.tasks import MouseResetProcessTask
                #     mouse_reset_process_task = MouseResetProcessTask.build(
                #         args=(event,), kwargs=kwargs, daemon=True
                #     ).start()
                #     self.running_tasks["MouseResetProcessTask"] = (mouse_reset_process_task, event)

                self.task_monitor.start()

                logger.info("任务已提交: %s", task_name)
                return True, "任务已提交"
            elif task_ops == TaskOpsEnum.STOP.value:
                logger.info("准备关闭任务: %s", task_name)
                if not self.running_tasks.get(task_name):
                    logger.warning("任务不存在，无需关闭")
                    return True, "任务不存在，无需关闭"

                self.task_monitor.stop()
                self.task_monitor = None

                task, event = self.running_tasks[task_name]
                event.clear()
                task.stop(0.1)
                self.running_tasks.pop(task_name)
                # if self.running_tasks.get("MouseResetProcessTask"):
                #     task, event = self.running_tasks["MouseResetProcessTask"]
                #     task.stop()
                #     self.running_tasks.pop("MouseResetProcessTask")
                logger.info("任务已停止: %s", task_name)
                return True, "任务已停止"
            else:
                raise NotImplementedError(f"不支持的类型{task_ops}")

    def stop(self):
        logger.info("关闭主窗口")
        if self.task_monitor:
            self.task_monitor.stop(False)
        for task_name, task_event in self.running_tasks.items():
            if not task_event:
                continue
            task, event = task_event
            event.clear()
            task.stop(0)

    def set_param_config_path(self, path: str):
        logger.debug("param_config_path: %s", path)
        self.param_config_path = path
        environs.set_param_config_path(path)

    def set_gui_win_id(self, gui_win_id: int):
        logger.debug("gui_win_id: %s", gui_win_id)
        self.gui_win_id = gui_win_id


if __name__ == '__main__':
    from src.config import logging_config

    logging_config.setup_logging_test()
    main_controller = MainController()

    # main_controller.execute("MouseResetController", TaskOpsEnum.START.value)
    main_controller.execute("AutoBossController", TaskOpsEnum.START.value)
    # main_controller.execute("AutoPickupController", TaskOpsEnum.START.value)
    # main_controller.execute("AutoStoryController", TaskOpsEnum.START.value)
    # main_controller.execute("DailyActivityController", TaskOpsEnum.START.value)
    time.sleep(10000000)
