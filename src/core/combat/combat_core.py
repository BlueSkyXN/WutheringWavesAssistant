import logging
import random
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
    """ 像素颜色校验器 """

    class LogicEnum(Enum):
        """
        多点匹配，逻辑或、与
        """
        OR = "or"
        AND = "and"

    def __init__(self, points: Sequence[tuple[int, int]], colors: Sequence[tuple[int, int, int]], tolerance: int = 30,
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
            # 多点匹配，一个点的颜色匹配上就为真
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

    @staticmethod
    def concerto_spectro():
        """ 衍射 协奏能量校验器，左下血条旁黄圈 """
        concerto_energy_point = [(513, 669), (514, 669), (514, 670), (514, 671)]
        concerto_energy_color = [(105, 204, 217)]  # BGR
        return ColorChecker(concerto_energy_point, concerto_energy_color)

    @staticmethod
    def concerto_fusion():
        """ 热熔 协奏能量校验器，左下血条旁红圈 """
        concerto_energy_point = [(513, 669), (514, 669), (514, 670), (514, 671)]
        concerto_energy_color = [(81, 112, 210)]  # BGR
        return ColorChecker(concerto_energy_point, concerto_energy_color)

    @staticmethod
    def concerto_havoc():
        """ 湮灭 协奏能量校验器，左下血条旁紫圈 """
        concerto_energy_point = [(513, 669), (514, 669), (514, 670), (514, 671)]
        concerto_energy_color = [(153, 77, 201)]  # BGR
        return ColorChecker(concerto_energy_point, concerto_energy_color)

    @staticmethod
    def concerto_glacio():
        """ 冷凝 协奏能量校验器，左下血条旁蓝圈 """
        concerto_energy_point = [(513, 669), (514, 669), (514, 670), (514, 671)]
        concerto_energy_color = [(222, 159, 68)]  # BGR
        return ColorChecker(concerto_energy_point, concerto_energy_color)

    @staticmethod
    def concerto_aero():
        """ 气动 协奏能量校验器，左下血条旁绿圈 """
        concerto_energy_point = [(513, 669), (514, 669), (514, 670), (514, 671)]
        concerto_energy_color = [(168, 226, 87), (171, 216, 121)]  # BGR
        return ColorChecker(concerto_energy_point, concerto_energy_color)


class BaseCombo:
    """ 连招 """

    def __init__(self, control_service: ControlService):
        self.control_service = control_service
        self.event: threading.Event | None = None
        self.is_nightmare: bool = False

    def combo_action(self, sequence: Sequence, end_wait: bool, ignore_event: bool = False):
        """
        执行按键序列
        :param sequence:
        :param end_wait: 队列最后一个按键是否睡眠等待后摇时间，用于合轴，False不等就是一放就切，True等待就是放完技能结束才切
        :param ignore_event:
        :return:
        """
        max_size = len(sequence)
        key_down_caches = set()
        tap_f_time = time.monotonic()
        for i, keys in enumerate(sequence):
            if not ignore_event and self.event is not None and not self.event.is_set():
                # 退出前释放按压的按键
                for key_down_cache in key_down_caches:
                    self.control_service.key_up(key_down_cache, 0.001)
                raise StopError()
            if self.is_nightmare:
                tap_f_cur_time = time.monotonic()
                # 限制自动F频率
                if tap_f_cur_time - tap_f_time > 0.25 or (i > 0 and i == max_size - 1):
                    tap_f_time = tap_f_cur_time
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
                    key_down_caches.add(key)
                elif key_action == "up":
                    self.control_service.key_up(key, press_time)
                    key_down_caches.discard(key)
                else:
                    self.control_service.fight_tap(key, press_time)
            if wait_time <= 0:
                continue
            # 最后一下可合轴，无需等待
            if i == max_size - 1 and end_wait is False:
                break
            if not ignore_event and self.event is not None and not self.event.is_set():
                raise StopError()
            time.sleep(wait_time)


class CharClassEnum(Enum):
    MainDPS = "MainDPS"
    SubDPS = "SubDPS"
    Support = "Support"
    Healer = "Healer"


class BaseResonator:
    """ 共鸣者 """

    def char_class(self) -> list[CharClassEnum]:
        """ 角色分类 """
        raise NotImplementedError()

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

    @classmethod
    def random_float(cls) -> float:
        return random.random()

    @classmethod
    def is_avatar_grey(cls, img: np.ndarray, member: int) -> bool:
        # 角色头像检查点，一般是中心点
        point = [1195, 168, 1]  # 坐标x,y，第三个是采样点在几号角色位
        # 右侧123号位角色血条起始点，用于定位，计算相对位置
        team_member_health_points = [(1170, 192), (1170, 280), (1170, 368)]
        if member > 1:
            member_1_point = team_member_health_points[0]
            member_n_point = team_member_health_points[member - 1]
            point = [
                point[0],
                point[1] + member_n_point[1] - member_1_point[1]
            ]
        b, g, r = img[point[1], point[0]]
        tolerance = 1  # 容差
        # uint8转为int
        is_avatar_grey = abs(int(b) - int(g)) <= tolerance and abs(int(g) - int(r)) <= tolerance
        # logger.debug("is_avatar_grey: %s", is_avatar_grey)
        return is_avatar_grey

    @classmethod
    def boss_hp(cls, img: np.ndarray) -> float:
        """ boss剩余血条比例，归一 """
        # 血条为黄到红的渐变色
        health_01_point = [(452, 41)]
        health_01_color = [(68, 179, 255)]  # BGR

        health_20_point = [(528, 41)]
        health_20_color = [(62, 164, 255)]  # BGR

        health_30_point = [(565, 41)]
        health_30_color = [(55, 148, 255)]  # BGR

        health_50_point = [(641, 41)]
        health_50_color = [(38, 109, 255)]  # BGR

        health_100_point = [(830, 41)]
        health_100_color = [(8, 37, 255)]  # BGR

        health = 0.0
        if ColorChecker(health_01_point, health_01_color).check(img):
            health = 0.01  # 这里不准，不能用来判断boss是否存活
        if ColorChecker(health_20_point, health_20_color).check(img):
            health = 0.20
            # logger.debug("boss_hp: %s", health)
        if ColorChecker(health_30_point, health_30_color).check(img):
            health = 0.30
            # logger.debug("boss_hp: %s", health)
        if ColorChecker(health_50_point, health_50_color).check(img):
            health = 0.50
            # logger.debug("boss_hp: %s", health)
        if ColorChecker(health_100_point, health_100_color).check(img):
            health = 1.00

        logger.debug("boss_hp: %s", health)
        return health

    @classmethod
    def is_boss_health_bar_exist(cls, img: np.ndarray) -> float:
        """ boss剩余血条比例，归一 """
        tolerance = 20

        # 血条为黄到红的渐变色
        health_01_point = [(449, 41)]
        health_01_color = [(68, 179, 255), (68, 168, 240), (68, 155, 219)]  # BGR
        health_01_checker = ColorChecker(health_01_point, health_01_color, tolerance=tolerance)

        health_02_point = [(452, 41), (451, 41), (450, 41)]
        # health_02_color = [(68, 179, 255), (47, 20, 37)]  # BGR
        health_02_color = [(69, 138, 194), (68, 179, 255)]  # BGR
        health_02_checker = ColorChecker(health_02_point, health_02_color, tolerance=tolerance)

        health_20_point = [(528, 41)]
        # health_20_color = [(62, 164, 255), (47, 18, 28)]  # BGR
        health_20_color = [(62, 164, 255)]  # BGR
        health_20_checker = ColorChecker(health_20_point, health_20_color, tolerance=tolerance)

        health_30_point = [(565, 41)]
        # health_30_color = [(55, 148, 255), (47, 17, 27)]  # BGR
        health_30_color = [(55, 148, 255)]  # BGR
        health_30_checker = ColorChecker(health_30_point, health_30_color, tolerance=tolerance)

        health_50_point = [(641, 41)]
        # health_50_color = [(38, 109, 255), (51, 19, 29)]  # BGR
        health_50_color = [(38, 109, 255)]  # BGR
        health_50_checker = ColorChecker(health_50_point, health_50_color, tolerance=tolerance)

        # health_100_point = [(830, 41)]
        # health_100_color = [(8, 37, 255), (65, 30, 41), (93, 80, 83)]  # BGR

        if (health_02_checker.check(img)
                or health_01_checker.check(img)
                or health_20_checker.check(img)
                or health_30_checker.check(img)
                or health_50_checker.check(img)):
            is_exist = True
        else:
            is_exist = False
        logger.debug("is_boss_health_bar_exist: %s", is_exist)
        return is_exist

    @classmethod
    def boss_is_immobilized(cls, img: np.ndarray) -> bool:
        """ boss是否已瘫痪 """
        # # 共振度，比血条略短一点点
        vibration_strength_00_point = [(453, 54)]
        # vibration_strength_20_point = [(528, 54)]
        # vibration_strength_50_point = [(641, 54)]
        # vibration_strength_100_point = [(826, 54)]
        # vibration_strength_color = [(255, 255, 255)]  # BGR

        # 瘫痪后，共振条由白色变为黄色
        immobilize_color = [(28, 235, 255)]  # BGR
        checker = ColorChecker(vibration_strength_00_point, immobilize_color)
        is_immobilized = checker.check(img)
        logger.debug("is_immobilized: %s", is_immobilized)
        return is_immobilized


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

    def get_avatars(self) -> dict[str, np.ndarray]:
        """ 获取所有角色的头像 """
        from src.util import file_util, img_util
        # 所有头像都放在一张透明图里1280x720，按网格摆放
        img_path = file_util.get_assets_template("Avatars.png")
        img = img_util.read_img(img_path, alpha=False)
        # logger.debug("img shape: %s", img.shape)
        # 头像摆放顺序
        avatar_names = [ # 重复的为皮肤或亮暗背景下的头像
            "jinhsi", "jinhsi", "changli", "changli", "changli", "shorekeeper",
            "verina", "verina", "verina", "encore", "encore", "encore",
            "camellya", "rover", "sanhua", "sanhua", "sanhua", "cantarella",
            "zani", "baizhi", "xiangliyao", "calcharo", "jianxin",
            "cartethyia"
        ]
        # 头像网格，40像素放一个，1280宽度，一行放32个
        avatar_grid = (40, 40)
        # 头像在网格内的位置，左上角0,0 到 右下角这个位置的正方形。有四个像素的空白间隙
        avatar_wh = (36, 36)
        x = 0
        y = 0
        avatar_map = {}
        for name in avatar_names:
            avatar_grid_img = img[y:y + avatar_grid[1], x:x + avatar_grid[0]]
            avatar_img = avatar_grid_img[0:avatar_wh[1], 0:avatar_wh[0]]
            avatar_map[name] = avatar_img
            # img_util.save_img_in_temp(avatar_img)
            x = x + avatar_grid[0]
            if x >= 1280:
                x = 0
                y = y + avatar_grid[1]
        return avatar_map

    def get_team_members(self, img: np.ndarray | None = None) -> list[str]:
        """
        识别画面中的角色，从上到下
        :param img: 16:9 BGR
        :return:
        """
        if img is None:
            img = self.img_service.screenshot()
            # from src.util import img_util
            # img_util.save_img_in_temp(img)
        img = self.img_service.resize(img)
        logger.debug("img shape: %s", img.shape)
        # start_col = int(img.shape[1] * 0.85)
        # img = img[:, start_col:]
        # img = img[135:372, 1168:1225]
        # 123号位角色头像在图中的区域
        member_regions = [(1167, 135, 1230, 198), (1167, 224, 1230, 285), (1167, 314, 1230, 373)]
        avatars = self.get_avatars()
        members = []
        for i, region in enumerate(member_regions):
            # 每个位置都匹配一遍头像，找出相似度最高的那个
            region_img = img[region[1]:region[3], region[0]:region[2]]
            # from src.util import img_util
            # img_util.save_img_in_temp(region_img)
            match_results = []
            for avatar_name, avatar_img in avatars.items():
                position = self.img_service.match_template(region_img, avatar_img, threshold=0.3)
                logger.debug(f"{i} avatar: {avatar_name}, position: {position}")
                if not position:
                    continue
                match_results.append((avatar_name, position.confidence))
            logger.debug(f"{i} match_results: {match_results}")
            if len(match_results) == 0:
                members.append(None)
                continue
            if len(match_results) > 1:
                match_results.sort(key=lambda x: x[1], reverse=True)  # 从大到小
            logger.debug(f"{i} match_results: {match_results}")
            members.append(match_results[0])

        logger.debug(f"members: {members}")
        member_names = []
        for i, member in enumerate(members):
            if member is None:
                logger.warning(f"无法识别{i + 1}号位角色")
                member_names.append(None)
                continue
            member_names.append(member[0])
        logger.info(f"member_names: {member_names}")
        return member_names

    def toggle(self, index: int, event: threading.Event | None,
               resonators: list[BaseResonator] | None, timeout_seconds: float = 1.0) -> bool | None:
        member = index + 1

        resonator = resonators[index]
        img = self.img_service.screenshot()
        is_avatar_grey = resonator.is_avatar_grey(img, member)
        if is_avatar_grey:
            logger.debug(f"角色{member}已阵亡，跳过")
            return None
        else:
            logger.debug(f"角色{member}存活")

        team_member_checker = self._team_member_map.get(member)
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout_seconds:
            if event is not None and not event.is_set():
                return None
            logger.debug("切换角色: %s", member)
            self.control_service.toggle_team_member(member)
            time.sleep(0.15)
            img = self.img_service.screenshot()
            is_toggled = team_member_checker.check(img)

            # from src.util import img_util
            # img_util.save_img_in_temp(img)

            if is_toggled:
                return True
            time.sleep(0.1)
        return False

    def get_cur_member_number(self) -> int | None:
        img = self.img_service.screenshot()
        for member, team_member_checker in self._team_member_map.items():
            if team_member_checker.check(img):
                return member
        return None

# circular import
# class CombatSystem:
