import logging
import subprocess
import threading
import time
from enum import Enum
from multiprocessing import Event, Lock

from src.core.contexts import Context
from src.core.injector import Container
from src.util import hwnd_util

logger = logging.getLogger(__name__)


class TaskOpsEnum(Enum):
    START = "START"
    STOP = "STOP"


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
        self._lock: Lock = Lock()

        self.context = Context()
        self.container = Container.build(self.context)

        self.restart_duration = self.get_restart_duration()
        self.restart_time = None

        self._monitor_event = threading.Event()
        self._monitor_event.set()
        self._monitor_thread = threading.Thread(target=self.monitor)
        self._monitor_thread.daemon = True
        self._monitor_running = False


    def execute(self, task_name: str, task_ops: str):
        logger.debug("task_name: %s, task_ops: %s", task_name, task_ops)
        with self._lock:
            if not self._monitor_running:
                # 提交了任务才启动，懒启动
                self._monitor_running = True
                self._monitor_thread.start()

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
                kwargs = {}
                kwargs["LOG_QUEUE"] = logging_config.get_log_queue()
                if task_name == "AutoStorySkipProcessTask":
                    kwargs["SKIP_IS_OPEN"] = "True"
                elif task_name == "AutoStoryEnjoyProcessTask":
                    kwargs["SKIP_IS_OPEN"] = "False"
                if task_name == "AutoBossProcessTask":
                    kwargs[environs.ENV_WWA_OCR_USE_GPU] = "True"
                else:
                    kwargs[environs.ENV_WWA_OCR_USE_GPU] = "False"

                task = task_builder.build(args=(event,), kwargs=kwargs, daemon=True).start()
                self.running_tasks[task_name] = (task, event)
                if task_name in ["AutoBossProcessTask", "DailyActivityProcessTask"]:
                    from src.core.tasks import MouseResetProcessTask
                    mouse_reset_process_task = MouseResetProcessTask.build(args=(event,), kwargs=kwargs,
                                                                           daemon=True).start()
                    self.running_tasks["MouseResetProcessTask"] = (mouse_reset_process_task, event)
                logger.info("任务已提交: %s", task_name)
                return True, "任务已提交"
            elif task_ops == TaskOpsEnum.STOP.value:
                logger.info("准备关闭任务: %s", task_name)
                if not self.running_tasks.get(task_name):
                    logger.warning("任务不存在，无需关闭")
                    return True, "任务不存在，无需关闭"
                task, event = self.running_tasks[task_name]
                event.clear()
                time.sleep(0.1)
                task.stop()
                self.running_tasks.pop(task_name)
                if self.running_tasks.get("MouseResetProcessTask"):
                    task, event = self.running_tasks["MouseResetProcessTask"]
                    task.stop()
                    self.running_tasks.pop("MouseResetProcessTask")
                logger.info("任务已停止: %s", task_name)
                return True, "任务已停止"
            else:
                raise NotImplementedError(f"不支持的类型{task_ops}")

    def monitor(self):
        logger.info("任务监控线程开始运行")
        try:
            duration = 5  # seconds
            while self._monitor_event.is_set():
                if not self.running_tasks:
                    time.sleep(duration)
                    continue

                # 定时重启(仅关闭游戏)
                if "AutoBossProcessTask" in self.running_tasks and self.restart_duration:
                    if not self.restart_time:
                        self.restart_time = time.monotonic()
                    elif time.monotonic() - self.restart_time > self.restart_duration:
                        self.close_game()
                        self.restart_time = time.monotonic()
                        time.sleep(5)

                # 检查游戏存活状态(重启游戏)
                self._monitor_game()

                # 检查任务存活状态
                for k, v in self.running_tasks.items():
                    if k == "MouseResetProcessTask":
                        continue
                    process_task, event = v
                    if not event.is_set():
                        continue
                    time.sleep(1)
                    if event.is_set() and not process_task.is_alive():
                        process_task.restart()

                time.sleep(duration)
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("任务监控线程异常")
            raise
        finally:
            logger.info("任务监控线程已停止")

    def _monitor_game(self):
        is_alive = False
        try:
            if hwnd_util.get_hwnd():
                is_alive = True
        except Exception:
            logger.exception("游戏不存在")
        if is_alive:
            return
        logger.info("开始重启游戏")
        self.restart_game()

    def restart_game(self) -> bool:
        start_time = time.monotonic()
        while time.monotonic() - start_time < 300:
            time.sleep(2)
            try:
                logger.info("先尝试关闭游戏")
                hwnd_util.force_close_process(hwnd_util.get_hwnd())
            except Exception:
                logger.exception("游戏不存在")
            time.sleep(5)
            game_path = self.context.config.app.AppPath
            subprocess.Popen(game_path, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            time.sleep(20)
            for i in range(10):
                try:
                    hwnd = hwnd_util.get_hwnd()
                    if hwnd:
                        logger.info("游戏已重启")
                        time.sleep(10)
                        hwnd_util.set_hwnd_left_top()
                        time.sleep(1)
                        return True
                except KeyboardInterrupt:
                    logger.warning("KeyboardInterrupt")
                    raise
                except Exception as e2:
                    logger.exception(e2)
                time.sleep(5)
        logger.error("游戏重启失败")
        return False

    def close_game(self):
        try:
            logger.info("定时关闭游戏")
            hwnd = hwnd_util.get_hwnd()
            hwnd_util.force_close_process(hwnd)
        except Exception:
            logger.exception("定时关闭游戏时异常")

    def get_restart_duration(self) -> int | None:
        # 定时重启开启
        if self.context.config.app.RestartWutheringWaves is True:
            restart_duration = self.context.config.app.RestartWutheringWavesTime
            if restart_duration < 10:
                logger.warning("定时重启周期过短: %ss, 自动关闭定时", restart_duration)
                return None
            else:
                logger.info("已开启定时重启，周期: %ss", restart_duration)
                return restart_duration
        return None


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
