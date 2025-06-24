import logging
import time

import pytest

from src.core.combat.combat_system import CombatSystem
from src.core.combat.resonator.encore import Encore
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
    # 汐汐 速喷 BV1sUfHYdEPG
    # 4a E闪a跳 a闪a闪 aE
    seq = [
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.90],
        ["a", 0.05, 0.40],

        ["E", 0.05, 0.05],
        ["d", 0.05, 0.30],
        ["a", 0.05, 0.05],
        ["j", 0.05, 0.01],

        ["W", 0.00, 0.00, "down"],
        ["a", 0.05, 0.05],
        ["d", 0.05, 0.30],
        ["W", 0.00, 0.00, "up"],
        ["a", 0.05, 0.05],
        ["d", 0.05, 0.30],

        # # 直接喷 E4
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
    combo_action(control_service, seq, 10.0, cycle=2000)


def test_combo_Jinhsi_AdvancedCombo2(control_service):
    # 汐汐 变奏（E2下劈）速喷 BV1rS5Vz4Egy BV1dtEgzUEAF
    # E2状态 下落攻击 落地瞬间跳（翻滚） E跳 a跳a跳a跳a跳 E
    seq = [
        # 进入E2
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.45],
        ["a", 0.05, 0.90],
        ["a", 0.05, 0.40],
        # 模拟下劈
        ["j", 0.05, 0.27],
        ["a", 0.05, 0.00],
    ]
    combo_action(control_service, seq, 0.0, cycle=1)
    seq = [
        ["j", 0.002, 0.005],
        ["a", 0.002, 0.005],
        ["j", 0.002, 0.005],
        ["E", 0.002, 0.005],

        # ["j", 0.002, 0.002],
        # ["a", 0.002, 0.002],
        # ["j", 0.002, 0.002],
        # ["E", 0.002, 0.002],
        # ["j", 0.002, 0.002],
        # ["a", 0.002, 0.002],
        # ["j", 0.002, 0.002],
        # ["a", 0.002, 0.002],
        # ["j", 0.002, 0.002],
        # ["a", 0.002, 0.002],
        # ["j", 0.002, 0.002],
        # ["a", 0.002, 0.002],
        # ["j", 0.002, 0.002],
        # ["a", 0.002, 0.002],
        # ["a", 0.002, 0.002],

    ]
    combo_action(control_service, seq, 0.0, cycle=50)


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


