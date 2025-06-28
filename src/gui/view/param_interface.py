# coding:utf-8
import logging
from typing import Union, List

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor, QIntValidator
from PySide6.QtWidgets import QWidget, QLabel, QFileDialog, QFrame, QVBoxLayout, QButtonGroup, QHBoxLayout, QPushButton, \
    QApplication, QSizePolicy
from qfluentwidgets import FluentIcon as FIF, OptionsSettingCard, SwitchSettingCard, SwitchButton, IndicatorPosition
from qfluentwidgets import InfoBar
from qfluentwidgets import (SettingCardGroup, ScrollArea,
                            ExpandLayout, ExpandSettingCard, FluentIconBase,
                            OptionsConfigItem, CheckBox, ExpandGroupSettingCard, RadioButton, MaskDialogBase,
                            SingleDirectionScrollArea, PrimaryPushButton, FluentStyleSheet,
                            LineEdit, SettingCard, ComboBox, ConfigItem,
                            PushButton, ToolButton, MessageBox)

from ..common.config import paramConfig, BossNameEnum
from ..common.globals import globalParam
from ..common.style_sheet import StyleSheet

logger = logging.getLogger(__name__)


class TimeLineEdit(LineEdit):
    """ Color line edit """

    def __init__(self, minimum, maximum: int, parent=None):
        super().__init__(parent)
        # self.setText(str(value))
        self.setFixedSize(136, 33)
        self.setClearButtonEnabled(True)
        self.setValidator(QIntValidator(minimum, maximum, self))


class TimeDialog(MaskDialogBase):
    """ Color dialog """

    valueChanged = Signal(list)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.scrollArea = SingleDirectionScrollArea(self.widget)
        self.scrollWidget = QWidget(self.scrollArea)

        self.buttonGroup = QFrame(self.widget)
        self.yesButton = PrimaryPushButton(self.tr('OK'), self.buttonGroup)
        self.cancelButton = QPushButton(self.tr('Cancel'), self.buttonGroup)

        self.titleLabel = QLabel(title, self.scrollWidget)

        self.redLabel = QLabel(self.tr('时'), self.scrollWidget)
        self.greenLabel = QLabel(self.tr('分'), self.scrollWidget)
        self.blueLabel = QLabel(self.tr('秒'), self.scrollWidget)
        self.redLineEdit = TimeLineEdit(0, 999, self.scrollWidget)
        self.greenLineEdit = TimeLineEdit(0, 999999, self.scrollWidget)
        self.blueLineEdit = TimeLineEdit(0, 999999999, self.scrollWidget)

        self.vBoxLayout = QVBoxLayout(self.widget)

        self.__initWidget()

    def __initWidget(self):
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setViewportMargins(48, 24, 0, 24)
        self.scrollArea.setWidget(self.scrollWidget)

        # self.widget.setMaximumSize(488, 696)
        # self.widget.resize(488, 696)
        # self.scrollWidget.resize(440, 560)
        self.widget.setMaximumSize(488, 296 + 25)
        self.widget.resize(488, 296 + 25)
        self.scrollWidget.resize(440, 160 + 25)
        self.buttonGroup.setFixedSize(486, 81)
        self.yesButton.setFixedWidth(216)
        self.cancelButton.setFixedWidth(216)

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 80))
        self.setMaskColor(QColor(0, 0, 0, 76))

        self.__setQss()
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.redLineEdit.move(0, 26 + 30)
        self.greenLineEdit.move(0, 70 + 30)
        self.blueLineEdit.move(0, 115 + 30)
        self.redLabel.move(144, 34 + 30)
        self.greenLabel.move(144, 78 + 30)
        self.blueLabel.move(144, 124 + 30)

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addWidget(self.scrollArea, 1)
        self.vBoxLayout.addWidget(self.buttonGroup, 0, Qt.AlignBottom)

        self.yesButton.move(24, 25)
        self.cancelButton.move(250, 25)

    def __setQss(self):
        self.titleLabel.setObjectName('titleLabel')
        self.yesButton.setObjectName('yesButton')
        self.cancelButton.setObjectName('cancelButton')
        self.buttonGroup.setObjectName('buttonGroup')
        FluentStyleSheet.COLOR_DIALOG.apply(self)
        self.titleLabel.adjustSize()

    def __onYesButtonClicked(self):
        """ yes button clicked slot """
        try:
            hours = int(self.redLineEdit.text().strip())
        except ValueError:
            hours = 0
        try:
            minutes = int(self.greenLineEdit.text().strip())
        except ValueError:
            minutes = 0
        try:
            seconds = int(self.blueLineEdit.text().strip())
        except ValueError:
            seconds = 0
        if hours * 3600 + minutes * 60 + seconds >= 60:
            self.accept()
            self.valueChanged.emit([hours, minutes, seconds])
        else:
            logger.warning("定时重启游戏时间不可小于60秒")

    def updateStyle(self):
        """ update style sheet """
        self.setStyle(QApplication.style())
        self.titleLabel.adjustSize()
        self.redLabel.adjustSize()
        self.greenLabel.adjustSize()
        self.blueLabel.adjustSize()

    def showEvent(self, e):
        self.updateStyle()
        super().showEvent(e)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        self.cancelButton.clicked.connect(self.reject)
        self.yesButton.clicked.connect(self.__onYesButtonClicked)


