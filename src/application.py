import logging

from src.config import logging_config, gui_config
from src.controller.main_controller import MainController
from src.core import environs
from src.util import uac_util

logger = logging.getLogger(__name__)

if uac_util.is_admin():
    logger.debug("管理员身份运行中")
else:
    logger.error("请以管理员身份运行！")


def run():
    from src.gui.common.globals import globalSignal, globalParam

    # 启动后台
    server = MainController()

    # 设置gui需要用到的参数
    globalParam.logFile = environs.get_log_path()
    globalParam.logQueue = logging_config.get_log_queue()
    globalParam.gamePath = gui_config.ParamConfig.get_default_game_path()

    # 前端信号绑定后端函数
    globalSignal.executeTaskSignal.connect(server.execute)
    globalSignal.closeMainWindowSignal.connect(server.stop)
    globalSignal.paramConfigPathSignal.connect(server.set_param_config_path)  # 动态告诉后端配置文件的路径，要在emit前绑定好

    # 启动qt
    from src.gui.gui import wwa
    wwa()
