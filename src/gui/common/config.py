# coding:utf-8
import json
import logging
import sys
from copy import deepcopy
from datetime import datetime
from enum import Enum, EnumMeta
from pathlib import Path
from typing import List

from PySide6.QtCore import QLocale, QObject, Signal
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, RangeConfigItem, RangeValidator,
                            FolderListValidator, Theme, FolderValidator, ConfigSerializer, EnumSerializer,
                            exceptionHandler, ConfigValidator)
from src import __version__
from src.gui.common.globals import globalSignal

logger = logging.getLogger(__name__)


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


class Config(QConfig):
    """ Config of application """

    # # folders
    # musicFolders = ConfigItem(
    #     "Folders", "LocalMusic", [], FolderListValidator())
    # downloadFolder = ConfigItem(
    #     "Folders", "Download", "app/download", FolderValidator())

    # main window
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)

    # # Material
    # blurRadius  = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

    # software update
    # checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", False, BoolValidator())
    checkUpdateAtStartUpV2 = ConfigItem("Update", "CheckUpdateAtStartUpV2", True, BoolValidator())


YEAR = datetime.now().year
AUTHOR = "wakening"
VERSION = __version__
HELP_URL = "https://github.com/wakening/WutheringWavesAssistant?tab=readme-ov-file#-%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97"
REPO_URL = "https://github.com/wakening/WutheringWavesAssistant"
EXAMPLE_URL = "https://github.com/wakening"
FEEDBACK_URL = "https://github.com/wakening/WutheringWavesAssistant/issues"
RELEASE_URL = "https://github.com/wakening/WutheringWavesAssistant/releases/latest"
ZH_SUPPORT_URL = "https://afdian.com/a/wakening"
EN_SUPPORT_URL = "https://afdian.com/a/wakening"
CHANGELOG_URL = "https://github.com/wakening/WutheringWavesAssistant/CHANGELOG.md" # TODO terminal

VERSION_URLS = [
    "https://ghfast.top/https://raw.githubusercontent.com/wakening/WutheringWavesAssistant/main/src/__init__.py",
    "https://cdn.jsdelivr.net/gh/wakening/WutheringWavesAssistant@main/src/__init__.py",
    "https://raw.githubusercontent.com/wakening/WutheringWavesAssistant/main/src/__init__.py",
]


cfg = Config()
cfg.themeMode.value = Theme.AUTO
# qconfig.load('temp/config/config.json', cfg)
_qconfigPath = str(Path(__file__).parent.parent.parent.parent.joinpath('temp/config/config.json'))
qconfig.load(_qconfigPath, cfg)


class BossNameEnum(Enum):
    Dreamless = "无妄者"
    FallacyOfNoReturn = "无归的谬误"
    LampylumenMyriad = "辉萤军势"
    BellBorneGeochelone = "鸣钟之龟"
    InfernoRider = "燎照之骑"
    ImpermanenceHeron = "无常凶鹭"
    MechAbomination = "聚械机偶"
    MourningAix = "哀声鸷"
    ThunderingMephis = "朔雷之鳞"
    TempestMephis = "云闪之鳞"
    FeilianBeringal = "飞廉之猩"
    Crownless = "无冠者"
    Jue = "角"
    SentryConstruct = "异构武装"
    Hecate = "赫卡忒"
    Lorelei = "罗蕾莱"
    DragonOfDirge = "叹息古龙"
    NightmareFeilianBeringal = "梦魇飞廉之猩"
    NightmareImpermanenceHeron = "梦魇无常凶鹭"
    NightmareTempestMephis = "梦魇云闪之鳞"
    NightmareThunderingMephis = "梦魇朔雷之鳞"
    NightmareCrownless = "梦魇无冠者"
    NightmareInfernoRider = "梦魇燎照之骑"
    NightmareMourningAix = "梦魇哀声鸷"
    NightmareLampylumenMyriad = "梦魇辉萤军势"
    Fleurdelys = "芙露德莉斯"
    NightmareKelpie = "梦魇凯尔匹"
    LionessOfGlory = "荣耀狮像"

    # Dreamless = ("无妄者", "Dreamless")
    # FallacyOfNoReturn = ("无归的谬误", "Fallacy of No Return")
    # LampylumenMyriad = ("辉萤军势", "Lampylumen Myriad")
    # BellBorneGeochelone = ("鸣钟之龟", "Bell-Borne Geochelone")
    # InfernoRider = ("燎照之骑", "Inferno Rider")
    # ImpermanenceHeron = ("无常凶鹭", "Impermanence Heron")
    # MechAbomination = ("聚械机偶", "Mech Abomination")
    # MourningAix = ("哀声鸷", "Mourning Aix")
    # ThunderingMephis = ("朔雷之鳞", "Thundering Mephis")
    # TempestMephis = ("云闪之鳞", "Tempest Mephis")
    # FeilianBeringal = ("飞廉之猩", "Feilian Beringal")
    # Crownless = ("无冠者", "Crownless")
    # Jue = ("角", "Jué")
    # SentryConstruct = ("异构武装", "Sentry Construct")
    # Hecate = ("赫卡忒", "Hecate")
    # Lorelei = ("罗蕾莱", "Lorelei")
    # DragonOfDirge = ("叹息古龙", "Dragon of Dirge")
    # NightmareFeilianBeringal = ("梦魇飞廉之猩", "Nightmare: Feilian Beringal")
    # NightmareImpermanenceHeron = ("梦魇无常凶鹭", "Nightmare: Impermanence Heron")
    # NightmareTempestMephis = ("梦魇云闪之鳞", "Nightmare: Tempest Mephis")
    # NightmareThunderingMephis = ("梦魇朔雷之鳞", "Nightmare: Thundering Mephis")
    # NightmareCrownless = ("梦魇无冠者", "Nightmare: Crownless")
    # NightmareInfernoRider = ("梦魇燎照之骑", "Nightmare: Inferno Rider")
    # NightmareMourningAix = ("梦魇哀声鸷", "Nightmare: Mourning Aix")
    # NightmareLampylumenMyriad = ("梦魇辉萤军势", "Nightmare: Lampylumen Myriad")
    # Fleurdelys = ("芙露德莉斯", "Fleurdelys")

    # @classmethod
    # def get_boss_name(cls):
    #     # return {member.name: member.value for member in cls}
    #     # TODO tr
    #     return [member.value[1] for member in cls]


