import logging
import random
import time

from src.core.combat.combat_core import BaseResonator, CharClassEnum, ResonatorNameEnum
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseGeneric(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def __str__(self):
        return self.resonator_name().name

    def resonator_name(self) -> ResonatorNameEnum:
        return ResonatorNameEnum.generic

    def char_class(self) -> list[CharClassEnum]:
        return [CharClassEnum.SubDPS]


class GenericResonator(BaseGeneric):
    COMBO_SEQ = [
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],

        ["z", 0.50, 0.50],
        ["R", 0.05, 0.50],
        ["Q", 0.05, 0.50],
    ]

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def a4(self):
        logger.debug("a4")
        return [
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
        ]

    def Eaa(self):
        logger.debug("Eaa")
        return [
            ["E", 0.05, 0.50],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
        ]

    def E(self):
        logger.debug("E")
        return [
            # 共鸣技能 E
            ["E", 0.05, 0.50],
        ]

    def z(self):
        logger.debug("z")
        return [
            ["z", 0.50, 0.50],
        ]

    def Q(self):
        logger.debug("Q")
        return [
            ["Q", 0.05, 0.50],
        ]

    def R(self):
        logger.debug("R")
        return [
            ["R", 0.05, 0.50],
        ]

    def full_combo(self):
        # 测试用，一整套连招
        return self.COMBO_SEQ

    def combo(self):
        self.combo_action(self.a4(), False)

        combo_list = [self.Eaa(), self.R(), self.z()]
        random.shuffle(combo_list)
        for i in combo_list:
            self.combo_action(i, False)
            time.sleep(0.15)

        self.combo_action(self.Q(), False)
