import logging

from src.core.constants import BossNameEnum
from src.core.interface import BossInfoService

logger = logging.getLogger(__name__)


class BossInfoServiceImpl(BossInfoService):

    def __init__(self):
        pass

    def is_nightmare(self, boss_name: str) -> bool:
        """
        是否是梦魇boss
        :param boss_name:
        :return:
        """
        return boss_name and boss_name.startswith("梦魇")

    def is_auto_pickup(self, boss_name: str) -> bool:
        """
        是否需要自动拾取，如梦魇boss、芬莱克
        :param boss_name:
        :return:
        """
        if not boss_name:
            return False
        if boss_name in [BossNameEnum.Fenrico.value, BossNameEnum.LadyOfTheSea.value, BossNameEnum.TheFalseSovereign.value]:
            return True
        if boss_name.startswith("梦魇"):
            return True
        return False