class AutoRestartPeriodSettingCard(ExpandGroupSettingCard):
    """ Custom Value setting card """

    autoRestartPeriodChanged = Signal(int)

    def __init__(self, configItem: ConfigItem, icon: Union[str, QIcon, FluentIconBase], title: str,
                 content=None, parent=None):
        super().__init__(icon, title, content, parent=parent)
        # self.enableAlpha = enableAlpha
        self.configItem = configItem
        self.defaultValue = configItem.defaultValue
        self.customValue = paramConfig.get(configItem)
        self.customValueLast = None if self.customValue == self.defaultValue else self.customValue

        self.choiceLabel = QLabel(self)
        # self.choiceLabel.setStyleSheet("""
        #     background-color: lightblue;  /* 背景颜色 */
        #     border-radius: 1px;           /* 可选，圆角边框 */
        # """)

        self.radioWidget = QWidget(self.view)
        self.radioLayout = QVBoxLayout(self.radioWidget)
        self.defaultRadioButton = RadioButton(
            self.tr('默认关闭'), self.radioWidget)
        # self.tr('Default Close'), self.radioWidget)
        self.customRadioButton = RadioButton(
            self.tr('自定义时间'), self.radioWidget)
        # self.tr('Custom Time'), self.radioWidget)
        self.buttonGroup = QButtonGroup(self)

        self.customValueWidget = QWidget(self.view)
        self.customValueLayout = QHBoxLayout(self.customValueWidget)
        self.customLabel = QLabel(
            self.tr('自定义时间'), self.customValueWidget)
        self.chooseTimeButton = QPushButton(
            self.tr('设置时间'), self.customValueWidget)

        self.__initWidget()

    def __initWidget(self):
        self.__initLayout()

        if self.defaultValue != self.customValue:
            self.customRadioButton.setChecked(True)
            self.chooseTimeButton.setEnabled(True)
            self._updateChoiceLabel(self.customValue)
        else:
            self.defaultRadioButton.setChecked(True)
            self.chooseTimeButton.setEnabled(False)
            self._updateChoiceLabel(self.defaultValue)

        # self.choiceLabel.setText(self.buttonGroup.checkedButton().text())
        self.choiceLabel.adjustSize()

        self.choiceLabel.setObjectName("titleLabel")
        self.customLabel.setObjectName("titleLabel")
        self.chooseTimeButton.setObjectName('chooseTimeButton')

        self.buttonGroup.buttonClicked.connect(self.__onRadioButtonClicked)
        self.chooseTimeButton.clicked.connect(self.__showChooseTimeDialog)

    def __initLayout(self):
        self.addWidget(self.choiceLabel)

        self.radioLayout.setSpacing(19)
        self.radioLayout.setAlignment(Qt.AlignTop)
        self.radioLayout.setContentsMargins(48, 18, 0, 18)
        self.buttonGroup.addButton(self.customRadioButton)
        self.buttonGroup.addButton(self.defaultRadioButton)
        self.radioLayout.addWidget(self.defaultRadioButton)
        self.radioLayout.addWidget(self.customRadioButton)
        self.radioLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        self.customValueLayout.setContentsMargins(48, 18, 44, 18)
        self.customValueLayout.addWidget(self.customLabel, 0, Qt.AlignLeft)
        self.customValueLayout.addWidget(self.chooseTimeButton, 0, Qt.AlignRight)
        self.customValueLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.addGroupWidget(self.radioWidget)
        self.addGroupWidget(self.customValueWidget)

    def __onRadioButtonClicked(self, button: RadioButton):
        """ radio button clicked slot """
        # if button.text() == self.choiceLabel.text():
        #     return

        # self.choiceLabel.setText(button.text())
        # self.choiceLabel.adjustSize()

        if button is self.defaultRadioButton:
            if self.choiceLabel.text() != button.text():
                self.choiceLabel.setText(button.text())
                self.choiceLabel.adjustSize()  # 此处设置相同的值label文本会置顶bug
            self.chooseTimeButton.setDisabled(True)
            paramConfig.set(self.configItem, self.defaultValue)
            if self.defaultValue != self.customValue:
                self.autoRestartPeriodChanged.emit(self.defaultValue)
        else:
            if self.customValueLast is not None:
                self.customValue = self.customValueLast
                self._updateChoiceLabel(self.customValue)
            self.chooseTimeButton.setDisabled(False)
            paramConfig.set(self.configItem, self.customValue)
            if self.defaultValue != self.customValue:
                self.autoRestartPeriodChanged.emit(self.customValue)

    def __showChooseTimeDialog(self):
        """ show color dialog """
        w = TimeDialog(self.tr('设置时间'), self.window())
        w.valueChanged.connect(self.__onCustomValueChanged)
        w.exec()

    def _updateChoiceLabel(self, value):
        if not value or value == self.defaultValue:
            self.choiceLabel.setText(self.defaultRadioButton.text())
        else:
            restartPeriod = value.split("#")
            template = self.tr("Restart every {hours} hours, {minutes} minutes, and {seconds} seconds")
            text = template.format(hours=restartPeriod[0], minutes=restartPeriod[1], seconds=restartPeriod[2])
            logger.debug(text)
            self.choiceLabel.setText(text)
        self.choiceLabel.adjustSize()

    def __onCustomValueChanged(self, value: list[int]):
        """ custom color changed slot """
        if not value:
            return
        strValue = "#".join(map(str, value))
        paramConfig.set(self.configItem, strValue)
        self.customValue = strValue
        self.customValueLast = strValue
        self._updateChoiceLabel(strValue)
        self.autoRestartPeriodChanged.emit(strValue)