class BossNameListValidator(ConfigValidator):
    """ Enum list validator """

    def __init__(self, enumMeta: EnumMeta): # EnumMeta是枚举类的元类，指枚举类本身（不是成员），Enum则是指枚举类的成员
        self._enumMeta = enumMeta
        self.names = list(enumMeta.__members__.keys())

    def validate(self, value):
        return value.name in self.names

    def correct(self, values: list):
        enumList = []
        for v in values:
            if isinstance(v, str) and v in self.names:
                enumList.append(self._enumMeta[v])
            elif isinstance(v, self._enumMeta):
                enumList.append(v)
        return enumList

class BossNameListSerializer(ConfigSerializer):
    """ enumeration class serializer """

    def __init__(self, enumClass):
        self.enumClass = enumClass

    def serialize(self, values: list[Enum]):
        enumList = [value.name for value in values]
        logger.debug(enumList)
        return enumList

    def deserialize(self, values: list[str]):
        enumList = [self.enumClass[value] for value in values]
        logger.debug(enumList)
        return enumList

class GameFolderValidator(ConfigValidator):

    def validate(self, value):
        if value == "Auto":
            return True
        return Path(value).exists()

    def correct(self, value):
        if value == "Auto":
            return value
        path = Path(value)
        return str(path.absolute()).replace("\\", "/").replace("\\\\", "/")

class ParamConfig(QConfig):
    """ Config of parameters """

    # Boss
    bossName = ConfigItem(
        "BossRush", "BossName", [BossNameEnum.Dreamless], BossNameListValidator(BossNameEnum), BossNameListSerializer(BossNameEnum))
    # Weekly Challenge
    bossLevel = OptionsConfigItem(
        "BossRush", "BossLevel", "Auto", OptionsValidator(["40", "50", "60", "70", "80", "90", "Auto"]))

    # defaultComboSequence = [
    #     ["Jinhsi", "q~0.1,e,r,e,a,a,a,a,a,e,a,a,a,a,a,e", True],
    #     ["Changli", "r,q~0.1,e,a,a,a,a~,e", True],
    #     ["Shorekeeper", "q~0.1,e~0.1,a", True],
    #     ["Verina", "r,e,q~0.1,s,a(0.1),a", True],
    # ]
    # defaultComboSequence = [
    #     ["Jinhsi"],
    #     ["Changli"],
    #     ["Shorekeeper"],
    #     ["Verina"],
    # ]
    # comboSequence = ConfigItem("BossRush", "ComboSequence", defaultComboSequence)

    autoCombat = ConfigItem("BossRush", "AutoCombatBeta", False, BoolValidator())

    autoRestartPeriod = ConfigItem("BossRush", "AutoRestartPeriod", 'Close')

    # Game
    gamePath = ConfigItem("Game", "GamePath", "Auto", GameFolderValidator())


    def save(self):
        """ Save config, excluding certain fields """
        # 获取字典并排除某些字段
        config_dict = self._cfg.toDict()

        # 排除字段
        fields_to_exclude = ['QFluentWidgets']
        filtered_dict = {key: value for key, value in config_dict.items() if key not in fields_to_exclude}

        # 保存过滤后的字典
        self._cfg.file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cfg.file, "w", encoding="utf-8") as f:
            json.dump(filtered_dict, f, ensure_ascii=False, indent=4)


def getParamFilePath():
    return str(Path(__file__).parent.parent.parent.parent.joinpath('temp/config/param-config.json'))


paramConfig = ParamConfig()
paramConfigPath = getParamFilePath()
paramConfig.load(paramConfigPath)
logger.debug(str(paramConfig.toDict()))
globalSignal.paramConfigPathSignal.emit(paramConfigPath)
