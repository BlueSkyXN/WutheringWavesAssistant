import logging
import queue
import threading

from PySide6.QtGui import Qt, QColor
from PySide6.QtWidgets import QTextEdit, QVBoxLayout
from qfluentwidgets import SimpleCardWidget

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


class TerminalCard(SimpleCardWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.textEdit = QTextEdit()

        self.vBoxLayout = QVBoxLayout(self)

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(10, 6, 10, 6)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)

        self.vBoxLayout.addWidget(self.textEdit)
        # self.vBoxLayout.addStretch(1)

        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName('textEdit')

        # self.levelName_color_mapping = {
        #     "": "green",
        #     "": "yellow",
        #     "": "red",
        # }

    def append_log(self, emit_msg):
        # 获取当前的滚动条位置
        scrollbar = self.textEdit.verticalScrollBar()
        # 判断滚动条是否在最底部
        is_at_bottom = scrollbar.value() == scrollbar.maximum()

        level_name, msg = emit_msg
        if level_name in ["ERROR", "WARN", "WARNING", "DEBUG"]:
            if level_name == "ERROR":
                color = QColor(255, 100, 100)
            elif level_name == "WARNING" or level_name == "WARN":
                # color = QColor(200, 200, 0)
                color = QColor(184, 134, 11)
            else:  # level_name == "DEBUG":
                color = QColor(100, 255, 100)
            formatted_msg = rf"<font color='{color.name()}'>{msg}</font>"
            self.textEdit.append(formatted_msg)
        else:
            # 添加文本
            formatted_msg = rf"<span>{msg}</span>"  # 也用html，防止被染色
            self.textEdit.append(formatted_msg)

        # 如果原本在底部，添加文本后跳到最底部
        if is_at_bottom:
            scrollbar.setValue(scrollbar.maximum())


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

        # self.textEdit = QTextEdit()
        self.terminalCard = TerminalCard(self)
        self.logListener = LogListener(self.logQueue, signalBus.logQueueSignal.emit)
        self.logListener.start()

        self.__initWidget()

    def __initWidget(self):
        # self.textEdit.setObjectName("textEdit")
        # self.textEdit.setReadOnly(True)
        # StyleSheet.TERMINAL_INTERFACE.apply(self)

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        # self.vBoxLayout.addWidget(self.textEdit)
        self.vBoxLayout.addWidget(self.terminalCard)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        signalBus.closeSignal.connect(self.stopLogListener)
        signalBus.logQueueSignal.connect(self.terminalCard.append_log)

    # def append_log(self, text):
    #     # 获取当前的滚动条位置
    #     scrollbar = self.textEdit.verticalScrollBar()
    #     # 判断滚动条是否在最底部
    #     is_at_bottom = scrollbar.value() == scrollbar.maximum()
    #     # 添加文本
    #     self.textEdit.append(text)
    #     # 如果原本在底部，添加文本后跳到最底部
    #     if is_at_bottom:
    #         scrollbar.setValue(scrollbar.maximum())

    def stopLogListener(self):
        self.logListener.stop()
