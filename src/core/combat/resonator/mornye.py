import logging

import numpy as np

from src.core.combat.combat_core import ColorChecker, BaseResonator, CharClassEnum, ResonatorNameEnum, LogicEnum
from src.core.exceptions import StopError
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseMornye(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

        # 协奏 左下血条旁红圈
        self._concerto_energy_checker = ColorChecker.concerto_fusion()

        ## 基准模式

        # 静质量能 满时可重击进入广域观测模式
        self._rest_mass_energy_20_point = [(570, 668), (571, 668), (571, 669)]
        self._rest_mass_energy_color = [(63, 119, 250)]  # BGR
        self._rest_mass_energy_20_checker = ColorChecker(
            self._rest_mass_energy_20_point, self._rest_mass_energy_color, logic=LogicEnum.AND)

        self._rest_mass_energy_50_point = [(633, 668), (634, 668)]
        self._rest_mass_energy_50_color = self._rest_mass_energy_color
        self._rest_mass_energy_50_checker = ColorChecker(
            self._rest_mass_energy_50_point, self._rest_mass_energy_50_color, logic=LogicEnum.AND)

        self._rest_mass_energy_80_point = [(692, 668), (693, 668), (693, 669)]
        self._rest_mass_energy_80_color = self._rest_mass_energy_color
        self._rest_mass_energy_80_checker = ColorChecker(
            self._rest_mass_energy_80_point, self._rest_mass_energy_80_color)

        # 重击·位势转换
        self._heavy_attack_geopotential_shift_point = [(954, 642), (953, 645), (956, 644), (953, 659)]
        self._heavy_attack_geopotential_shift_color = [(255, 255, 255)]  # BGR
        self._heavy_attack_geopotential_shift_checker = ColorChecker(
            self._heavy_attack_geopotential_shift_point, self._heavy_attack_geopotential_shift_color,
            logic=LogicEnum.AND)

        # # 共鸣技能·期望误差
        # self._resonance_skill_expectation_error_point = [(1078, 630), (1078, 658), (1096, 655)]
        # self._resonance_skill_expectation_error_color = [(255, 255, 255)]  # BGR
        # self._resonance_skill_expectation_error_checker = ColorChecker(
        #     self._resonance_skill_expectation_error_point, self._resonance_skill_expectation_error_color,
        #     logic=LogicEnum.AND)

        ## 广域观测模式

        # 广域观测模式
        self._wide_field_observation_mode_point = [(890, 627), (890, 640), (885, 644), (895, 644)]
        self._wide_field_observation_mode_color = [(255, 255, 255)]  # BGR
        self._wide_field_observation_mode_checker = ColorChecker(
            self._wide_field_observation_mode_point, self._wide_field_observation_mode_color, logic=LogicEnum.AND)

        # 相对动能 满时可释放重击·反演
        self._relative_momentum_20_point = self._rest_mass_energy_20_point
        self._relative_momentum_color = [(245, 202, 199), (255, 221, 188), (255, 206, 176), (255, 160, 140), (255, 237, 206)]  # BGR
        self._relative_momentum_20_checker = ColorChecker(
            self._relative_momentum_20_point, self._relative_momentum_color)

        self._relative_momentum_50_point = self._rest_mass_energy_50_point
        self._relative_momentum_50_color = self._relative_momentum_color
        self._relative_momentum_50_checker = ColorChecker(
            self._relative_momentum_50_point, self._relative_momentum_50_color, logic=LogicEnum.AND)

        self._relative_momentum_80_point = self._rest_mass_energy_80_point
        self._relative_momentum_80_color = self._relative_momentum_color
        self._relative_momentum_80_checker = ColorChecker(
            self._relative_momentum_80_point, self._relative_momentum_80_color, logic=LogicEnum.AND)

        # 共鸣技能·分布式阵列
        self._resonance_skill_optimal_solution_point = [(1082, 632), (1083, 632), (1084, 632)]
        self._resonance_skill_optimal_solution_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_optimal_solution_checker = ColorChecker(
            self._resonance_skill_optimal_solution_point, self._resonance_skill_optimal_solution_color,
            logic=LogicEnum.AND)

        # 重击·反演
        self._heavy_attack_inversion_point = [(949, 638), (959, 638), (954, 642), (953, 645), (956, 644)]
        self._heavy_attack_inversion_color = [(255, 255, 255)]  # BGR
        self._heavy_attack_inversion_checker = ColorChecker(
            self._heavy_attack_inversion_point, self._heavy_attack_inversion_color, logic=LogicEnum.AND)

        # 声骸技能
        self._echo_skill_point = [(1145, 634)]
        self._echo_skill_color = [(255, 255, 255)]  # BGR
        self._echo_skill_checker = ColorChecker(self._echo_skill_point, self._echo_skill_color)

        # 共鸣解放
        self._resonance_liberation_point = [(1212, 652), (1212, 653), (1212, 654)]
        self._resonance_liberation_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_checker = ColorChecker(
            self._resonance_liberation_point, self._resonance_liberation_color, logic=LogicEnum.AND)

        # 共鸣解放2 谐振场内
        self._resonance_liberation_2_point = [(1205, 656), (1205, 657), (1205, 658)]
        self._resonance_liberation_2_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_2_checker = ColorChecker(
            self._resonance_liberation_2_point, self._resonance_liberation_2_color, logic=LogicEnum.AND)

    def __str__(self):
        return self.resonator_name().name

    def resonator_name(self) -> ResonatorNameEnum:
        return ResonatorNameEnum.mornye

    def char_class(self) -> list[CharClassEnum]:
        return [CharClassEnum.Healer]

    def is_concerto_energy_ready(self, img: np.ndarray) -> bool:
        is_ready = self._concerto_energy_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-协奏: {is_ready}")
        return is_ready

    def rest_mass_energy_count(self, img: np.ndarray) -> int:
        energy_count = 0
        if self._rest_mass_energy_20_checker.check(img):
            energy_count = 20
        if self._rest_mass_energy_50_checker.check(img):
            energy_count = 50
        if self._rest_mass_energy_80_checker.check(img):
            energy_count = 80
        logger.debug(f"{self.resonator_name().value}-静质量能: {energy_count}格")
        return energy_count

    def is_heavy_attack_geopotential_shift_ready(self, img: np.ndarray) -> bool:
        is_ready = self._heavy_attack_geopotential_shift_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-重击·位势转换: {is_ready}")
        return is_ready

    def is_wide_field_observation_mode_ready(self, img: np.ndarray) -> bool:
        is_ready = self._wide_field_observation_mode_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-广域观测模式: {is_ready}")
        return is_ready

    def relative_momentum_count(self, img: np.ndarray) -> int:
        energy_count = 0
        if self._relative_momentum_20_checker.check(img):
            energy_count = 20
        if self._relative_momentum_50_checker.check(img):
            energy_count = 50
        if self._relative_momentum_80_checker.check(img):
            energy_count = 80
        logger.debug(f"{self.resonator_name().value}-相对动能: {energy_count}格")
        return energy_count

    def is_resonance_skill_optimal_solution_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_skill_optimal_solution_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-共鸣技能·分布式阵列: {is_ready}")
        return is_ready

    def is_heavy_attack_inversion_ready(self, img: np.ndarray) -> bool:
        is_ready = self._heavy_attack_inversion_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-重击·反演: {is_ready}")
        return is_ready

    def is_echo_skill_ready(self, img: np.ndarray) -> bool:
        is_ready = self._echo_skill_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-声骸技能: {is_ready}")
        return is_ready

    def is_resonance_liberation_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-共鸣解放: {is_ready}")
        return is_ready

    def is_resonance_liberation_2_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_2_checker.check(img)
        logger.debug(f"{self.resonator_name().value}-共鸣解放2: {is_ready}")
        return is_ready


class Mornye(BaseMornye):
    # COMBO_SEQ 为训练场单人静态完整连段，后续开发以此为准从中拆分截取

    # 常规轴
    COMBO_SEQ_0 = [
        # 3a E az
        ["a", 0.05, 0.31],
        ["a", 0.05, 0.43],
        ["a", 0.05, 0.40],
        ["E", 0.05, 0.32],
        ["a", 0.05, 0.35],
        # 清空能量
        ## 常规重击
        ["z", 0.50, 0.45],
        ## E跳a
        # ["E", 0.01, 0.05],
        # ["j", 0.05, 0.05],
        # ["a", 0.05, 0.00],
        # 间隔
        ["w", 0.00, 0.70],
        ["j", 0.05, 1.20],
    ]

    # 进阶轴
    COMBO_SEQ = [
        # 3a 四格能量
        ["a", 0.05, 0.31],
        ["a", 0.05, 0.43],
        ["a", 0.05, 0.40],
        # 进入蝴蝶 有连击则四格能量起手，无连击三格能量起手（重击会先a一下变四格能量）
        ["z", 0.50, 0.30],
        # 退出蝴蝶 五格能量
        ["a", 0.01, 0.01],
        ["E", 0.01, 0.10],
        # 清空能量
        ["j", 0.05, 0.15],
        ["a", 0.05, 0.10],
        ["Q", 0.05, 0.10],
        # 间隔
        ["w", 0.00, 0.35],
        # ["j", 0.05, 1.20],
        # 开大
        ["R", 0.05, 1.20],
    ]

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def E(self):
        logger.debug("E")
        return [
            ["E", 0.05, 0.10],
        ]

    def zE(self):
        logger.debug("zE")
        return [
            ["z", 0.50, 0.30],
            ["E", 0.01, 0.10],
            ["a", 0.05, 0.05],  # 多一个普攻打断z防止一直飞
            ["a", 0.05, 0.05],  # 多一个普攻打断z防止一直飞
        ]

    def Eja(self):
        logger.debug("Eja")
        return [
            ["E", 0.01, 0.10],
            # 清空能量
            ["j", 0.05, 0.17],
            ["a", 0.05, 0.10],
        ]

    def ja(self):
        logger.debug("ja")
        return [
            # 清空能量
            ["j", 0.05, 0.17],
            ["a", 0.05, 0.10],
        ]

    def zaEja(self):
        logger.debug("zaEja")
        return [
            # 进入蝴蝶 有连击则四格能量起手，无连击三格能量起手（重击会先a一下变四格能量）
            ["z", 0.50, 0.30],
            # 退出蝴蝶 五格能量
            ["a", 0.01, 0.01],
            ["E", 0.01, 0.10],
            # 清空能量
            ["j", 0.05, 0.17],
            ["a", 0.05, 0.10],
            ["a", 0.05, 0.00],  # 多一个普攻
            # ["Q", 0.05, 0],
            # 间隔
            ["w", 0.00, 0.55],
        ]

    # def a3Eaz(self):
    #     logger.debug("a3Eaz")
    #     return [
    #         # 3a E az
    #         ["a", 0.05, 0.31],
    #         ["a", 0.05, 0.43],
    #         ["a", 0.05, 0.40],
    #         # ["E", 0.05, 0.32],
    #         ["E", 0.05, 0.00],
    #         ["a", 0.05, 0.32],
    #
    #         ["a", 0.05, 0.35],
    #         # 清空能量
    #         ## 常规重击
    #         # ["z", 0.50, 0.45],
    #         ["z", 0.50, 0.05],
    #         ["a", 0.05, 0.05],  # 多一个普攻打断z防止一直飞
    #         ["a", 0.05, 0.05],  # 多一个普攻打断z防止一直飞
    #     ]

    def a3Ea(self):
        logger.debug("a3Ea")
        return [
            # 3a E az
            ["a", 0.05, 0.31],
            # ["a", 0.05, 0.43],  # 拆分
            ["a", 0.05, 0.18],
            ["a", 0.05, 0.20],
            # ["a", 0.05, 0.40],  # 拆分
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.15],
            # ["E", 0.05, 0.32],
            ["E", 0.05, 0.00],
            ["a", 0.05, 0.32],  # E后接a，防止E没好原地发呆

            ["a", 0.05, 0.35],
        ]

    def a2(self):
        logger.debug("a2")
        return [
            # 2a
            ["a", 0.05, 0.31],
            # ["a", 0.05, 0.43],  # 拆分
            ["a", 0.05, 0.18],
            ["a", 0.05, 0.20],
        ]

    def a3(self):
        logger.debug("a3")
        return [
            # 3a
            ["a", 0.05, 0.31],
            # ["a", 0.05, 0.43],  # 拆分
            ["a", 0.05, 0.18],
            ["a", 0.05, 0.20],
            # ["a", 0.05, 0.40],  # 拆分
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.15],
        ]

    def za(self):
        logger.debug("za")
        return [
            # 清空能量
            ## 常规重击
            # ["z", 0.50, 0.45],
            ["z", 0.50, 0.05],
            ["a", 0.05, 0.05],  # 多一个普攻打断z防止一直飞
            ["a", 0.05, 0.05],  # 多一个普攻打断z防止一直飞
        ]

    def Q(self):
        logger.debug("Q")
        return [
            ["Q", 0.05, 0.10],
        ]

    def R(self):
        logger.debug("R")
        return [
            ["R", 0.05, 3.08],
        ]

    def full_combo(self):
        # 测试用，一整套连招
        # return self.COMBO_SEQ_0
        return self.COMBO_SEQ

    def combo(self):
        try:
            img = self.img_service.screenshot()
            # energy_count = self.energy_count(img)
            # is_concerto_energy_ready = self.is_concerto_energy_ready(img)
            # is_resonance_skill_ready = self.is_resonance_skill_ready(img)
            # is_echo_skill_ready = self.is_echo_skill_ready(img)
            is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
            # boss_hp = self.boss_hp(img)

            # 性价比a3
            self.combo_action(self.a3(), True)

            # 协星调律
            if is_resonance_liberation_ready:
                self.combo_action(self.E(), False)
                self.combo_action(self.R(), True)
                return

            ## 打满能量

            img = self.img_service.screenshot()
            energy_count = self.energy_count(img)
            is_resonance_skill_ready = self.is_resonance_skill_ready(img)
            is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
            boss_hp = self.boss_hp(img)

            if energy_count == 3 and is_resonance_skill_ready and boss_hp > 0.01:
                self.combo_action(self.zaEja(), False)
                self.combo_action(self.Q(), False)
                return

            self.combo_action(self.E(), not is_resonance_liberation_ready)
            self.combo_action(self.R(), is_resonance_liberation_ready)
            # 不打z，改成ja。防止击败boss时停卡掉按键，导致变成蝴蝶飞出场外
            if energy_count == 5:
                self.combo_action(self.ja(), False)

            self.combo_action(self.Q(), False)
        except StopError as e:
            self.control_service.jump()  # 打断守岸人变身蝴蝶
            raise e