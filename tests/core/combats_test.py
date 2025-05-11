import logging
import time

import pytest

from src.core.combat.combat_system import CombatSystem
from src.core.combat.resonator import Shorekeeper
from src.core.contexts import Context
from src.core.injector import Container
from src.core.interface import ControlService, WindowService, ImgService

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def context():
    logger.debug("\n")
    context = Context()
    return context


@pytest.fixture(scope="module")
def container(context):
    container = Container.build(context)
    return container


@pytest.fixture(scope="module")
def control_service(container):
    control_service: ControlService = container.control_service()
    control_service.activate()
    time.sleep(0.2)
    return control_service


def combo_action(control_service, seq, after_time, cycle=50):
    for i in range(cycle):
        for keys in seq:
            key, press_time, wait_time = keys[:3]
            if key == "a":
                if press_time > 0.2:
                    raise ValueError("普攻按压时间不可大于0.2，默认统一填写0.05")
                control_service.player().fight_click(0, 0, press_time)
            elif key == "z":
                if press_time < 0.3:
                    raise ValueError("重击按压时间不可小于0.3，默认统一写0.5")
                control_service.player().fight_click(0, 0, press_time)
            elif key == "w":
                time.sleep(wait_time)
            elif key == "j":
                control_service.player().fight_tap("SPACE", press_time)
            elif key == "d":
                control_service.player().fight_tap("LSHIFT", press_time)
            else:
                key_action = keys[3] if len(keys) >= 4 else None
                if key_action == "down":
                    control_service.player().key_down(key, press_time)
                elif key_action == "up":
                    control_service.player().key_up(key, press_time)
                else:
                    control_service.player().fight_tap(key, press_time)
            if wait_time > 0:
                time.sleep(wait_time)
        time.sleep(after_time)


def test_combo_Jinhsi(control_service):
    # 大写A-Z表示键盘上的按键
    # 小写 a 代表普通攻击，默认按压0.05s
    # 小写 z 代表重击，默认按压0.5s
    # 小写 w wait，代表等待，用于设置等待时间
    # 小写 j jump，代表跳跃，用于测试后摇是否结束，跳跃能否触发会不会被吞，按压时长同普攻
    # 小写 d dodge，代表闪避，用于取消后摇

    # ["按键", "默认按压时间", "按压后等待时间，即后摇时间，需要动态调整，小于这个时间游戏会吞按键"]
    # ["a",    0.05,        0.50]
    # ["z",    0.50,        0.50]
    # ["w",    0.00,        0.50]
    # ["j",    0.05,        0.50]

    # 汐汐 BnB combo
    seq = [
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.90],
        ["a", 0.05, 0.35],
        ["E", 0.05, 0.00],
        # 间隔
        ["w", 0.00, 0.75],  # 间隔(合轴点)需足够，否则二段开始，角色却还在一段的后摇中，会吞按键

        ["a", 0.05, 0.45],
        ["a", 0.05, 0.55],
        ["a", 0.05, 0.25],
        ["E", 0.05, 0.75],
        ["a", 0.05, 0.35],
        ["a", 0.05, 0.40],
        ["E", 0.05, 0.00],
    ]
    combo_action(control_service, seq, 7.5)


def test_combo_Jinhsi_AdvancedCombo(control_service):
    # 汐汐 瞬喷 BV1sUfHYdEPG
    # 4a E闪a跳 a闪a闪 aE
    seq = [
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.90],
        ["a", 0.05, 0.40],

        ["E", 0.05, 0.05],
        ["d", 0.05, 0.20],
        ["a", 0.05, 0.05],
        ["j", 0.05, 0.01],

        ["W", 0.00, 0.00, "down"],
        ["a", 0.05, 0.05],
        ["d", 0.05, 0.20],
        ["W", 0.00, 0.00, "up"],
        ["a", 0.05, 0.05],
        ["d", 0.05, 0.20],

        ## 直接喷 E4
        # ["a", 0.05, 0.05],
        # ["E", 0.05, 0.00],

        # 升龙再喷 E3E4
        ["E", 0.05, 1.00],
        ["a", 0.05, 0.20],
        ["a", 0.05, 0.20],
        ["E", 0.05, 0.00],

        ["w", 0.05, 2.50],
        ["j", 0.05, 0.15],
    ]
    combo_action(control_service, seq, 10.0)


def test_combo_Changli(control_service):
    # 长离
    seq = [
        # 声骸技能
        ["Q", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 1.60],
        ["j", 0.05, 1.20],
        # 共鸣技能 Ea 一离火
        ["E", 0.05, 1.25],
        ["a", 0.05, 1.30],
        # ["E", 0.05, 1.25],
        # ["a", 0.05, 1.30],
        # 间隔
        ["w", 0.00, 1.20],
        # 普攻 5a 一离火
        ["a", 0.05, 0.31],
        ["a", 0.05, 0.50],
        ["a", 0.05, 0.50],
        ["a", 0.05, 1.05],
        ["a", 0.05, 0.00],
        ["w", 0.05, 0.75],
        ["j", 0.05, 1.2],
        # 共鸣技能 Ea 一离火
        ["E", 0.05, 1.25],
        ["a", 0.05, 1.30],
        ["w", 0.00, 1.20],
        # 普攻 5a 一离火
        ["a", 0.05, 0.31],
        ["a", 0.05, 0.50],
        ["a", 0.05, 0.50],
        ["a", 0.05, 1.05],
        ["a", 0.05, 0.00],
        ["w", 0.05, 0.75],
        ["j", 0.05, 1.20],
        # zRz
        ["z", 0.50, 0.90],
        ["R", 0.05, 1.65],
        ["z", 1.90, 0.00],
        ["w", 0.00, 1.00],
        ["j", 0.05, 0.00],
    ]
    combo_action(control_service, seq, 3)


def test_combo_Shorekeeper(control_service):
    # 守岸人 BnB combo
    # seq = [
    #     # 3a 闪 az
    #     ["W", 0.01, 0.01, "down"],
    #     ["a", 0.05, 0.31],
    #     ["a", 0.05, 0.42],
    #     ["a", 0.05, 0.40],
    #     ["d", 0.01, 0.00],
    #     # ["E", 0.05, 0.00],
    #     ["W", 0.01, 0.00, "up"],
    #     ["a", 0.05, 0.30],
    #     ["z", 0.50, 0.45],
    #     # 间隔
    #     ["w", 0.00, 0.70],  # 间隔需足够，否则二段开始，角色却还在一段的后摇中，会吞按键
    #     ["j", 0.05, 1.20],
    # ]
    seq = [
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
    combo_action(control_service, seq, 2)


def test_combo_Shorekeeper_AdvancedCombo(control_service):
    # 守岸人 BV1wjxse8EmD

    # 满能量 E跳a
    # 重击进入蝴蝶状态可普攻或E打断获得一格能量

    seq = [
        # 3a 四格能量
        ["a", 0.05, 0.31],
        ["a", 0.05, 0.43],
        ["a", 0.05, 0.40],
        # 进入蝴蝶
        ["z", 0.50, 0.30],
        # 退出蝴蝶 五格能量
        ["E", 0.01, 0.01],
        ["a", 0.01, 0.01],
        # 清空能量
        ["j", 0.05, 0.15],
        ["a", 0.05, 0.00],
        # 间隔
        ["w", 0.00, 0.55],
        # ["j", 0.05, 1.20],
        # 开大
        ["R", 0.05, 1.20],
    ]
    combo_action(control_service, seq, 2)


def test_combat(container, control_service):
    window_service: WindowService = container.window_service()
    img_service: ImgService = container.img_service()
    # ocr_service: OCRService = container.ocr_service()

    # img_path = file_util.get_assets_screenshot("Resonator_Shorekeeper_001.png")
    # img = img_util.read_img(img_path)
    img = img_service.screenshot()

    shorekeeper = Shorekeeper(control_service, img_service)
    shorekeeper.energy_count(img)
    shorekeeper.is_concerto_energy_ready(img)
    shorekeeper.is_resonance_skill_ready(img)
    shorekeeper.is_echo_skill_ready(img)
    shorekeeper.is_resonance_liberation_ready(img)

    for _ in range(50):
        img = img_service.screenshot()
        shorekeeper.combo_action(img)
        time.sleep(1.5)

    # 延奏 OutroSkill
    # 变奏 IntroSkill

    # img_util.show_img(img)


def test_CombatSystem(container, control_service):
    img_service: ImgService = container.img_service()
    combat_system = CombatSystem(control_service, img_service)
    combat_system.is_running = True
    combat_system.run()
