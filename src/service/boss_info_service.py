import logging

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