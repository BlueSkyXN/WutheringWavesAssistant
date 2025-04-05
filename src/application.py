import logging

from src.config import logging_config
from src.controller.main_controller import MainController
from src.core import environs
from src.gui.gui import GuiController, wwa
from src.util import uac_util

logger = logging.getLogger(__name__)

if uac_util.is_admin():
    logger.debug("管理员身份运行中")
else:
    logger.error("请以管理员身份运行！")

APPLICATION = MainController()
GUI = GuiController()

GUI.log_file = environs.get_log_path()
GUI.log_queue = logging_config.get_log_queue()

# 前端连接信号到后端函数
GUI.task_run_requested.connect(APPLICATION.execute)


def run():
    wwa()
# https://kekee000.github.io/fonteditor/
# Fluentlcon.MUTE
# Speaker 1
# Speaker Off
# Window Console
# Cellular Off