import logging
import queue
import threading

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from src import application
from .gallery_interface import GalleryInterface
from ..common.signal_bus import signalBus

logger = logging.getLogger(__name__)


# class LogListener(QThread):
class LogListener:

    def __init__(self, log_queue, callback):
        super().__init__()
        self.log_queue = log_queue
        self.callback = callback
        self._running = threading.Event()
        self._running.set()
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True

    def run(self):
        while self._running.is_set():
            try:
                log_text = self.log_queue.get(timeout=1)  # 设置超时，避免永久阻塞
                if log_text is None:
                    continue
                self.callback(log_text)
            except queue.Empty:
                continue  # 超时继续循环，及时感知运行状态
            except Exception:
                logger.exception("Unexpected exception")
                break

    def stop(self):
        self._running.clear()
        self.log_queue.put(None)
        self.log_queue.put(None)
        self._thread.join(timeout=1.2)
        logger.info("日志监听已关闭")

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
        # self.textEdit.setStyleSheet("font: 14px 'Microsoft YaHei Mono'; background-color: transparent; ")
        self.textEdit.setObjectName("textEdit")

        self.logListener = LogListener(self.logQueue, signalBus.logQueueSignal.emit)
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
        signalBus.logQueueSignal.connect(self.append_log)

    def append_log(self, text):
        # 获取当前的滚动条位置
        scrollbar = self.textEdit.verticalScrollBar()
        # 判断滚动条是否在最底部
        is_at_bottom = scrollbar.value() == scrollbar.maximum()
        # 添加文本
        self.textEdit.append(text)
        # 如果原本在底部，添加文本后跳到最底部
        if is_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def stopLogListener(self):
        self.logListener.stop()
