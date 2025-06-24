import logging
import time

import numpy as np

from src.core.combat.combat_core import ColorChecker, BaseResonator, BaseCombo, CharClassEnum
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseCartethyia(BaseResonator):

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service)
        self.img_service = img_service

        self.name = "卡提希娅"
        self.name_en = "cartethyia"

        # 协奏 左下血条旁绿圈
        self._concerto_energy_checker = ColorChecker.concerto_aero()

        ### 常态 小卡技能

        # 共鸣技能 E 卡提希娅
        self._resonance_skill_cartethyia_point = [(1050, 631), (1065, 635), (1079, 631)]
        self._resonance_skill_cartethyia_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_cartethyia_checker = ColorChecker(
            self._resonance_skill_cartethyia_point, self._resonance_skill_cartethyia_color,
            logic=ColorChecker.LogicEnum.AND)

        # 声骸技能
        self._echo_skill_point = [(1132, 654), (1138, 655)]
        self._echo_skill_color = [(255, 255, 255)]  # BGR
        self._echo_skill_checker = ColorChecker(self._echo_skill_point, self._echo_skill_color)

        # 共鸣解放 R 听骑士从心祈愿
        self._resonance_liberation_point = [(1195, 655), (1201, 662), (1210, 664), (1216, 656)]
        self._resonance_liberation_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_checker = ColorChecker(
            self._resonance_liberation_point, self._resonance_liberation_color, logic=ColorChecker.LogicEnum.AND)

        ### 大卡技能

        # 共鸣技能 E1 芙露德莉斯 此剑为潮浪之意
        self._resonance_skill_fleurdelys_point = [(1064, 624), (1055, 657), (1075, 656)]
        self._resonance_skill_fleurdelys_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_fleurdelys_checker = ColorChecker(
            self._resonance_skill_fleurdelys_point, self._resonance_skill_fleurdelys_color,
            logic=ColorChecker.LogicEnum.AND)

        # 共鸣技能 E2 芙露德莉斯 凭风斩浪破敌
        self._resonance_skill_fleurdelys_2_point = [(1071, 655), (1074, 661), (1076, 663)]
        self._resonance_skill_fleurdelys_2_color = [(255, 255, 255)]  # BGR
        self._resonance_skill_fleurdelys_2_checker = ColorChecker(
            self._resonance_skill_fleurdelys_2_point, self._resonance_skill_fleurdelys_2_color,
            logic=ColorChecker.LogicEnum.AND)

        # 化身显示的是当前形态，切换有1.5秒冷却

        # 共鸣解放 R 化身·芙露德莉斯
        self._resonance_liberation_avatar_fleurdelys_point = [(1206, 631), (1207, 661), (1208, 663), (1193, 639)]
        self._resonance_liberation_avatar_fleurdelys_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_avatar_fleurdelys_checker = ColorChecker(
            self._resonance_liberation_avatar_fleurdelys_point, self._resonance_liberation_avatar_fleurdelys_color,
            logic=ColorChecker.LogicEnum.AND)

        # 共鸣解放 R 化身·卡提希娅
        self._resonance_liberation_avatar_cartethyia_point = [(1207, 661), (1208, 663), (1203, 661)]
        self._resonance_liberation_avatar_cartethyia_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_avatar_cartethyia_checker = ColorChecker(
            self._resonance_liberation_avatar_cartethyia_point, self._resonance_liberation_avatar_cartethyia_color,
            logic=ColorChecker.LogicEnum.AND)

        # 共鸣解放 R 看潮怒风哮之刃
        self._resonance_liberation_blade_of_howling_squall_point = [(1198, 641), (1206, 636), (1211, 644), (1194, 634)]
        self._resonance_liberation_blade_of_howling_squall_color = [(255, 255, 255)]  # BGR
        self._resonance_liberation_blade_of_howling_squall_checker = ColorChecker(
            self._resonance_liberation_blade_of_howling_squall_point,
            self._resonance_liberation_blade_of_howling_squall_color,
            logic=ColorChecker.LogicEnum.AND)

        ### 状态识别

        # 剑一 重击 异权剑
        self._sword_of_discord_point = [(567, 663), (575, 663)]
        self._sword_of_discord_color = [(255, 255, 255)]  # BGR
        self._sword_of_discord_checker = ColorChecker(
            self._sword_of_discord_point, self._sword_of_discord_color, logic=ColorChecker.LogicEnum.AND)

        # 剑二 普攻 神权剑
        self._sword_of_divinity_point = [(634, 663), (633, 663), (627, 667), (640, 667)]
        self._sword_of_divinity_color = [(255, 255, 255), (189, 194, 119), (106, 122, 50)]  # BGR
        self._sword_of_divinity_checker = ColorChecker(
            self._sword_of_divinity_point, self._sword_of_divinity_color)

        # 剑三 E   人权剑
        self._sword_of_virtue_point = [(692, 658), (701, 658), (690, 667), (703, 667)]
        self._sword_of_virtue_color = [(255, 255, 255), (147, 79, 67)]  # BGR
        self._sword_of_virtue_checker = ColorChecker(
            self._sword_of_virtue_point, self._sword_of_virtue_color)

        # 显化
        self._manifest_point = [(620, 679), (648, 679)]
        self._manifest_color = [(255, 255, 255)]  # BGR
        self._manifest_checker = ColorChecker(self._manifest_point, self._manifest_color,
                                              logic=ColorChecker.LogicEnum.AND)
        # 决意 大卡血条上方能量条 仅大卡可见
        self._conviction_point = [(543, 668), (544, 668)]
        self._conviction_color = [
            (170, 161, 160),  # 灰色空能量
            (251, 187, 114),  # 蓝色能量未全满
            (255, 241, 135), (255, 254, 165), (242, 201, 117),   # 绿色满能量
        ]  # BGR
        self._conviction_checker = ColorChecker(self._conviction_point, self._conviction_color)

        # self._cartethyia_point = [(567, 663), (575, 663)]
        # self._cartethyia_color = [(225, 237, 83)]  # BGR
        # self._cartethyia_checker = ColorChecker(self._cartethyia_point, self._cartethyia_color)

    def __str__(self):
        return self.name_en

    def char_class(self) -> list[CharClassEnum]:
        return [CharClassEnum.MainDPS]

    def is_concerto_energy_ready(self, img: np.ndarray) -> bool:
        is_ready = self._concerto_energy_checker.check(img)
        logger.debug(f"{self.name}-协奏: {is_ready}")
        return is_ready

    def is_resonance_skill_cartethyia_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_skill_cartethyia_checker.check(img)
        logger.debug(f"{self.name}-共鸣技能-卡提希娅: {is_ready}")
        return is_ready

    def is_echo_skill_ready(self, img: np.ndarray) -> bool:
        is_ready = self._echo_skill_checker.check(img)
        logger.debug(f"{self.name}-声骸技能: {is_ready}")
        return is_ready

    def is_resonance_liberation_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_checker.check(img)
        logger.debug(f"{self.name}-共鸣解放: {is_ready}")
        return is_ready

    def is_resonance_skill_fleurdelys_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_skill_fleurdelys_checker.check(img)
        logger.debug(f"{self.name}-共鸣技能 E1 芙露德莉斯: {is_ready}")
        return is_ready

    def is_resonance_skill_fleurdelys_2_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_skill_fleurdelys_checker.check(img)
        logger.debug(f"{self.name}-共鸣技能 E2 芙露德莉斯: {is_ready}")
        return is_ready

    def is_resonance_liberation_avatar_fleurdelys_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_avatar_fleurdelys_checker.check(img)
        logger.debug(f"{self.name}-共鸣解放 R 化身·芙露德莉斯: {is_ready}")
        return is_ready

    def is_resonance_liberation_avatar_cartethyia_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_avatar_cartethyia_checker.check(img)
        logger.debug(f"{self.name}-共鸣解放 R 化身·卡提希娅: {is_ready}")
        return is_ready

    def is_resonance_liberation_blade_of_howling_squall_ready(self, img: np.ndarray) -> bool:
        is_ready = self._resonance_liberation_blade_of_howling_squall_checker.check(img)
        logger.debug(f"{self.name}-共鸣解放 R 看潮怒风哮之刃: {is_ready}")
        return is_ready

    def is_sword_of_discord_existing(self, img: np.ndarray) -> bool:
        is_existing = self._sword_of_discord_checker.check(img)
        logger.debug(f"{self.name}-剑一 异权剑: {is_existing}")
        return is_existing

    def is_sword_of_divinity_existing(self, img: np.ndarray) -> bool:
        is_existing = self._sword_of_divinity_checker.check(img)
        logger.debug(f"{self.name}-剑二 神权剑: {is_existing}")
        return is_existing

    def is_sword_of_virtue_existing(self, img: np.ndarray) -> bool:
        is_existing = self._sword_of_virtue_checker.check(img)
        logger.debug(f"{self.name}-剑三 人权剑: {is_existing}")
        return is_existing

    def is_manifest_existing(self, img: np.ndarray) -> bool:
        is_existing = self._manifest_checker.check(img)
        logger.debug(f"{self.name}-显化: {is_existing}")
        return is_existing

    def is_conviction_existing(self, img: np.ndarray) -> bool:
        is_existing = self._conviction_checker.check(img)
        logger.debug(f"{self.name}-决意条: {is_existing}")
        return is_existing


