import logging
import time

import numpy as np

from src.core.combat.combat_core import ColorChecker, BaseResonator, BaseCombo, CharClassEnum
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseCiaccona(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

        self.name = "夏空"
        self.name_en = "ciaccona"

        # 协奏 左下血条旁绿圈
        self._concerto_energy_checker = ColorChecker.concerto_aero()

        # 能量1 血条上方的3格能量
        self._energy1_point = [(548, 668), (549, 668), (557, 668)]
        self._energy1_color = [(189, 245, 87), (250, 251, 143), (250, 251, 164), (250, 251, 180), (225, 251, 206), (225, 251, 225)]  # BGR
        self._energy1_checker = ColorChecker(self._energy1_point, self._energy1_color)

        # 能量2 血条上方的3格能量
        self._energy2_point = [(615, 668), (616, 668), (624, 668)]
        self._energy2_color = self._energy1_color
        self._energy2_checker = ColorChecker(self._energy2_point, self._energy2_color)

        # 能量3 血条上方的3格能量
        self._energy3_point = [(682, 668), (683, 668), (691, 668)]
        self._energy3_color = self._energy1_color
        self._energy3_checker = ColorChecker(self._energy3_point, self._energy3_color)

        # 共鸣技能
        self._resonance_skill_point = [(1073, 634), (1057, 653)]
        self._resonance_skill_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_checker = ColorChecker(self._resonance_skill_point, self._resonance_skill_color)

        # 声骸技能
        self._echo_skill_point = [(1132, 654), (1138, 655)]
        self._echo_skill_color = [(255, 255, 255)]  # BGR
        self._echo_skill_checker = ColorChecker(self._echo_skill_point, self._echo_skill_color)

        # 共鸣解放
        self._resonance_liberation_point = [(1206, 635), (1209, 637)]
        self._resonance_liberation_color = [(255, 255, 255), (232, 252, 219), (208, 247, 165), (190, 244, 132)]  # BGR
        self._resonance_liberation_checker = ColorChecker(
            self._resonance_liberation_point, self._resonance_liberation_color)

        ## 战斗时动态变量

        # 唱歌时不切夏空
        self._is_singing = False
        self._singing_timeout_seconds = 34.5
        self._singing_start_time = None  # time.monotonic()

    def __str__(self):
        return self.name_en

    def char_class(self) -> list[CharClassEnum]:
        return [CharClassEnum.Support]

    def energy_count(self, img: np.ndarray) -> int:
        energy_count = 0
        if self._energy1_checker.check(img):
            energy_count = 1
        if self._energy2_checker.check(img):
            energy_count = 2
        if self._energy3_checker.check(img):
            energy_count = 3
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

    def is_singing(self):
        if self._is_singing is False:
            return False
        if time.monotonic() - self._singing_start_time > self._singing_timeout_seconds:
            return False
        return True

    def _set_singing(self, state: bool):
        if state:
            self._is_singing = True
            self._singing_start_time = time.monotonic()
        else:
            self._is_singing = False


class Ciaccona(BaseCiaccona, BaseCombo):
    # COMBO_SEQ 为训练场单人静态完整连段，后续开发以此为准从中拆分截取

    # 常规轴
    COMBO_SEQ = [
        # 普攻4a
        ["a", 0.05, 0.24],
        ["a", 0.05, 0.88],
        ["a", 0.05, 0.85],
        ["a", 0.05, 1.30],
        ["j", 0.05, 1.20],

        # 普攻4a取消
        ["a", 0.05, 0.24],
        ["a", 0.05, 0.88],
        ["a", 0.05, 0.85],
        ["a", 0.05, 0.10],
        ["d", 0.05, 0.30],
        ["j", 0.05, 1.20],

        # E3a E后从普攻第二段开始打 E加一层风蚀
        ["E", 0.05, 0.50],
        ["a", 0.05, 0.88],
        ["a", 0.05, 0.85],
        ["a", 0.05, 1.30],
        ["j", 0.05, 1.20],

        # jaaa
        ["j", 0.05, 0.12],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 1.20],
        ["j", 0.05, 1.20],

        # jaaa取消
        ["j", 0.05, 0.12],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 0.10],
        ["d", 0.05, 1.00],
        ["j", 0.05, 1.20],

        # 3能量 重击 加一层风蚀
        ["z", 1.54, 0.20],
        ["j", 0.05, 1.20],

        # 能量不满 重击上挑
        ["z", 0.82, 0.05],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 1.20],
        ["j", 0.05, 1.20],

        # 空中E 3音律重击
        ["j", 0.05, 0.12],
        ["E", 0.05, 0.15],
        ["z", 1.30, 0.40],
        ["j", 0.05, 1.20],

        # R 风蚀
        ["R", 0.05, 3.67],
        # ["1", 0.05, 1.20],

        # R 光噪
        ["R", 0.05, 3.67],
        ["A", 0.05, 0.30],
        ["A", 0.05, 0.15],
        # ["1", 0.05, 1.20],

        # R 全程
        ["R", 0.05, 3.67],  # 37950
        ["w", 0.00, 34.28],
        ["j", 0.05, 1.20],

        # jaaaEaaa
        ["j", 0.05, 0.12],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 0.10],
        ["E", 0.05, 0.50],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 0.10],
        ["j", 0.05, 1.20],

        # jEaaajaaa BV1N8KyzAENt
        ["j", 0.05, 0.12],
        ["E", 0.05, 0.50],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 0.10],
        ["j", 0.05, 0.12],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.78],
        ["a", 0.05, 0.10],
        ["j", 0.05, 1.20],

        # 枪系通用 瞄准加特林
        ["G", 0.008, 0.008],

        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.010],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],

        ["G", 0.008, 0.008],

        ["w", 0.00, 0.50],

        # 普攻 瞄准无限戳
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
        ["a", 0.008, 0.200],
        ["G", 0.008, 0.008],
        ["G", 0.008, 0.008],
    ]

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def a4(self):
        logger.debug("a4")
        return [
            # 普攻4a
            ["a", 0.05, 0.24],

            # ["a", 0.05, 0.88],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.28],

            # ["a", 0.05, 0.85],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],

            # ["a", 0.05, 1.30],
            ["a", 0.05, 0.15],
            ["a", 0.05, 0.10],
            ["w", 0.00, 1.00],
        ]

    def a_intro(self):
        logger.debug("a_intro")
        return [
            # 普攻1.3秒，覆盖变奏时间
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.20],
        ]

    def a2_end(self):
        logger.debug("a2_end")
        return [
            # 普攻4a的后两段
            # ["a", 0.05, 0.24],
            # ["a", 0.05, 0.88],

            # ["a", 0.05, 0.85],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],

            # ["a", 0.05, 1.30],
            ["a", 0.05, 0.15],
            ["a", 0.05, 0.10],
            ["w", 0.00, 1.00],
        ]

    # def z(self):
    #     logger.debug("z")
    #     return [
    #         # 能量不满 重击上挑
    #         ["z", 0.82, 0.05],
    #     ]

    def z_musical_essence_3(self):
        logger.debug("z_musical_essence_3")
        return [
            # 3能量 重击 加一层风蚀
            ["z", 1.54, 0.20],
        ]

    def E(self):
        logger.debug("E")
        return [
            # ["E", 0.05, 0.60],
            ["E", 0.05, 0.15],
            ["E", 0.05, 0.40],
        ]

    def E3a(self):
        logger.debug("E3a")
        return [
            # E3a E后从普攻第二段开始打 E加一层风蚀
            # ["E", 0.05, 0.50],
            ["E", 0.05, 0.15],
            ["E", 0.05, 0.30],

            # ["a", 0.05, 0.88],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.28],

            # ["a", 0.05, 0.85],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],

            # ["a", 0.05, 1.30],
            ["a", 0.05, 0.15],
            ["a", 0.05, 0.10],
            ["w", 0.00, 1.00],
        ]

    def jEz(self):
        logger.debug("jEz")
        return [
            # 空中E 3音律重击
            ["j", 0.05, 0.12],
            ["E", 0.05, 0.15],
            ["z", 1.30, 0.40],
        ]

    def jEaaa(self):
        logger.debug("jEaaa")
        return [
            ["j", 0.05, 0.12],

            # ["a", 0.05, 0.65],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],

            # ["a", 0.05, 0.78],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.18],

            ["a", 0.05, 0.20],

            ["w", 0.00, 1.00],
        ]

    def jEaaajaaa(self):
        logger.debug("jEaaajaaa")
        return [
            ["j", 0.05, 0.12],

            # ["E", 0.05, 0.50],
            ["E", 0.05, 0.15],
            ["E", 0.05, 0.30],

            # ["a", 0.05, 0.65],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],

            # ["a", 0.05, 0.78],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.18],

            ["a", 0.05, 0.10],

            ["j", 0.05, 0.12],

            # ["a", 0.05, 0.65],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],

            # ["a", 0.05, 0.78],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.18],

            ["a", 0.05, 0.20],

            ["w", 0.00, 1.00],
        ]

    def jaaa(self):
        logger.debug("jaaa")
        return [
            # jaaa
            ["j", 0.05, 0.12],

            # ["a", 0.05, 0.65],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.30],

            # ["a", 0.05, 0.78],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.18],

            ["a", 0.05, 0.20],

            ["w", 0.00, 1.00],
        ]

    def Q(self):
        logger.debug("Q")
        return [
            # 声骸技能
            ["Q", 0.05, 0.00],
        ]

    def R_aero_erosion(self):
        logger.debug("R_aero_erosion")
        return [
            # R 风蚀
            # ["R", 0.05, 3.67],
            ["R", 0.05, 0.20],
            ["R", 0.05, 3.42],
        ]

    def R_spectro_frazzle(self):
        logger.debug("R_spectro_frazzle")
        return [
            # R 光噪
            # ["R", 0.05, 3.67],
            ["R", 0.05, 0.20],
            ["R", 0.05, 3.42],

            ["A", 0.05, 0.30],
            ["A", 0.05, 0.15],
        ]

    def full_combo(self):
        # 测试用，一整套连招
        return self.COMBO_SEQ

    def combo(self):
        # 普攻第四段、3音律重击、E、变奏 加一层风蚀
        # 专武对风蚀目标减风抗
        # 普攻第四段、变奏 加一格音律能量

        # 入场自动退出大招
        self._set_singing(False)

        # 变奏1.29秒，从第三段普攻开始打
        self.combo_action(self.a_intro(), True)

        img = self.img_service.screenshot()
        energy_count = self.energy_count(img)
        # is_concerto_energy_ready = self.is_concerto_energy_ready(img)
        is_resonance_skill_ready = self.is_resonance_skill_ready(img)
        # is_echo_skill_ready = self.is_echo_skill_ready(img)
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        # boss_hp = self.boss_hp(img)

        self.combo_action(self.Q(), False)

        # 哒～哒啦哒哒哒啦～哒哒啦哒哒啦哒～
        if is_resonance_liberation_ready:
            if energy_count == 3:
                if is_resonance_skill_ready:
                    self.combo_action(self.jEz(), True)
                else:
                    self.combo_action(self.z_musical_essence_3(), True)
            else:
                if is_resonance_skill_ready:
                    self.combo_action(self.jEaaa(), False)
                else:
                    self.combo_action(self.jaaa(), False)

            # TODO 光噪、风蚀
            self.combo_action(self.R_aero_erosion(), True)
            self._set_singing(True)
            return

        if energy_count == 3:
            self.combo_action(self.z_musical_essence_3(), False)
        else:
            if is_resonance_skill_ready:
                if energy_count == 2:
                    self.combo_action(self.jEaaa(), False)
                else:
                    self.combo_action(self.jEaaajaaa(), False)
            else:
                self.combo_action(self.a2_end(), False)

        img = self.img_service.screenshot()
        energy_count = self.energy_count(img)
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        if energy_count == 3:
            self.combo_action(self.z_musical_essence_3(), False)
        if not is_resonance_liberation_ready:
            img = self.img_service.screenshot()
            is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        if is_resonance_liberation_ready:
            self.combo_action(self.R_aero_erosion(), True)
            self._set_singing(True)
            return