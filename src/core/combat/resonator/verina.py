import logging
import time

import numpy as np

from src.core.combat.combat_core import ColorChecker, BaseResonator, BaseCombo
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseVerina(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service)
        self.img_service = img_service

        self.name = "维里奈"
        self.name_en = "verina"

        # 协奏 左下血条旁红圈
        self._concerto_energy_checker = ColorChecker.concerto_spectro()

        # 能量1 血条上方的4格能量
        self._energy1_point = [(547, 668), (548, 668), (552, 668)]
        self._energy1_color = [(114, 241, 255)]  # BGR
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
        self._resonance_skill_point = [(1071, 658), (1073, 656)]
        self._resonance_skill_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_checker = ColorChecker(self._resonance_skill_point, self._resonance_skill_color)

        # 声骸技能
        self._echo_skill_point = [(1137, 634), (1122, 657), (1149, 655)]
        self._echo_skill_color = [(255, 255, 255)]  # BGR
        self._echo_skill_checker = ColorChecker(self._echo_skill_point, self._echo_skill_color)

        # 共鸣解放
        self._resonance_liberation_point = [(1205, 660), (1208, 631), (1209, 631)]
        self._resonance_liberation_color = [(253, 253, 253), (219, 218, 215)]  # BGR
        self._resonance_liberation_checker = ColorChecker(
            self._resonance_liberation_point, self._resonance_liberation_color)

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
        logger.debug(f"{self.name}-能量: {energy_count}格")
        return energy_count

    def is_concerto_energy_ready(self, img: np.ndarray) -> bool:
        is_ready = self._concerto_energy_checker.check(img)
        logger.debug(f"{self.name}-协奏: {is_ready}")
        return is_ready

    def is_resonance_skill_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_skill_checker.check(img)
        logger.debug(f"{self.name}-共鸣技能: {is_ready}")
        return is_ready

    def is_echo_skill_ready(self, img: np.ndarray) -> bool:
        is_ready = self._echo_skill_checker.check(img)
        logger.debug(f"{self.name}-声骸技能: {is_ready}")
        return is_ready

    def is_resonance_liberation_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_checker.check(img)
        logger.debug(f"{self.name}-共鸣解放: {is_ready}")
        return is_ready


class Verina(BaseVerina, BaseCombo):
    # COMBO_SEQ 为训练场单人静态完整连段，后续开发以此为准从中拆分截取

    # 常规轴
    COMBO_SEQ = [
        # 普攻5a
        ["a", 0.05, 0.40],
        ["a", 0.05, 0.40],
        ["a", 0.05, 0.70],
        ["a", 0.05, 0.55],
        ["a", 0.05, 0.90],
        ["j", 0.05, 1.20],

        # (切人) aa EQ 跳aaa
        ["a", 0.05, 0.35],
        ["a", 0.05, 0.32],
        ["E", 0.05, 0.10],
        ["Q", 0.05, 0.10],
        ["j", 0.05, 0.10],
        ["a", 0.05, 0.20],
        ["a", 0.05, 0.20],
        ["a", 0.05, 1.17],
        ["j", 0.05, 1.20],
    ]

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def a2EQ(self):
        logger.debug("a2EQ")
        return [
            ["a", 0.05, 0.35],
            ["a", 0.05, 0.32],
            ["a", 0.05, 0.00],  # 多打一个a，若EQ没cd还可以出普攻
            ["E", 0.05, 0.10],
            ["Q", 0.05, 0.10],
        ]

    def ja3(self):
        logger.debug("ja3")
        return [
            ["j", 0.05, 0.10],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.20],
            ["a", 0.05, 1.17],
        ]

    # def a5(self):
    #     logger.debug("a5")
    #     return [
    #         # 普攻5a
    #         ["a", 0.05, 0.40],
    #         ["a", 0.05, 0.40],
    #         # ["a", 0.05, 0.70],  # 拆分长等待
    #         # ["a", 0.05, 0.55],
    #         ["a", 0.05, 0.20],
    #         ["a", 0.05, 0.20],
    #         ["a", 0.05, 0.15],
    #         ["a", 0.05, 0.25],
    #         ["a", 0.05, 0.25],
    #
    #         ["a", 0.05, 0.90],
    #     ]

    def a3(self):
        logger.debug("a3")
        return [
            # 普攻a5的后三下
            # ["a", 0.05, 0.40],
            # ["a", 0.05, 0.40],
            # ["a", 0.05, 0.70],  # 拆分长等待
            # ["a", 0.05, 0.55],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.15],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],

            ["a", 0.05, 0.90],
        ]

    def R(self):
        logger.debug("R")
        return [
            # R
            ["R", 0.05, 2.63],
        ]

    def EQR(self):
        logger.debug("EQR")
        return [
            # EQR
            ["E", 0.05, 0.10],
            ["Q", 0.05, 0.10],
            ["R", 0.05, 2.63],
        ]

    def full_combo(self):
        # 测试用，一整套连招
        return self.COMBO_SEQ

    def combo(self):
        img = self.img_service.screenshot()
        energy_count = self.energy_count(img)
        # is_concerto_energy_ready = self.is_concerto_energy_ready(img)
        # is_resonance_skill_ready = self.is_resonance_skill_ready(img)
        # is_echo_skill_ready = self.is_echo_skill_ready(img)
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)

        # 不管条件，入场就打aaEQ
        self.combo_action(self.a2EQ(), False)

        # 有大开大
        if is_resonance_liberation_ready:
            self.combo_action(self.R(), False)
            time.sleep(0.05)
            return

        # 有能量就跳a
        if energy_count > 0:
            self.combo_action(self.ja3(), False)
            time.sleep(0.05)
            return

        # # 兜底，打完剩下的普攻段数
        # self.combo_action(self.a3(), False)
        # self.combo_action(self.EQR(), False)
