import logging
import queue
import threading

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from src import application
from .gallery_interface import GalleryInterface
from ..common.signal_bus import signalBus

logger = logging.getLogger(__name__)


# class LogMonitor(QThread):
class LogListener:

    def __init__(self, log_queue, callback):
        super().__init__()
        self.log_queue = log_queue
        self.callback = callback
        self._running = True
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True

    def run(self):
        while self._running:
            try:
                log_text = self.log_queue.get(timeout=1)  # 设置超时，避免永久阻塞
                self.callback(log_text)
            except queue.Empty:
                continue  # 超时继续循环，及时感知运行状态
            except Exception:
                logger.exception("Unexpected exception")
                break

    def stop(self):
        self._running = False

    def start(self):
        self._thread.start()

    # def stop(self):
    #     self._running = False
    #     if self.isRunning():
    #         # self.quit()
    #         self.terminate()


class TerminalInterface(GalleryInterface):
    """ Terminal interface """

    def __init__(self, parent=None):
        self.logFIle = application.GUI.log_file
        self.logQueue = application.GUI.log_queue

        super().__init__(
            title=self.tr("Terminal"),
            subtitle=self.logFIle,
            parent=parent,
            needButtonLayout=False,
        )
        self.setObjectName('terminalInterface')

        self.textEdit = QTextEdit()
        self.textEdit.setStyleSheet("font: 14px 'Microsoft YaHei Mono'; background-color: transparent; ")

        self.logListener = LogListener(self.logQueue, self.append_log)
        self.logListener.start()

        self.__initWidget()

    def __initWidget(self):
        self.textEdit.setReadOnly(True)

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.vBoxLayout.addWidget(self.textEdit)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        signalBus.closeSignal.connect(self.stopLogListener)

    def append_log(self, text):
        # 获取当前光标
        cursor = self.textEdit.textCursor()
        # 判断是否在底部
        is_at_bottom = cursor.atBlockEnd()
        # 添加新日志
        self.textEdit.append(text)
        # 如果光标原本在底部，就自动滚动
        if is_at_bottom:
            cursor = self.textEdit.textCursor()
            cursor.movePosition(QTextCursor.End)  # 修改为 QTextCursor.End
            self.textEdit.setTextCursor(cursor)

    def stopLogListener(self):
        self.logListener.stop()