class AutoCombatSwitchSettingCard(SettingCard):
    """ Setting card with switch button """

    checkedChanged = Signal(bool)

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, content=None,
                 configItem: ConfigItem = None, parent=None):
        """
        Parameters
        ----------
        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        configItem: ConfigItem
            configuration item operated by the card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.switchButton = SwitchButton(
            self.tr('Off'), self, IndicatorPosition.RIGHT)

        if configItem:
            self.setValue(paramConfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        """ switch button checked state changed slot """
        self.setValue(isChecked)
        self.checkedChanged.emit(isChecked)

    def setValue(self, isChecked: bool):
        if self.configItem:
            paramConfig.set(self.configItem, isChecked)

        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(
            self.tr('On') if isChecked else self.tr('Off'))

    def setChecked(self, isChecked: bool):
        self.setValue(isChecked)

    def isChecked(self):
        return self.switchButton.isChecked()


class ComboSequenceDialog(MaskDialogBase):
    valueChanged = Signal(list)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.vBoxLayout = QVBoxLayout(self.widget)

        self.titleLabel = QLabel(title, self.widget)
        self.contentLabel = QLabel(
            "逗号分隔, e,q,r为技能, l(小写L)为向后闪避, a为普攻(默认连点0.3秒), 数字为间隔时间,a~0.5为普攻按下0.5秒,a(0.5)为连续普攻0.5秒，摩托车短按请用q~0.1",
            self.widget)

        self.comboNameGroup = QHBoxLayout(self.widget)
        self.comboNameLabel = QLabel(self.tr('备注: '), self.widget)
        self.comboNameLineEdit = LineEdit(self.widget)

        self.comboSeqGroup = QHBoxLayout(self.widget)
        self.comboSeqLabel = QLabel(self.tr('连招: '), self.widget)
        self.comboSeqLineEdit = LineEdit(self.widget)

        self.buttonGroup = QFrame(self.widget)
        self.yesButton = PrimaryPushButton(self.tr('OK'), self.buttonGroup)
        self.cancelButton = QPushButton(self.tr('Cancel'), self.buttonGroup)

        self.__initWidget()

    def __initWidget(self):
        self.__setQss()
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.comboNameGroup.addWidget(self.comboNameLabel)
        self.comboNameGroup.addWidget(self.comboNameLineEdit)
        self.comboSeqGroup.addWidget(self.comboSeqLabel)
        self.comboSeqGroup.addWidget(self.comboSeqLineEdit)

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.contentLabel)
        self.vBoxLayout.addLayout(self.comboNameGroup)
        self.vBoxLayout.addLayout(self.comboSeqGroup)
        self.vBoxLayout.addWidget(self.buttonGroup, Qt.AlignBottom)

    def __setQss(self):
        # self.editLabel.setObjectName('editLabel')
        self.titleLabel.setObjectName('titleLabel')
        self.yesButton.setObjectName('yesButton')
        self.cancelButton.setObjectName('cancelButton')
        self.buttonGroup.setObjectName('buttonGroup')

    def __onYesButtonClicked(self):
        """ yes button clicked slot """
        pass

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        self.cancelButton.clicked.connect(self.reject)
        self.yesButton.clicked.connect(self.__onYesButtonClicked)


class ComboSequenceSettingCard(ExpandGroupSettingCard):
    """ Custom Value setting card """

    autoRestartPeriodChanged = Signal(int)

    def __init__(self, configItem: ConfigItem, icon: Union[str, QIcon, FluentIconBase], title: str,
                 content=None, parent=None):
        super().__init__(icon, title, content, parent=parent)
        # self.enableAlpha = enableAlpha
        self.configItem = configItem
        self.defaultValue = configItem.defaultValue
        self.customValue = paramConfig.get(configItem)
        self.customValueLast = None if self.customValue == self.defaultValue else self.customValue

        self.choiceLabel = QLabel(self)

        self.radioWidget = QWidget(self.view)
        self.radioLayout = QVBoxLayout(self.radioWidget)
        self.defaultRadioButton = RadioButton(
            self.tr('默认'), self.radioWidget)
        # self.tr('Default Close'), self.radioWidget)
        self.customRadioButton = RadioButton(
            self.tr('自定义连招'), self.radioWidget)
        # self.tr('Custom Time'), self.radioWidget)
        self.buttonGroup = QButtonGroup(self)

        self.customValueWidget = QWidget(self.view)
        self.customValueLayout = QHBoxLayout(self.customValueWidget)
        self.customLabel = QLabel(
            self.tr('自定义连招'), self.customValueWidget)
        self.chooseTimeButton = QPushButton(
            self.tr('设置连招'), self.customValueWidget)

        self.__initWidget()

    def __initWidget(self):
        self.__initLayout()

        if self.defaultValue != self.customValue:
            self.customRadioButton.setChecked(True)
            self.chooseTimeButton.setEnabled(True)
            self._updateChoiceLabel(self.customValue)
        else:
            self.defaultRadioButton.setChecked(True)
            self.chooseTimeButton.setEnabled(False)
            self._updateChoiceLabel(self.defaultValue)

        # self.choiceLabel.setText(self.buttonGroup.checkedButton().text())
        self.choiceLabel.adjustSize()

        self.choiceLabel.setObjectName("titleLabel")
        self.customLabel.setObjectName("titleLabel")
        self.chooseTimeButton.setObjectName('chooseTimeButton')

        self.buttonGroup.buttonClicked.connect(self.__onRadioButtonClicked)
        self.chooseTimeButton.clicked.connect(self.__showChooseTimeDialog)

    def __initLayout(self):
        self.addWidget(self.choiceLabel)

        self.radioLayout.setSpacing(19)
        self.radioLayout.setAlignment(Qt.AlignTop)
        self.radioLayout.setContentsMargins(48, 18, 0, 18)
        self.buttonGroup.addButton(self.customRadioButton)
        self.buttonGroup.addButton(self.defaultRadioButton)
        self.radioLayout.addWidget(self.defaultRadioButton)
        self.radioLayout.addWidget(self.customRadioButton)
        self.radioLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        self.customValueLayout.setContentsMargins(48, 18, 44, 18)
        self.customValueLayout.addWidget(self.customLabel, 0, Qt.AlignLeft)
        self.customValueLayout.addWidget(self.chooseTimeButton, 0, Qt.AlignRight)
        self.customValueLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.addGroupWidget(self.radioWidget)
        self.addGroupWidget(self.customValueWidget)

    def __onRadioButtonClicked(self, button: RadioButton):
        """ radio button clicked slot """
        # if button.text() == self.choiceLabel.text():
        #     return

        # self.choiceLabel.setText(button.text())
        # self.choiceLabel.adjustSize()

        if button is self.defaultRadioButton:
            if self.choiceLabel.text() != button.text():
                self.choiceLabel.setText(button.text())
                self.choiceLabel.adjustSize()  # 此处设置相同的值label文本会置顶bug
            self.chooseTimeButton.setDisabled(True)
            paramConfig.set(self.configItem, self.defaultValue)
            if self.defaultValue != self.customValue:
                self.autoRestartPeriodChanged.emit(self.defaultValue)
        else:
            if self.customValueLast is not None:
                self.customValue = self.customValueLast
                self._updateChoiceLabel(self.customValue)
            self.chooseTimeButton.setDisabled(False)
            paramConfig.set(self.configItem, self.customValue)
            if self.defaultValue != self.customValue:
                self.autoRestartPeriodChanged.emit(self.customValue)

    def __showChooseTimeDialog(self):
        """ show color dialog """
        # w = ComboSequenceDialog(self.tr('设置连招'), self.window())
        # w.valueChanged.connect(self.__onCustomValueChanged)
        # w.exec()
        title = 'Are you sure you want to delete the folder?'
        content = """If you delete the "Music" folder from the list, the folder will no longer appear in the list, but will not be deleted."""
        # w = MessageDialog(title, content, self)   # Win10 style message box
        w = MessageBox(title, content, self)

        # close the message box when mask is clicked
        w.setClosableOnMaskClicked(True)

        w.exec()

    def _updateChoiceLabel(self, value):
        if not value or value == self.defaultValue:
            self.choiceLabel.setText(self.defaultRadioButton.text())
        else:
            restartPeriod = value.split("#")
            template = self.tr("Restart every {hours} hours, {minutes} minutes, and {seconds} seconds")
            text = template.format(hours=restartPeriod[0], minutes=restartPeriod[1], seconds=restartPeriod[2])
            logger.debug(text)
            self.choiceLabel.setText(text)
        self.choiceLabel.adjustSize()

    def __onCustomValueChanged(self, value: list[int]):
        """ custom color changed slot """
        if not value:
            return
        strValue = "#".join(map(str, value))
        paramConfig.set(self.configItem, strValue)
        self.customValue = strValue
        self.customValueLast = strValue
        self._updateChoiceLabel(strValue)
        self.autoRestartPeriodChanged.emit(strValue)


class GamePathSettingCard(ExpandGroupSettingCard):
    """ Custom Value setting card """

    gamePathChanged = Signal(int)

    def __init__(self, configItem: ConfigItem, icon: Union[str, QIcon, FluentIconBase], title: str,
                 content=None, parent=None):
        super().__init__(icon, title, content, parent=parent)
        self.configItem = configItem
        self.defaultValue = configItem.defaultValue
        self.customValue = paramConfig.get(configItem)
        self.customValueLast = None if self.customValue == self.defaultValue else self.customValue

        self.choiceLabel = QLabel(self)

        self.radioWidget = QWidget(self.view)
        self.radioLayout = QVBoxLayout(self.radioWidget)

        if globalParam.gamePath:
            template = self.tr("默认自动获取。例: {gamePath}")
            gamePath = globalParam.gamePath.strip().replace("\\", "/").replace("\\\\", "/")
            gamePathText = template.format(gamePath=gamePath)
        else:
            gamePathText = self.tr("默认自动获取。当前未找到游戏路径，请手动设置")

        self.defaultRadioButton = RadioButton(gamePathText, self.radioWidget)
        # self.tr('Default Close'), self.radioWidget)
        self.customRadioButton = RadioButton(
            self.tr('自定义路径，适合多游戏，同时运行多个游戏时优先操控该路径下的游戏窗口'), self.radioWidget)
        # self.tr('Custom Time'), self.radioWidget)
        self.buttonGroup = QButtonGroup(self)

        self.customValueWidget = QWidget(self.view)
        self.customValueLayout = QHBoxLayout(self.customValueWidget)
        self.customLabel = QLabel(
            # self.tr('自定义路径'), self.customValueWidget)
            self.tr(f"脚本优先操控运行中的游戏窗口，不管这个参数，多开或游戏没启动时才看选了哪个"), self.customValueWidget)
        # self.customLabel.setEnabled(False)
        # self.chooseTimeButton = QPushButton(
        #     self.tr('设置路径'), self.customValueWidget)
        self.chooseTimeButton = PushButton(
            self.tr(f'Add \"Wuthering Waves.exe\"'), self, FIF.FOLDER_ADD)

        self.__initWidget()

    def __initWidget(self):
        self.__initLayout()

        if self.defaultValue != self.customValue:
            # self.customLabel.setEnabled(True)
            self.customRadioButton.setChecked(True)
            self.chooseTimeButton.setEnabled(True)
            self._updateChoiceLabel(self.customValue)
        else:
            self.defaultRadioButton.setChecked(True)
            self.chooseTimeButton.setEnabled(False)
            self._updateChoiceLabel(self.defaultValue)

        # self.choiceLabel.setText(self.buttonGroup.checkedButton().text())
        self.choiceLabel.adjustSize()

        self.choiceLabel.setObjectName("titleLabel")
        self.customLabel.setObjectName("titleLabel")
        self.chooseTimeButton.setObjectName('chooseTimeButton')

        self.buttonGroup.buttonClicked.connect(self.__onRadioButtonClicked)
        self.chooseTimeButton.clicked.connect(self.__showFolderDialog)

    def __initLayout(self):
        self.addWidget(self.choiceLabel)

        self.radioLayout.setSpacing(19)
        self.radioLayout.setAlignment(Qt.AlignTop)
        self.radioLayout.setContentsMargins(48, 18, 0, 18)
        self.buttonGroup.addButton(self.customRadioButton)
        self.buttonGroup.addButton(self.defaultRadioButton)
        self.radioLayout.addWidget(self.defaultRadioButton)
        self.radioLayout.addWidget(self.customRadioButton)
        self.radioLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        self.customValueLayout.setContentsMargins(48, 18, 44, 18)
        self.customValueLayout.addWidget(self.customLabel, 0, Qt.AlignLeft)
        self.customValueLayout.addWidget(self.chooseTimeButton, 0, Qt.AlignRight)
        self.customValueLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.addGroupWidget(self.radioWidget)
        self.addGroupWidget(self.customValueWidget)

    def __onRadioButtonClicked(self, button: RadioButton):
        """ radio button clicked slot """
        # if button.text() == self.choiceLabel.text():
        #     return

        # self.choiceLabel.setText(button.text())
        # self.choiceLabel.adjustSize()

        if button is self.defaultRadioButton:
            # self.customLabel.setEnabled(False)
            if self.choiceLabel.text() != self.defaultValue:
                self.choiceLabel.setText(self.tr(self.defaultValue))
                self.choiceLabel.adjustSize()
            self.chooseTimeButton.setDisabled(True)
            paramConfig.set(self.configItem, self.defaultValue)
            if self.defaultValue != self.customValue:
                self.gamePathChanged.emit(self.defaultValue)
        else:
            # self.customLabel.setEnabled(True)
            if self.customValueLast is not None:
                self.customValue = self.customValueLast
                self._updateChoiceLabel(self.customValue)
            self.chooseTimeButton.setDisabled(False)
            paramConfig.set(self.configItem, self.customValue)
            if self.defaultValue != self.customValue:
                self.gamePathChanged.emit(self.customValue)

    # def __showChooseTimeDialog(self):
    #     """ show color dialog """
    #     w = TimeDialog(self.tr('设置时间'), self.window())
    #     w.valueChanged.connect(self.__onCustomValueChanged)
    #     w.exec()

    def __showFolderDialog(self):
        """ show folder dialog """
        # folder = QFileDialog.getExistingDirectory(
        #     self, self.tr("Choose folder"), self._dialogDirectory)
        # 打开文件对话框，选择文件
        folder, _ = QFileDialog.getOpenFileName(
            self,
            "Choose \"Wuthering Waves.exe\"",
            "./",
            "Executable Files (*.exe);;All Files (*)"  # 过滤器：只显示 .exe 文件及所有文件
            # filter="Wuthering Waves (Wuthering Waves.exe);;Executable Files (*.exe);;All Files (*)"
        )
        if folder:
            logger.debug(f"Selected file: {folder}")
        else:
            logger.debug("No file selected.")

        if not folder or folder == self.customValue:
            return

        # self.__addFolderItem(folder)
        # self.folders.append(folder)
        # paramConfig.set(self.configItem, self.folders)
        # self.folderChanged.emit(self.folders)

        self.__onCustomValueChanged(folder)

    def _updateChoiceLabel(self, value):
        if not value or value == self.defaultValue:
            self.choiceLabel.setText(self.tr(self.defaultValue))
        else:
            logger.debug(value)
            self.choiceLabel.setText(value)
        self.choiceLabel.adjustSize()

    def __onCustomValueChanged(self, value):
        """ custom color changed slot """
        if not value:
            return
        paramConfig.set(self.configItem, value)
        self.customValue = value
        self.customValueLast = value
        self._updateChoiceLabel(value)
        self.gamePathChanged.emit(value)


class ClickableButton(QWidget):
    def __init__(self, button, parent=None):
        super().__init__(parent)
        self.button = button
        self.layout = QHBoxLayout(self)
        # self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setContentsMargins(0, 1, 0, 6)
        # self.layout.setAlignment(Qt.AlignVCenter)
        self.layout.addWidget(self.button)
        # self.setStyleSheet("background: rgba(0, 255, 0, 0.1);")

    def mousePressEvent(self, event):
        # 点整个行区域都能切换 checkbox 状态
        self.button.toggle()
        super().mousePressEvent(event)


class BossNameOptionsSettingCard(ExpandSettingCard):
    """ setting card with a group of options """

    optionChanged = Signal(OptionsConfigItem)

    def __init__(self, configItem, icon: Union[str, QIcon, FluentIconBase], title, content=None, texts=None,
                 parent=None):
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.configName = configItem.name  # 在配置文件中的key
        self.choiceLabel = QLabel(self)  # 右上角展示选中的枚举名称（枚举的value）
        self.buttonGroup = []  # 存储所有的枚举按钮对象
        self.choiceBosses = []  # 存储被选中的枚举

        self.choiceLabel.setObjectName("titleLabel")
        self.addWidget(self.choiceLabel)

        # create buttons
        # self.viewLayout.setSpacing(19)
        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(48, 18, 0, 18)
        for boss in BossNameEnum:
            button = CheckBox(boss.value, self.view)  # 按钮上展示枚举的value，即描述，可国际化
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # button.setStyleSheet("background: rgba(0, 255, 0, 0.1);")
            self.buttonGroup.append(button)
            self.viewLayout.addWidget(ClickableButton(button, self))
            button.setProperty(self.configName, boss)
            button.stateChanged.connect(
                lambda state, cb=button: self.__onButtonClicked(cb)
            )

        self._adjustViewSize()
        self.setValue(paramConfig.get(self.configItem), block_signal=True)  # 调取配置文件中的枚举名列表来初始化当前实例变量的值，并展示到页面上
        # configItem.valueChanged.connect(self.setValue) # 配置中的值被其他地方修改了，通知这个页面同步刷新

    def __onButtonClicked(self, button: CheckBox):  # 增量修改，全量刷新和保存
        """ button clicked slot """
        value = button.property(self.configName)  # 按钮绑定的是枚举对象
        self.updateChoiceBosses(value, button.isChecked())
        self.updateChoiceLabel()
        paramConfig.set(self.configItem, [item.name for item in self.choiceBosses])
        self.optionChanged.emit(self.configItem)

    def setValue(self, values, block_signal=False):  # 全量覆盖，全量刷新和保存
        """ select button according to the value """
        # if update_config:
        #     paramConfig.set(self.configItem, values) # 配置文件存的是字符串列表，枚举对象的name
        self.choiceBosses.clear()
        for button in self.buttonGroup:
            value = button.property(self.configName)  # 按钮绑定的是枚举对象
            # isChecked = value.name in values
            isChecked = value in values
            if block_signal:
                button.blockSignals(True)
                button.setChecked(isChecked)
                button.blockSignals(False)
            else:
                button.setChecked(isChecked)
            self.updateChoiceBosses(value, isChecked)  # 这个按钮是否选中，先更新实例变量
        self.updateChoiceLabel()  # 再一次将实例变量中维护的所选枚举值拼接，并展示到页面右上角

    def updateChoiceBosses(self, value: str | BossNameEnum, isChecked: bool):
        if isinstance(value, str):
            value = BossNameEnum[value]
        elif not isinstance(value, BossNameEnum):
            raise TypeError(f"value {value} is not BossNameEnum or str")
        if isChecked:
            if value not in self.choiceBosses:
                self.choiceBosses.append(value)
        else:
            try:
                self.choiceBosses.remove(value)
            except ValueError:
                pass

    def updateChoiceLabel(self):
        # 更新右上展示选择的枚举的值并翻译
        self.choiceLabel.setText(", ".join(self.tr(item.value) for item in self.choiceBosses))
        self.choiceLabel.adjustSize()


class BossLevelOptionsSettingCard(ExpandSettingCard):
    """ setting card with a group of options """

    optionChanged = Signal(OptionsConfigItem)

    def __init__(self, configItem, icon: Union[str, QIcon, FluentIconBase], title, content=None, texts=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.texts = texts or []
        self.configItem = configItem
        self.configName = configItem.name
        self.choiceLabel = QLabel(self)
        self.buttonGroup = QButtonGroup(self)

        self.choiceLabel.setObjectName("titleLabel")
        self.addWidget(self.choiceLabel)

        # create buttons
        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(48, 18, 0, 18)
        for text, option in zip(texts, configItem.options):
            button = RadioButton(text, self.view)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # button.setStyleSheet("background: rgba(0, 255, 0, 0.1);")
            self.buttonGroup.addButton(button)
            self.viewLayout.addWidget(ClickableButton(button, self))
            # self.viewLayout.addWidget(button)
            button.setProperty(self.configName, option)

        self._adjustViewSize()
        self.setValue(paramConfig.get(self.configItem))
        # configItem.valueChanged.connect(self.setValue)
        self.buttonGroup.buttonClicked.connect(self.__onButtonClicked)

    def __onButtonClicked(self, button: RadioButton):
        """ button clicked slot """
        if button.text() == self.choiceLabel.text():
            return

        value = button.property(self.configName)
        paramConfig.set(self.configItem, value)

        self.choiceLabel.setText(button.text())
        self.choiceLabel.adjustSize()
        self.optionChanged.emit(self.configItem)

    def setValue(self, value):
        """ select button according to the value """
        paramConfig.set(self.configItem, value)

        for button in self.buttonGroup.buttons():
            isChecked = button.property(self.configName) == value
            button.setChecked(isChecked)

            if isChecked:
                self.choiceLabel.setText(button.text())
                self.choiceLabel.adjustSize()


class ParamComboBoxSettingCard(SettingCard):
    """ Setting card with a combo box """

    def __init__(self, configItem: OptionsConfigItem, icon: Union[str, QIcon, FluentIconBase], title, content=None,
                 texts=None, parent=None):
        """
        Parameters
        ----------
        configItem: OptionsConfigItem
            configuration item operated by the card

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        texts: List[str]
            the text of items

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.comboBox = ComboBox(self)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.optionToText = {o: t for o, t in zip(configItem.options, texts)}
        for text, option in zip(texts, configItem.options):
            self.comboBox.addItem(text, userData=option)

        self.comboBox.setCurrentText(self.optionToText[paramConfig.get(configItem)])
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        configItem.valueChanged.connect(self.setValue)

    def _onCurrentIndexChanged(self, index: int):

        paramConfig.set(self.configItem, self.comboBox.itemData(index))

    def setValue(self, value):
        if value not in self.optionToText:
            return

        self.comboBox.setCurrentText(self.optionToText[value])
        paramConfig.set(self.configItem, value)