def test_combo_Encore(control_service):
    # 安可 BnB combo
    seq = [
        # ja
        ["j", 0.05, 0.33],
        ["a", 0.05, 0.72],
        ["j", 0.05, 1.20],

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
    combo_action(control_service, seq, 2)


def test_combo_verina(control_service):
    # 维里奈 BnB combo
    seq = [
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
    combo_action(control_service, seq, 2)


def test_combo_camellya(control_service):
    # 椿 BnB combo
    seq = [
        # 白椿 普攻4a
        ["a", 0.05, 0.29],
        ["a", 0.05, 0.46],
        ["a", 0.05, 1.00],
        ["a", 0.05, 2.00],
        ["j", 0.05, 1.20],

        # 白椿 普攻3az 转圈派生
        ["a", 0.05, 0.29],
        ["a", 0.05, 0.46],
        ["a", 0.05, 1.00],
        ["z", 3.50, 0.41],
        ["j", 0.05, 1.20],

        # 白椿 重击
        ["z", 2.50, 1.40],
        ["j", 0.05, 1.20],

        # 白椿 重击 转圈派生
        ["z", 4.78, 0.80],
        ["j", 0.05, 1.20],

        # 一日花 Ea 下砸落地
        ["E", 0.05, 1.40],
        ["a", 0.05, 1.00],
        ["j", 0.05, 1.20],

        # 白椿转红椿 普攻重击转圈 下砸落地 消耗【红椿·蕊】
        ["E", 0.05, 1.25],
        ["a", 0.05, 0.85],
        ["a", 0.05, 0.69],
        ["z", 3.55, 0.35],
        ["j", 0.05, 0.93],
        ["a", 0.05, 1.28],
        ["j", 0.05, 1.20],

        # 白椿转红椿 重击转圈 下砸落地 消耗【红椿·蕊】
        ["E", 0.05, 0.50],
        ["z", 5.35, 0.50],
        ["j", 0.05, 1.01],
        ["a", 0.05, 1.20],
        ["j", 0.05, 1.20],

        # R
        ["R", 0.05, 4.06],
        ["j", 0.05, 1.20],
    ]
    combo_action(control_service, seq, 2)


def test_combo_camellya_AdvancedCombo(control_service):
    # 椿 Advanced combo
    seq = [
        # 白椿取消转红椿 重击转圈 三连鞭
        # ["E", 0.05, 0.45],
        # ["Q", 0.05, 0.05],
        # ["d", 0.05, 0.05],
        # ["z", 5.00, 0.20],
        # ["j", 0.05, 0.55],
        # ["E", 0.05, 1.25],
        # ["j", 0.05, 1.20],

        ["E", 0.05, 0.27],
        ["Q", 0.05, 0.20],
        ["d", 0.05, 0.25],
        ["z", 5.00, 0.34],
        ["j", 0.05, 1.05],
        ["E", 0.05, 1.25],
        ["j", 0.05, 1.20],
    ]
    combo_action(control_service, seq, 2)


def test_combo_sanhua(control_service):
    # 散华 BnB combo
    seq = [
        # 普攻4a
        ["a", 0.05, 0.36],
        ["a", 0.05, 0.33],
        ["a", 0.05, 0.60],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.89],
        ["j", 0.05, 1.20],

        # # 重击爆裂
        # ["z", 0.915, 1.30],
        # ["j", 0.05, 1.20],

        ["w", 0.00, 1.00],

        # Ez
        ["E", 0.05, 0.20],
        ["z", 0.85, 1.56],
        ["j", 0.05, 1.20],

        # 辉萤军势
        ["Q", 0.05, 0.66],
        ["a", 0.05, 0.93],
        ["a", 0.05, 1.23],
        ["j", 0.05, 1.20],

        # # 无常凶鹭
        # ["Q", 0.05, 1.45],
        # ["j", 0.05, 1.20],

        # 普攻4a
        ["a", 0.05, 0.36],
        ["a", 0.05, 0.33],
        ["a", 0.05, 0.60],
        ["a", 0.05, 0.67],
        ["a", 0.05, 0.89],
        ["j", 0.05, 1.20],

        # ERz
        ["E", 0.05, 0.39],
        ["R", 0.05, 0.05],
        ["z", 1.85, 1.43],
        ["j", 0.05, 1.20],

        # 下落攻击
        ["j", 0.05, 0.28],
        ["a", 0.05, 0.75],
        ["j", 0.05, 1.20],

    ]
    combo_action(control_service, seq, 2)


def test_combo_cartethyia(control_service):
    # 卡提希娅 BnB combo
    seq = [
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
    combo_action(control_service, seq, 2)


def test_combo_cartethyia_AdvancedCombo(control_service):
    # 卡提希娅 advanced combo
    seq = [
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
    combo_action(control_service, seq, 2)


def test_combo_cartethyia_AdvancedCombo2(control_service):
    # 卡提希娅 advanced combo2
    # 跟1差不多，1是无剑，先打E攒剑三启动
    # 2是已有剑三，E也cd，可以变身后打E，结束后打E
    seq = [
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
    combo_action(control_service, seq, 2)


def test_combat(container, control_service):
    window_service: WindowService = container.window_service()
    img_service: ImgService = container.img_service()
    # ocr_service: OCRService = container.ocr_service()

    # img_path = file_util.get_assets_screenshot("Resonator_Shorekeeper_001.png")
    # img = img_util.read_img(img_path)
    img = img_service.screenshot()

    # resonator = Shorekeeper(control_service, img_service)
    resonator = Encore(control_service, img_service)
    resonator.energy_count(img)
    resonator.is_concerto_energy_ready(img)
    resonator.is_resonance_skill_ready(img)
    resonator.is_echo_skill_ready(img)
    resonator.is_resonance_liberation_ready(img)

    resonator.boss_hp(img)

    # for _ in range(50):
    #     shorekeeper.full_combo()
    #     time.sleep(1.5)

    # 延奏 OutroSkill
    # 变奏 IntroSkill

    # img_util.show_img(img)


def test_CombatSystem(container, control_service):
    img_service: ImgService = container.img_service()
    combat_system = CombatSystem(control_service, img_service)
    combat_system.start()
