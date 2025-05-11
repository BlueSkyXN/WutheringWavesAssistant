import logging
import threading
import time
from enum import Enum
from typing import Sequence

import numpy as np

from src.core.exceptions import StopError
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class BaseChecker:

    def __init__(self):
        self.unit = (1280, 720)  # 坐标参考系，默认使用1280x720下的坐标，根据传入的图片动态等比缩放

    def check(self, img: np.ndarray) -> bool:
        pass

    def get_scale(self, img: np.ndarray) -> float:
        h, w = img.shape[:2]
        if abs(w / h - self.unit[0] / self.unit[1]) > 0.05:
            raise ValueError("不支持的像素比例，请使用16:9")
        scale = w / self.unit[0]
        # logger.debug(f"scale: {scale:.4f}")
        return scale


class ColorChecker(BaseChecker):
    class LogicEnum(Enum):
        """
        多点匹配，逻辑或、与
        """
        OR = "or"
        AND = "and"

    def __init__(self, points: Sequence[tuple[int, int]], colors: Sequence[tuple[int, int, int]], tolerance=30,
                 logic=LogicEnum.OR):
        super().__init__()
        self.points = points  # 坐标 x,y
        self.colors = np.array(colors)  # BGR
        self.tolerance = tolerance  # 容差
        self.logic = logic

    def check(self, img: np.ndarray) -> bool:
        if self.points is None or len(self.points) == 0:
            raise ValueError("Points is empty")
        if self.logic == self.LogicEnum.OR:
            # 多点匹配，一点的颜色匹配上就为真
            scale = self.get_scale(img)
            for point in self.points:
                target = img[int(scale * point[1]), int(scale * point[0])]
                # logger.debug(f"target: {target}")
                # 颜色按或匹配
                for sample in self.colors:
                    if np.all(np.abs(sample - target) <= self.tolerance):  # 容差匹配
                        # logger.debug(f"sample: {sample}")
                        return True
            return False
        elif self.logic == self.LogicEnum.AND:
            # 多点匹配，所有点的颜色都匹配才为真
            scale = self.get_scale(img)
            for point in self.points:
                target = img[int(scale * point[1]), int(scale * point[0])]
                # logger.debug(f"target: {target}")
                # 颜色按或匹配
                is_color_match = False
                for sample in self.colors:
                    if np.all(np.abs(sample - target) <= self.tolerance):  # 容差匹配
                        # logger.debug(f"sample: {sample}")
                        is_color_match = True
                        break
                if not is_color_match:
                    return False
            return True
        raise NotImplementedError("Unknown logic")


class BaseCombo:
    """ 连招 """

    def __init__(self, control_service: ControlService):
        self.control_service = control_service
        self.event: threading.Event | None = None

    def combo_action(self, sequence: Sequence, end_wait: bool):
        """
        执行按键序列
        :param sequence:
        :param end_wait: 队列最后一个按键是否睡眠等待后摇时间，用于合轴，False不等就是一放就切，True等待就是放完技能结束才切
        :return:
        """
        max_size = len(sequence)
        for i, keys in enumerate(sequence):
            if self.event is not None and not self.event.is_set():
                raise StopError()
            if i % 2 == 0:
                self.control_service.fight_tap("F", 0.001)
            key, press_time, wait_time = keys[:3]
            if key == "a":
                if press_time > 0.2:
                    raise ValueError("普攻按压时间不可大于0.2，默认统一填写0.05")
                self.control_service.fight_click(0, 0, press_time)
            elif key == "z":
                if press_time < 0.3:
                    raise ValueError("重击按压时间不可小于0.3，默认统一写0.5")
                self.control_service.fight_click(0, 0, press_time)
            # elif key == "w":
            #     time.sleep(wait_time)
            elif key == "j":
                self.control_service.fight_tap("SPACE", press_time)
            elif key == "d":
                self.control_service.fight_tap("LSHIFT", press_time)
            else:
                key_action = keys[3] if len(keys) >= 4 else None
                if key_action == "down":
                    self.control_service.key_down(key, press_time)
                elif key_action == "up":
                    self.control_service.key_up(key, press_time)
                else:
                    self.control_service.fight_tap(key, press_time)
            if wait_time <= 0:
                continue
            # 最后一下可合轴，无需等待
            if i == max_size - 1 and end_wait is False:
                break
            if self.event is not None and not self.event.is_set():
                raise StopError()
            time.sleep(wait_time)


class BaseResonator:
    """ 共鸣者 """

    def energy_count(self, img: np.ndarray) -> int:
        raise NotImplementedError()

    def is_concerto_energy_ready(self, img: np.ndarray) -> bool:
        raise NotImplementedError()

    def is_resonance_skill_ready(self, img: np.ndarray) -> bool:
        raise NotImplementedError()

    def is_echo_skill_ready(self, img: np.ndarray) -> bool:
        raise NotImplementedError()

    def is_resonance_liberation_ready(self, img: np.ndarray) -> bool:
        raise NotImplementedError()


class TeamMemberSelector:

    def __init__(self, control_service: ControlService, img_service: ImgService):
        self.control_service = control_service
        self.img_service = img_service

        self.point_1 = [(1158, 146), (1166, 143)]
        self.point_2 = [(1159, 234), (1167, 231)]
        self.point_3 = [(1159, 322), (1167, 319)]
        self.colors = [(247, 250, 254)]

        # team_member 1
        self._team_member_1_point = [*self.point_2, *self.point_3]
        self._team_member_1_color = self.colors
        self._team_member_1_checker = ColorChecker(
            self._team_member_1_point, self._team_member_1_color, 20, logic=ColorChecker.LogicEnum.AND)

        # team_member 2
        self._team_member_2_point = [*self.point_1, *self.point_3]
        self._team_member_2_color = self.colors
        self._team_member_2_checker = ColorChecker(
            self._team_member_2_point, self._team_member_2_color, 20, logic=ColorChecker.LogicEnum.AND)

        # team_member 3
        self._team_member_3_point = [*self.point_1, *self.point_2]
        self._team_member_3_color = self.colors
        self._team_member_3_checker = ColorChecker(
            self._team_member_3_point, self._team_member_3_color, 20, logic=ColorChecker.LogicEnum.AND)

        self._team_member_map = {
            1: self._team_member_1_checker,
            2: self._team_member_2_checker,
            3: self._team_member_3_checker,
        }

    def toggle(self, member: int, timeout_seconds: float = 1.0, event: threading.Event | None = None) -> bool:
        team_member_checker = self._team_member_map.get(member)
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_seconds:
            if event is not None and not event.is_set():
                return False
            self.control_service.toggle_team_member(member)
            time.sleep(0.15)
            img = self.img_service.screenshot()
            is_toggled = team_member_checker.check(img)
            if is_toggled:
                return True
        return False

# circular import
# class CombatSystem:
