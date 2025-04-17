from PySide6.QtCore import Signal, QObject


class GlobalSignal(QObject):
    """ Signal """
    closeMainWindowSignal = Signal()  # gui关闭信号，右上角的关闭
    executeTaskSignal = Signal(str, str)  # 提交运行任务，任务名 和 启动/停止
    paramConfigPathSignal = Signal(str)  # 参数配置文件的路径


class GlobalParam:

    def __init__(self):
        self.logFile = None
        self.logQueue = None
        self.gamePath = None  # winreg内游戏的路径


# 前后端交互专用信号和参数
globalSignal = GlobalSignal()
globalParam = GlobalParam()
