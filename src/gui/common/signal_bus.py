# coding: utf-8
from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """ Signal bus """

    switchToSampleCard = Signal(str, int)
    micaEnableChanged = Signal(bool)
    supportSignal = Signal()

    closeSignal = Signal()  # gui关闭信号，右上角的关闭
    logQueueSignal = Signal(str)  # 日志队列信号，表明队列有新日志


signalBus = SignalBus()
