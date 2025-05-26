import logging
import random
import time

import numpy as np

from src.core.combat.combat_core import ColorChecker, BaseResonator, BaseCombo
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseRover(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service)
        self.img_service = img_service

        self.name = "漂泊者-湮灭"

        # 协奏 左下血条旁红圈
        self._concerto_energy_point = [(513, 669), (514, 669), (514, 670), (514, 671)]
        self._concerto_energy_color = [(81, 112, 210)]  # BGR
        self._concerto_energy_checker = ColorChecker(self._concerto_energy_point, self._concerto_energy_color)

        # 能量满 血条上方的能量
        self._energy_full_point = [(723, 667), (724, 668)]
        self._energy_full_color = [(97, 121, 255)]  # BGR
        self._energy_full_checker = ColorChecker(self._energy_full_point, self._energy_full_color)

        # 共鸣技能
        self._resonance_skill_point = [(1056, 635), (1074, 635), (1065, 665)]
        self._resonance_skill_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_checker = ColorChecker(self._resonance_skill_point, self._resonance_skill_color)

        # 声骸技能
        self._echo_skill_point = [(1135, 632), (1130, 654), (1150, 658)]
        self._echo_skill_color = [(255, 255, 255)]  # BGR
        self._echo_skill_checker = ColorChecker(self._echo_skill_point, self._echo_skill_color)

        # 共鸣解放
        self._resonance_liberation_point = [(1097, 659), (1217, 658)]
        self._resonance_liberation_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_checker = ColorChecker(
            self._resonance_liberation_point, self._resonance_liberation_color)

        # 共鸣解放 黑咩大暴走状态
        self._cosmos_rave_point = [(532, 673), (734, 673)]
        self._cosmos_rave_color = [(73, 81, 181)]  # BGR
        self._cosmos_rave_checker = ColorChecker(
            self._cosmos_rave_point, self._cosmos_rave_color, logic=ColorChecker.LogicEnum.AND)

    def energy_count(self, img: np.ndarray) -> int:
        # 安可只看能量是否满，满为1，未满为0
        energy_count = 0
        if self._energy_full_checker.check(img):
            energy_count = 1
            logger.debug(f"{self.name}-能量: 已满")
        else:
            logger.debug(f"{self.name}-能量: 未满")
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

    def is_cosmos_rave_ready(self, img: np.ndarray) -> bool:
        is_ready = self._cosmos_rave_checker.check(img)
        logger.debug(f"{self.name}-黑咩大暴走状态: {is_ready}")
        return is_ready


class Rover(BaseRover, BaseCombo):
    # COMBO_SEQ 为训练场单人静态完整连段，后续开发以此为准从中拆分截取

    # 常规轴
    COMBO_SEQ = [
        # Ea
        ["E", 0.05, 1.90],
        ["a", 0.05, 0.90],
        ["j", 0.05, 1.20],

        # 普攻5a
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.40],
        ["a", 0.05, 0.52],
        ["a", 0.05, 0.62],
        ["a", 0.05, 1.22],
        ["j", 0.05, 1.20],

        # R
        ["R", 0.05, 2.63],
        ["j", 0.05, 1.20],

        # R E普攻E，普攻连点打满一套的时间
        ["E", 0.05, 0.28],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["E", 0.05, 0.28],
        ["w", 0.05, 1.20],
        ["j", 0.05, 1.20],
    ]

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def E(self):
        logger.debug("E")
        return [
            # E
            ["E", 0.05, 1.90],
        ]

    def Ea(self):
        logger.debug("Ea")
        return [
            # Ea
            # ["E", 0.05, 1.90],  # 等待时间太长，实战容易发呆，拆分
            ["E", 0.05, 0.00],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.15],
            ["a", 0.05, 0.05],

            # ["a", 0.05, 0.90],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.20],
        ]

    def a5(self):
        logger.debug("a5")
        return [
            # 普攻5a
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.40],
            ["a", 0.05, 0.52],
            ["a", 0.05, 0.62],
            ["a", 0.05, 1.22],
        ]

    def R(self):
        logger.debug("R")
        return [
            # R
            ["R", 0.05, 2.63],
        ]

    def Ea11E(self):
        logger.debug("Ea11E")
        return [
            # R E普攻E，普攻连点打满一套的时间
            ["E", 0.05, 0.28],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["E", 0.05, 0.28],
        ]

    def z(self):
        logger.debug("z")
        return [
            # 重击
            ["z", 0.60, 3.00],
        ]

    def Qa3(self):
        logger.debug("Qa3")
        return [
            # 声骸技能，梦魇摩托
            ["Q", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.10],  # 多a一下
            ["a", 0.05, 1.60],
        ]

    def Q(self):
        logger.debug("Q")
        return [
            # 声骸技能，普通摩托
            ["Q", 0.05, 0.30],
        ]

    def full_combo(self):
        # 测试用，一整套连招
        return self.COMBO_SEQ

    def combo(self):
        img = self.img_service.screenshot()
        energy_count = self.energy_count(img)
        is_concerto_energy_ready = self.is_concerto_energy_ready(img)
        is_resonance_skill_ready = self.is_resonance_skill_ready(img)
        is_echo_skill_ready = self.is_echo_skill_ready(img)
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        is_cosmos_rave_ready = self.is_cosmos_rave_ready(img)

        # 黑咩大暴走状态
        if is_cosmos_rave_ready:
            self.combo_action(self.Ea11E(), False)
            return

        # 别靠近安可
        if energy_count == 1:
            self.combo_action(self.z(), False)
            return

        # 有大开大
        if is_resonance_liberation_ready:
            self.combo_action(self.R(), False)
            self.combo_action(self.E(), False)
            time.sleep(0.05)
            return

        # 呼呼啦开
        if is_resonance_skill_ready:
            if random.random() < 0.66:
                self.combo_action(self.Ea(), False)
            self.combo_action(self.E(), False)
            time.sleep(0.05)
            # E被检测频率太高，在空中又放不出来，导致经常想打E合轴切人，实战时啥也没干就切走了
            # 同步放其他技能总能有一个生效，将R、Q也放到这
            if is_resonance_liberation_ready:
                self.combo_action(self.R(), False)
            elif is_echo_skill_ready:
                # 随机放梦魇摩托或普通摩托
                random_q = self.Qa3() if random.random() < 0.5 else self.Q()
                self.combo_action(random_q, False)
            return

        # 兜底，打一套普攻
        self.combo_action(self.a5(), is_echo_skill_ready)

        # 大招图标在切人时会先红一下，导致颜色无法匹配，最后再匹配一次
        img = self.img_service.screenshot()
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        if is_resonance_liberation_ready:
            self.combo_action(self.R(), False)
            return

        # 摩托最后放合轴
        if is_echo_skill_ready:
            # 随机放梦魇摩托或普通摩托
            random_q = self.Qa3() if random.random() < 0.5 else self.Q()
            self.combo_action(random_q, False)
