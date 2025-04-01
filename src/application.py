import logging

from src.controller.main_controller import MainController
from src.gui.gui import GuiController, wwa
from src.util import uac_util

logger = logging.getLogger(__name__)

if uac_util.is_admin():
    logger.debug("管理员身份运行中")
else:
    logger.error("请以管理员身份运行！")

APPLICATION = MainController()
GUI = GuiController()

# 前端连接信号到后端函数
GUI.task_run_requested.connect(APPLICATION.execute)


def run():
    wwa()
