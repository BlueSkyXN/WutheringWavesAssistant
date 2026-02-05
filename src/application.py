import logging
import sys

from src import __version__
from src.config import logging_config, gui_config
from src.controller.main_controller import MainController
from src.core import environs
from src.util import windows_util

logger = logging.getLogger(__name__)


def before():
    if windows_util.is_admin():
        logger.debug("管理员身份运行中")
    else:
        logger.error("请以管理员身份运行！")
        windows_util.show_windows_notification("请以管理员身份运行！")
        sys.exit(0)


def gui_is_exist():
    windows_util.show_windows_notification("同一路径下只能启动一个实例！多开可拷贝一份代码到其他目录启动")
    sys.exit(0)


def run():
    logger.info(f"WWA v{__version__}, free and open-source")

    before()

    # 启动后台
    server = MainController()

    # 设置gui需要用到的参数
    from src.gui.common.globals import globalSignal, globalParam
    globalParam.logFile = environs.get_log_path()
    globalParam.logQueue = logging_config.get_log_queue()
    globalParam.gamePath = gui_config.ParamConfig.get_default_game_path()

    # 前端信号绑定后端函数
    globalSignal.executeTaskSignal.connect(server.execute)
    globalSignal.guiExistSignal.connect(gui_is_exist)
    globalSignal.closeMainWindowSignal.connect(server.stop)
    globalSignal.paramConfigPathSignal.connect(server.set_param_config_path)  # 动态告诉后端配置文件的路径，要在emit前绑定好
    globalSignal.guiWinId.connect(server.set_gui_win_id)

    # 启动qt
    from src.gui.gui import wwa
    wwa()