class FolderItem(QWidget):
    """ Folder item """

    removed = Signal(QWidget)

    def __init__(self, folder: str, parent=None):
        super().__init__(parent=parent)
        self.folder = folder
        self.hBoxLayout = QHBoxLayout(self)
        self.folderLabel = QLabel(folder, self)
        self.removeButton = ToolButton(FIF.CLOSE, self)

        self.removeButton.setFixedSize(39, 29)
        self.removeButton.setIconSize(QSize(12, 12))

        self.setFixedHeight(53)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.hBoxLayout.setContentsMargins(48, 0, 60, 0)
        self.hBoxLayout.addWidget(self.folderLabel, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.removeButton, 0, Qt.AlignRight)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)

        self.removeButton.clicked.connect(
            lambda: self.removed.emit(self))


class ParamInterface(ScrollArea):
    """ Config interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel(self.tr("Param"), self)

        # Task
        self.bossGroup = SettingCardGroup(
            self.tr('Boss Rush Parameters'), self.scrollWidget)

        self.bossNameCard = BossNameOptionsSettingCard(
            paramConfig.bossName,
            FIF.LABEL,
            # self.tr('选择刷哪些boss'),
            self.tr('Target Boss Names'),
            # self.tr("可任选，大世界的建议选三个循环刷，副本里的建议单刷"),
            self.tr("Choose any bosses, suggested: one for instances and nightmare, three for open world"),
            texts=None,
            parent=self.bossGroup
        )

        # self.bossLevelCard = ParamComboBoxSettingCard(
        #     paramConfig.bossLevel,
        #     FIF.LABEL,
        #     self.tr('Target Boss Level'),
        #     self.tr('Select the lowest boss level that can drop Echo'),
        #     texts=["40", "50", "60", "70", "80", "90", "Auto"],
        #     parent=self.bossGroup
        # )

        self.bossLevelCard = BossLevelOptionsSettingCard(
            paramConfig.bossLevel,
            FIF.LABEL,
            self.tr('Target Boss Level'),
            self.tr('Default auto is the lowest boss level that drops Echo; changing it makes it faster'),
            texts=["Lv 40", "Lv 50", "Lv 60", "Lv 70", "Lv 80", "Lv 90", "Auto"],
            parent=self.bossGroup
        )

        # self.comboSequenceCard = ComboSequenceSettingCard(
        #     paramConfig.comboSequence,
        #     FIF.CODE,
        #     # self.tr('定时重启游戏'),
        #     # self.tr('每隔一段时间重启一次游戏，仅对刷boss任务有效'),
        #     self.tr("Combo Sequence"),
        #     self.tr("释放技能顺序,逗号分隔,e,q,r为技能,l(小写L)为闪避, a为普攻(默认连点0.3秒),数字为间隔时间,a~0.5为普攻按下0.5秒,a(0.5)为连续普攻0.5秒，摩托车短按用q~0.1"),
        #     self.bossGroup
        # )

        self.autoRestartPeriodCard = AutoRestartPeriodSettingCard(
            paramConfig.autoRestartPeriod,
            FIF.STOP_WATCH,
            # self.tr('定时重启游戏'),
            # self.tr('每隔一段时间重启一次游戏，仅对刷boss任务有效'),
            self.tr("Scheduled Game Restart"),
            self.tr("Restart the game at regular intervals. This only applies to the Boss Rush task"),
            self.bossGroup
        )

        self.autoCombatCard = AutoCombatSwitchSettingCard(
            FIF.LABEL,
            self.tr('智能连招 测试V0.3 支持：守岸人、长离、今汐、安可、维里奈、椿、散华、卡提希娅，替代无效'),
            self.tr('默认关闭，此开关仅在测试阶段可见。征集角色账号包含：菲比、珂莱塔、洛可可、折枝、忌炎、布兰特，用于制作连招，在群里先@群主，借号有风险！请勿借与陌生人！'),
            configItem=paramConfig.autoCombat,
            parent=self.bossGroup
        )

        # game folders
        self.gameGroup = SettingCardGroup(
            self.tr("Game Parameters"), self.scrollWidget)

        self.gamePathCard = GamePathSettingCard(
            paramConfig.gamePath,
            FIF.FOLDER,
            self.tr("Installation Directory"),
            self.tr("If you play multiple games, configure this accordingly"),
            self.gameGroup
        )

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('paramInterface')

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')
        StyleSheet.SETTING_INTERFACE.apply(self)

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(36, 30)

        # add cards to group
        self.gameGroup.addSettingCard(self.gamePathCard)

        self.bossGroup.addSettingCard(self.bossNameCard)
        self.bossGroup.addSettingCard(self.bossLevelCard)
        # self.bossGroup.addSettingCard(self.comboSequenceCard)
        self.bossGroup.addSettingCard(self.autoCombatCard)
        self.bossGroup.addSettingCard(self.autoRestartPeriodCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)

        self.expandLayout.addWidget(self.bossGroup)
        self.expandLayout.addWidget(self.gameGroup)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.success(
            self.tr('Updated successfully'),
            self.tr('Configuration takes effect after restart'),
            duration=1500,
            parent=self
        )

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        # cfg.appRestartSig.connect(self.__showRestartTooltip)

        # # music in the pc
        # self.gamePathCard.clicked.connect(
        #     self.__onDownloadFolderCardClicked)
        pass