class Cartethyia(BaseCartethyia, BaseCombo):
    # COMBO_SEQ 为训练场单人静态完整连段，后续开发以此为准从中拆分截取

    # 常规轴
    COMBO_SEQ = [
        # 小卡
        # 普攻4a 召唤神权剑
        ["a", 0.05, 0.36],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        ["a", 0.05, 1.20],
        ["j", 0.05, 1.20],

        # 重击 召唤异权剑
        ["z", 0.92, 0.48],
        ["j", 0.05, 1.20],

        # Ea 召唤人权剑 收剑
        ["E", 0.05, 1.00],
        ["a", 0.05, 0.92],
        ["j", 0.05, 1.20],

        # 下落攻击 收剑
        ["j", 0.05, 0.24],
        ["a", 0.05, 0.80],
        ["j", 0.05, 1.20],

        # R
        ["R", 0.05, 4.00],
        ["j", 0.05, 1.20],
        ["w", 0.00, 1.20],

        # 大卡
        # 普攻5a
        ["a", 0.05, 0.32],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.82],
        ["a", 0.05, 1.02],
        ["a", 0.05, 0.90],
        ["j", 0.05, 1.20],
        ["w", 0.00, 1.20],

        # EaaEaaa
        ["E", 0.05, 0.93],
        ["a", 0.05, 0.68],
        ["a", 0.05, 1.20],
        ["E", 0.05, 1.65],
        ["a", 0.05, 0.82],
        ["a", 0.05, 1.02],
        ["a", 0.05, 0.90],
        ["j", 0.05, 1.20],
        ["w", 0.00, 1.20],

        # R
        # ["R", 0.05, 7.20],
        ["R", 0.05, 9.40],
        ["w", 0.05, 1.20],

    ]

    # 进阶轴1
    COMBO_SEQ_1 = [
        # 小卡

        # 先打一套三剑下劈

        # 普攻4a
        ["a", 0.05, 0.33],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        # ["a", 0.05, 1.20],
        ["a", 0.05, 0.70],

        ["z", 0.70, 0.50],

        ["E", 0.05, 1.00],
        ["a", 0.05, 1.10],

        # R
        ["R", 0.05, 3.60],

        # 变大卡
        # 普攻5a
        # ["a", 0.05, 0.32],
        ["a", 0.05, 0.10],
        ["a", 0.05, 0.20],
        ["a", 0.05, 0.65],
        ["a", 0.05, 0.82],
        ["a", 0.05, 1.02],
        ["a", 0.05, 0.90],

        # EaaEaaa
        ["E", 0.05, 0.93],
        ["a", 0.05, 0.68],
        ["a", 0.05, 1.20],
        # ["E", 0.05, 1.65],
        ["E", 0.05, 1.10],

        # 切小卡

        ["R", 0.05, 1.10],

        # 再打一套三剑下劈

        # 普攻4a 显化切小卡从第二段普攻开始打
        # ["a", 0.05, 0.33],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        # ["a", 0.05, 1.20],
        ["a", 0.05, 0.70],

        ["z", 0.70, 0.50],

        ["E", 0.05, 1.00],
        ["a", 0.05, 1.10],

        # 切大卡
        ["R", 0.05, 0.65],

        # 普攻5a 化身卡提希娅切回芙露德莉斯从普攻第三段开始打
        # ["a", 0.05, 0.32],
        # ["a", 0.05, 0.65],
        ["a", 0.05, 0.82],
        ["a", 0.05, 1.02],
        ["a", 0.05, 0.90],

        # R
        # ["R", 0.05, 7.20],
        ["R", 0.05, 9.40],
        ["w", 0.05, 1.20],
    ]

    # 进阶轴2
    COMBO_SEQ_2 = [
        # 小卡
        # R
        ["R", 0.05, 3.60],

        # 切小卡
        ["w", 0.00, 0.20],
        ["R", 0.05, 1.10],

        # 再打一套三剑下劈

        # 普攻4a 显化切小卡从第二段普攻开始打
        # ["a", 0.05, 0.33],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        # ["a", 0.05, 1.20],
        ["a", 0.05, 0.70],

        ["z", 0.70, 0.50],

        ["E", 0.05, 1.00],
        ["a", 0.05, 1.10],

        # 切大卡
        ["R", 0.05, 0.65],

        # 普攻5a 化身卡提希娅切回芙露德莉斯从普攻第三段开始打
        # ["a", 0.05, 0.32],
        # ["a", 0.05, 0.65],
        ["a", 0.05, 0.82],
        ["a", 0.05, 1.02],
        ["a", 0.05, 0.90],

        # EaaEaaa
        ["E", 0.05, 0.93],
        ["a", 0.05, 0.68],
        ["a", 0.05, 1.20],
        ["E", 0.05, 1.65],
        ["a", 0.05, 0.82],
        ["a", 0.05, 1.02],
        ["a", 0.05, 0.90],

        # R
        ["R", 0.05, 5.20],

        # 普攻4a
        ["a", 0.05, 0.33],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        # ["a", 0.05, 1.20],
        ["a", 0.05, 0.70],

        ["z", 0.70, 0.50],

        ["E", 0.05, 1.00],
        ["a", 0.05, 1.10],

        # 普攻4a
        ["a", 0.05, 0.33],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        # ["a", 0.05, 1.20],
        ["a", 0.05, 0.70],
        ["w", 0.00, 1.20],

        # 普攻4a
        ["a", 0.05, 0.33],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.84],
        # ["a", 0.05, 1.20],
        ["a", 0.05, 0.70],
        ["w", 0.00, 1.20],

    ]

    def __init__(self, control_service: ControlService, img_service: ImgService):
        super().__init__(control_service, img_service)

    def cartethyia_a4(self):
        logger.debug("cartethyia_a4")
        return [
            # 小卡
            # 普攻4a 召唤神权剑
            ["a", 0.05, 0.36],
            ["a", 0.05, 0.67],
            ["a", 0.05, 0.84],
            # ["a", 0.05, 1.20],  # 拆分
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.20],
            ["w", 0.00, 0.75],
        ]

    def cartethyia_a2_start(self):
        logger.debug("cartethyia_a2_start")
        return [
            # 普攻前两下
            ["a", 0.05, 0.36],
            # ["a", 0.05, 0.67],
            ["a", 0.05, 0.37],
            ["w", 0.00, 0.30],
        ]

    def cartethyia_a2_end(self):
        logger.debug("cartethyia_a2_end")
        return [
            # 普攻后两下
            # ["a", 0.05, 0.84],  # 拆分
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],

            # ["a", 0.05, 1.20],  # 拆分
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.20],
            ["w", 0.00, 0.75],
        ]

    def cartethyia_a2_end_z(self):
        logger.debug("cartethyia_a2_end_z")
        return [
            # 普攻后两下
            # ["a", 0.05, 0.84],  # 拆分
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],
            ["a", 0.05, 0.25],

            # ["a", 0.05, 1.20],
            # ["a", 0.05, 0.70],
            ["a", 0.05, 0.30],
            ["a", 0.05, 0.35],

            ["z", 0.70, 0.50],
        ]

    def cartethyia_a4zEa(self):
        logger.debug("cartethyia_a4zEa")
        return [
            # 小卡
            # 普攻4a
            ["a", 0.05, 0.33],
            ["a", 0.05, 0.67],
            ["a", 0.05, 0.84],
            # ["a", 0.05, 1.20],
            ["a", 0.05, 0.70],

            ["z", 0.70, 0.50],

            ["E", 0.05, 1.00],
            # ["a", 0.05, 1.10],
            ["a", 0.05, 0.20],
            ["w", 0.00, 0.90],
        ]

    def cartethyia_Ea(self):
        logger.debug("cartethyia_Ea")
        return [
            # Ea 召唤人权剑 收剑
            ["E", 0.05, 1.00],
            ["a", 0.05, 1.10],
        ]

    def cartethyia_ja(self):
        logger.debug("cartethyia_ja")
        return [
            # 下落攻击 收剑
            ["j", 0.05, 0.20],
            ["a", 0.05, 0.80],
        ]

    def cartethyia_R(self):
        logger.debug("cartethyia_R")
        return [
            ["R", 0.05, 3.60],
        ]

    def cartethyia_R_full_combo(self):
        logger.debug("cartethyia_R_full_combo")
        return [
            # R
            ["R", 0.05, 3.60],

            # 变大卡
            # 普攻5a
            # ["a", 0.05, 0.32],
            ["a", 0.05, 0.10],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.65],
            ["a", 0.05, 0.82],
            ["a", 0.05, 1.02],
            ["a", 0.05, 0.90],

            # EaaEaaa
            ["E", 0.05, 0.93],
            ["a", 0.05, 0.68],
            ["a", 0.05, 1.20],
            # ["E", 0.05, 1.65],
            ["E", 0.05, 1.10],

            # 切小卡

            ["R", 0.05, 1.10],

            # 再打一套三剑下劈

            # 普攻4a 显化切小卡从第二段普攻开始打
            # ["a", 0.05, 0.33],
            ["a", 0.05, 0.67],
            ["a", 0.05, 0.84],
            # ["a", 0.05, 1.20],
            ["a", 0.05, 0.70],

            ["z", 0.70, 0.50],

            ["E", 0.05, 1.00],
            ["a", 0.05, 1.10],

            # 切大卡
            ["R", 0.05, 0.65],

            # 普攻5a 化身卡提希娅切回芙露德莉斯从普攻第三段开始打
            # ["a", 0.05, 0.32],
            # ["a", 0.05, 0.65],
            ["a", 0.05, 0.82],
            ["a", 0.05, 1.02],
            ["a", 0.05, 0.90],

            # R
            ["R", 0.05, 5.20],
        ]

    def fleurdelys_a5(self):
        logger.debug("fleurdelys_a5")
        return [
            # 大卡
            # 普攻5a
            # ["a", 0.05, 0.32],
            ["a", 0.05, 0.10],
            ["a", 0.05, 0.20],
            ["a", 0.05, 0.65],
            ["a", 0.05, 0.82],
            ["a", 0.05, 1.02],
            ["a", 0.05, 0.90],
        ]

    def fleurdelys_Ra3(self):
        logger.debug("fleurdelys_a5")
        return [
            # 切大卡
            ["R", 0.05, 0.65],

            # 普攻5a 化身卡提希娅切回芙露德莉斯从普攻第三段开始打
            # ["a", 0.05, 0.32],
            # ["a", 0.05, 0.65],
            ["a", 0.05, 0.82],
            ["a", 0.05, 1.02],
            ["a", 0.05, 0.90],
        ]

    def fleurdelys_zaa3(self):
        logger.debug("fleurdelys_zaa3")
        return [
            # 大卡
            # 普攻5a
            ["z", 0.90, 0.31],
            ["a", 0.05, 0.93],
            ["a", 0.05, 0.50],
            ["a", 0.05, 0.68],
            ["a", 0.05, 1.20],
        ]

    def fleurdelys_EaaEaaa(self):
        logger.debug("fleurdelys_EaaEaaa")
        return [
            # 大卡
            # EaaEaaa
            ["E", 0.05, 0.93],
            ["a", 0.05, 0.68],
            ["a", 0.05, 1.20],
            ["E", 0.05, 1.65],
            ["a", 0.05, 0.82],
            ["a", 0.05, 1.02],
            ["a", 0.05, 0.90],
        ]

    def fleurdelys_R_blade_of_howling_squall(self):
        logger.debug("R")
        return [
            ["R", 0.05, 3.60],
        ]

    def Q(self):
        logger.debug("Q")
        return [
            # 声骸技能
            ["Q", 0.05, 0.00],
        ]

    def full_combo(self):
        # 测试用，一整套连招
        return self.COMBO_SEQ

    def combo(self):
        # 变奏后摇1.2s
        # 空中切人，附近有怪，自动打下落攻击，后摇0.8s，没人则在地面
        # 地面切人，附近有怪，自动打普攻第二段

        # 风蚀效应持续15s
        # 普攻第四段叠一层
        # E技能叠两层

        self.combo_action(self.cartethyia_a2_start(), False)

        start_time = time.monotonic()

        img = self.img_service.screenshot()
        # 常态 小卡技能
        # is_concerto_energy_ready = self.is_concerto_energy_ready(img)
        is_resonance_skill_cartethyia_ready = self.is_resonance_skill_cartethyia_ready(img)
        # is_echo_skill_ready = self.is_echo_skill_ready(img)
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        # 大卡技能
        is_resonance_skill_fleurdelys_ready = self.is_resonance_skill_fleurdelys_ready(img)
        is_resonance_skill_fleurdelys_2_ready = self.is_resonance_skill_fleurdelys_2_ready(img)
        is_resonance_liberation_avatar_fleurdelys_ready = self.is_resonance_liberation_avatar_fleurdelys_ready(img)
        is_resonance_liberation_avatar_cartethyia_ready = self.is_resonance_liberation_avatar_cartethyia_ready(img)
        is_resonance_liberation_blade_of_howling_squall_ready = self.is_resonance_liberation_blade_of_howling_squall_ready(img)
        # 状态
        is_sword_of_discord_existing = self.is_sword_of_discord_existing(img)
        is_sword_of_divinity_existing = self.is_sword_of_divinity_existing(img)
        is_sword_of_virtue_existing = self.is_sword_of_virtue_existing(img)
        is_manifest_existing = self.is_manifest_existing(img)
        is_conviction_existing = self.is_conviction_existing(img)

        boss_hp = self.boss_hp(img)

        self.combo_action(self.Q(), False)

        use_seconds = time.monotonic() - start_time
        time.sleep(max(0.0, 0.30 - use_seconds))

        # 化身·芙露德莉斯 有大开大
        if is_resonance_liberation_blade_of_howling_squall_ready:
            self.combo_action(self.fleurdelys_R_blade_of_howling_squall(), True)
            # 若小卡E转好了再打一个三剑下劈
            img = self.img_service.screenshot()
            is_resonance_skill_cartethyia_ready = self.is_resonance_skill_cartethyia_ready(img)
            if is_resonance_skill_cartethyia_ready:
                self.combo_action(self.cartethyia_a4zEa(), False)
            return
        
        # 化身·卡提希娅 打一套三剑下劈
        avatar_cartethyia_to_fleurdelys = False
        if is_resonance_liberation_avatar_cartethyia_ready:
            if is_resonance_skill_cartethyia_ready:
                self.combo_action(self.cartethyia_a4zEa(), True)
                avatar_cartethyia_to_fleurdelys = True
            else:
                self.combo_action(self.cartethyia_a4(), False)
                return 

        # 化身·芙露德莉斯 决意未满
        if is_resonance_liberation_avatar_fleurdelys_ready or avatar_cartethyia_to_fleurdelys:
            if avatar_cartethyia_to_fleurdelys:
                self.combo_action(self.fleurdelys_Ra3(), True)
            elif is_resonance_skill_fleurdelys_ready:
                self.combo_action(self.fleurdelys_EaaEaaa(), True)
            else:
                self.combo_action(self.fleurdelys_a5(), True)

            # 有E打空中，没有打普攻，补决意
            img = self.img_service.screenshot()
            is_resonance_skill_fleurdelys_ready = self.is_resonance_skill_fleurdelys_ready(img)
            is_resonance_liberation_blade_of_howling_squall_ready = self.is_resonance_liberation_blade_of_howling_squall_ready(img)
            if not is_resonance_liberation_blade_of_howling_squall_ready:
                if is_resonance_skill_fleurdelys_ready:
                    self.combo_action(self.fleurdelys_EaaEaaa(), True)
                else:
                    self.combo_action(self.fleurdelys_a5(), True)

            # 决意还没满，补一个重击派生
            img = self.img_service.screenshot()
            is_resonance_liberation_blade_of_howling_squall_ready = self.is_resonance_liberation_blade_of_howling_squall_ready(img)
            if not is_resonance_liberation_blade_of_howling_squall_ready:
                self.combo_action(self.fleurdelys_zaa3(), True)

            # 开大
            img = self.img_service.screenshot()
            is_resonance_liberation_blade_of_howling_squall_ready = self.is_resonance_liberation_blade_of_howling_squall_ready(img)
            if is_resonance_liberation_blade_of_howling_squall_ready:
                self.combo_action(self.fleurdelys_R_blade_of_howling_squall(), True)
                # 若小卡E转好了再打一个三剑下劈
                img = self.img_service.screenshot()
                is_resonance_skill_cartethyia_ready = self.is_resonance_skill_cartethyia_ready(img)
                if is_resonance_skill_cartethyia_ready:
                    self.combo_action(self.cartethyia_a4zEa(), False)
            return

        # 常态 卡提希娅 有E或R TODO 根据状态栏剑一剑二剑三，动态攒剑
        if is_resonance_skill_cartethyia_ready or is_resonance_liberation_ready:
            # 先打剑二剑一
            self.combo_action(self.cartethyia_a2_end_z(), True)
            # 有E打剑三，接三剑下劈
            if is_resonance_skill_cartethyia_ready:
                self.combo_action(self.cartethyia_Ea(), True)
            else:
                # 再检查E是否转好
                img = self.img_service.screenshot()
                is_resonance_skill_cartethyia_ready = self.is_resonance_skill_cartethyia_ready(img)
                # 接着打三剑，没有也直接收剑
                if is_resonance_skill_cartethyia_ready:
                    self.combo_action(self.cartethyia_Ea(), True)
                else:
                    self.combo_action(self.cartethyia_ja(), True)

            # 再看看大招好了没有
            if not is_resonance_liberation_ready:
                img = self.img_service.screenshot()
                is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
            # 大招还没好，结束
            if not is_resonance_liberation_ready:
                return

            self.combo_action(self.Q(), False)
            # 开大
            self.combo_action(self.cartethyia_R_full_combo(), True)
            return

        self.combo_action(self.cartethyia_a4(), False)

