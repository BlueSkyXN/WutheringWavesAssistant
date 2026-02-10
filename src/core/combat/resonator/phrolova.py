import logging
import time

import numpy as np

from src.core.combat.combat_core import ColorChecker, BaseResonator, CharClassEnum, ResonatorNameEnum
from src.core.combat.resonator.generic import GenericResonator
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BasePhrolova(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

        # 协奏 左下血条旁红圈
        self._concerto_energy_checker = ColorChecker.concerto_fusion()

        # 能量1 血条上方的4格能量
        self._energy1_point = [(547, 668), (548, 668), (552, 668)]
        self._energy1_color = [(107, 97, 250)]  # BGR
        self._energy1_checker = ColorChecker(self._energy1_point, self._energy1_color)

        # 能量2 血条上方的4格能量
        self._energy2_point = [(595, 668), (604, 668), (614, 668)]
        self._energy2_color = self._energy1_color
        self._energy2_checker = ColorChecker(self._energy2_point, self._energy2_color)

        # 能量3 血条上方的4格能量
        self._energy3_point = [(649, 668), (659, 668), (668, 668)]
        self._energy3_color = self._energy1_color
        self._energy3_checker = ColorChecker(self._energy3_point, self._energy3_color)

        # 能量4 血条上方的4格能量
        self._energy4_point = [(692, 668), (701, 668), (711, 668)]
        self._energy4_color = self._energy1_color
        self._energy4_checker = ColorChecker(self._energy4_point, self._energy4_color)

        # 共鸣技能
        self._resonance_skill_point = [(1051, 632), (1077, 630), (1065, 665)]
        self._resonance_skill_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_checker = ColorChecker(self._resonance_skill_point, self._resonance_skill_color)

        # 声骸技能
        self._echo_skill_point = [(1135, 632), (1130, 654), (1150, 658)]
        self._echo_skill_color = [(255, 255, 255)]  # BGR
        self._echo_skill_checker = ColorChecker(self._echo_skill_point, self._echo_skill_color)

        # 共鸣解放
        self._resonance_liberation_point = [(1203, 654), (1210, 654)]
        self._resonance_liberation_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_checker = ColorChecker(
            self._resonance_liberation_point, self._resonance_liberation_color)

    def __str__(self):
        return self.resonator_name().name

    def resonator_name(self) -> ResonatorNameEnum:
        return ResonatorNameEnum.phrolova

    def char_class(self) -> list[CharClassEnum]:
        return [CharClassEnum.MainDPS]

    def energy_count(self, img: np.ndarray) -> int:
        energy_count = 0
        if self._energy1_checker.check(img):
            energy_count = 1
        if self._energy2_checker.check(img):
            energy_count = 2
        if self._energy3_checker.check(img):
            energy_count = 3
        if self._energy4_checker.check(img):
            energy_count = 4
        logger.debug(f"{self.resonator_name().value}-能量: {energy_count}格")
        return energy_count

    def is_concerto_energy_ready(self, img: np.ndarray) -> bool:
        is_ready = self._concerto_energy_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-协奏: {is_ready}")
        return is_ready

    def is_resonance_skill_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_skill_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-共鸣技能: {is_ready}")
        return is_ready

    def is_echo_skill_ready(self, img: np.ndarray) -> bool:
        is_ready = self._echo_skill_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-声骸技能: {is_ready}")
        return is_ready

    def is_resonance_liberation_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-共鸣解放: {is_ready}")
        return is_ready


class Phrolova(GenericResonator):
# class Phrolova(BasePhrolova):
    # # COMBO_SEQ 为训练场单人静态完整连段，后续开发以此为准从中拆分截取
    #
    # # 常规轴
    # COMBO_SEQ = [
    #     # 声骸技能
    #     ["Q", 0.05, 0.30],
    #     ["a", 0.05, 0.30],
    #     ["a", 0.05, 0.30],
    #     ["a", 0.05, 1.60],
    #     ["j", 0.05, 1.20],
    #     # 共鸣技能 Ea 一离火
    #     ["E", 0.05, 1.25],
    #     ["a", 0.05, 1.30],
    #     # ["E", 0.05, 1.25],
    #     # ["a", 0.05, 1.30],
    #     # 间隔
    #     ["w", 0.00, 1.20],
    #     # 普攻 5a 一离火
    #     ["a", 0.05, 0.31],
    #     ["a", 0.05, 0.50],
    #     ["a", 0.05, 0.50],
    #     ["a", 0.05, 1.05],
    #     ["a", 0.05, 0.00],
    #     ["w", 0.05, 0.75],
    #     ["j", 0.05, 1.2],
    #     # 共鸣技能 Ea 一离火
    #     ["E", 0.05, 1.25],
    #     ["a", 0.05, 1.30],
    #     ["w", 0.00, 1.20],
    #     # 普攻 5a 一离火
    #     ["a", 0.05, 0.31],
    #     ["a", 0.05, 0.50],
    #     ["a", 0.05, 0.50],
    #     ["a", 0.05, 1.05],
    #     ["a", 0.05, 0.00],
    #     ["w", 0.05, 0.75],
    #     ["j", 0.05, 1.20],
    #     # zRz
    #     ["z", 0.50, 0.90],
    #     ["R", 0.05, 1.65],
    #     ["z", 1.90, 0.00],
    #     ["w", 0.00, 1.00],
    #     ["j", 0.05, 0.00],
    # ]
    #
    # def __init__(self, control_service: ControlService, img_service: ImgService):
    #     super().__init__(control_service, img_service)
    #
    # def Ea(self):
    #     logger.debug("Ea")
    #     return [
    #         # 共鸣技能 Ea 一离火
    #         # ["E", 0.05, 1.25],
    #         # ["a", 0.05, 1.30],
    #
    #         ["E", 0.05, 0.30],  # 冗余
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.40],
    #         ["a", 0.05, 0.30],
    #     ]
    #
    # def E(self):
    #     logger.debug("E")
    #     return [
    #         # 共鸣技能 E
    #         ["E", 0.05, 1.25],
    #     ]
    #
    # def a2(self):
    #     logger.debug("a2")
    #     return [
    #         # 普攻 2a
    #         ["a", 0.05, 0.31],
    #         # ["a", 0.05, 0.50],
    #         ["a", 0.05, 0.30],
    #     ]
    #
    # # def a5(self):
    # #     logger.debug("a5")
    # #     return [
    # #         # 普攻 5a 一离火
    # #         ["a", 0.05, 0.31],
    # #         ["a", 0.05, 0.50],
    # #         ["a", 0.05, 0.50],
    # #
    # #         # ["a", 0.05, 1.05],
    # #         ["a", 0.05, 0.35],
    # #         ["a", 0.05, 0.35],
    # #         ["a", 0.05, 0.20],
    # #         ["a", 0.05, 0.10],
    # #
    # #         ["a", 0.05, 0.00],
    # #         ["w", 0.05, 0.75],
    # #     ]
    #
    # def a3(self):
    #     logger.debug("a3")
    #     return [
    #         # 普攻 5a 一离火
    #         # ["a", 0.05, 0.31],
    #         # ["a", 0.05, 0.50],
    #         ["a", 0.05, 0.25],
    #         ["a", 0.05, 0.20],
    #
    #         # ["a", 0.05, 1.05],
    #         ["a", 0.05, 0.35],
    #         ["a", 0.05, 0.35],
    #         ["a", 0.05, 0.20],
    #         ["a", 0.05, 0.10],
    #
    #         ["a", 0.05, 0.00],
    #         ["w", 0.05, 0.75],
    #     ]
    #
    # def a(self):
    #     logger.debug("a")
    #     return [
    #         ["a", 0.05, 0.31],
    #     ]
    #
    # # def zRz(self):
    # #     return [
    # #         # zRz 实战效果不好，若被打断等情况，会长时间原地发呆
    # #         ["z", 0.60, 0.90],
    # #         ["R", 0.05, 1.65],
    # #         ["z", 1.90, 1.00],
    # #     ]
    #
    # def Rz(self):
    #     logger.debug("Rz")
    #     return [
    #         # Rz
    #         ["R", 0.05, 1.65],
    #         ["z", 2.00, 1.00],
    #     ]
    #
    # def zR(self):
    #     logger.debug("zR")
    #     return [
    #         # zR
    #         # ["z", 0.60, 1.10],
    #         # ["R", 0.05, 1.65],
    #
    #         ["z", 0.60, 0.00],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.10],
    #
    #         ["R", 0.05, 1.65],
    #     ]
    #
    # def z(self):
    #     logger.debug("z")
    #     return [
    #         # z
    #         ["z", 0.70, 1.10],
    #     ]
    #
    # def az(self):
    #     logger.debug("az")
    #     return [
    #         # az
    #         ["a", 0.05, 0.31],
    #         ["z", 0.70, 1.10],
    #     ]
    #
    # def Qa3(self):
    #     logger.debug("Qa3")
    #     return [
    #         # 声骸技能，梦魇摩托
    #         ["Q", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 0.30],
    #         ["a", 0.05, 1.60],
    #     ]
    #
    # def Q(self):
    #     logger.debug("Q")
    #     return [
    #         # 声骸技能，普通摩托
    #         ["Q", 0.05, 0.30],
    #     ]
    #
    # def R(self):
    #     logger.debug("R")
    #     return [
    #         ["R", 0.05, 1.65],
    #     ]

    def quit_R(self):
        logger.debug("R")
        return [
            ["R", 0.60, 0.30],
        ]

    # def full_combo(self):
    #     # 测试用，一整套连招
    #     return self.COMBO_SEQ
    #
    # def combo(self):
    #
    #     pass
