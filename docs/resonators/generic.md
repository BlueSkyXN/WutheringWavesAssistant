# 通用角色 (Generic) - 连招逻辑分析

## 基本信息

| 属性 | 值 |
|------|------|
| 角色名称 | generic（通用） |
| 角色定位 | SubDPS（副输出） |
| 元素属性 | 无 |
| 协奏类型 | 无（不检测） |
| 源文件 | `src/core/combat/resonator/generic.py` |
| 适用对象 | 未注册定制连招的所有角色 |

## 概述

`GenericResonator` 是所有未注册定制连招角色的默认实现。当编队中出现 `resonator_map` 中没有的角色时，系统自动使用此通用连招。

## 技能状态检测

通用角色**不检测任何技能状态**，仅依赖固定的按键序列。

## 连招片段

| 方法 | 描述 | 说明 |
|------|------|------|
| `custom_combo_action(fight_tactic)` | 自定义连招 | 解析 FightTactics 配置中的连招字符串 |
| `default_combo()` | 默认连招 | 简单的 E + Q + R + 普攻循环 |

### 自定义连招语法

通过 `config.yaml` 中的 `FightTactics` 配置，可以为通用角色定义连招：

```yaml
FightTactics:
    - "q~0.1,e~0.1,a"
    - "r,q~0.1,e,a,a,a,a~,e"
    - "q~0.1,e,r,e,a,a,a,a,a,e,a,a,a,a,a,e"
```

**语法解析**：

| 指令 | 说明 | 动作 |
|------|------|------|
| `a` | 普攻 | 连点 0.3 秒 |
| `a~0.5` | 普攻指定时长 | 按下 0.5 秒 |
| `a(0.5)` | 持续普攻 | 连续普攻 0.5 秒 |
| `e` | 技能 | 按下 0.3 秒 |
| `e~0.1` | 技能指定时长 | 按下 0.1 秒 |
| `q` | 声骸 | 按下 0.3 秒 |
| `q~0.1` | 声骸短按 | 按下 0.1 秒 |
| `r` | 大招 | 按下 0.3 秒 |
| `s` | 重击 | 长按左键 |
| `l` | 向后闪避 | 后退+闪避 |
| 数字 | 等待 | 等待 N 秒 |

### 默认连招

当 `FightTactics` 为空时使用：

```python
def default_combo(self):
    return [
        ["E", 0.05, 0.50],  # E技能
        ["Q", 0.05, 0.50],  # 声骸
        ["R", 0.05, 0.50],  # 大招
        ["a", 0.05, 0.30],  # 普攻×5
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.30],
        ["a", 0.05, 0.50],
    ]
```

## 连招决策逻辑 (`combo()`)

```python
def combo(self):
    if self._fight_tactic:
        self.custom_combo_action(self._fight_tactic)
    else:
        self.combo_action(self.default_combo(), False)
```

1. 有自定义连招配置 → 解析并执行
2. 无配置 → 使用默认连招（E → Q → R → 5a）

## 适用角色

以下角色在编队中使用通用连招：

- 弗洛洛 (Phrolova) - 虽有 BasePhrolova，但继承了 GenericResonator
- 菲比 (Phoebe) - 虽有 BasePhoebe，但未注册到 resonator_map
- 莫宁 (Mornye) - 虽有 BaseMornye，但未注册到 resonator_map
- 漂泊者 (Rover) - 虽有 BaseRover，但未注册到 resonator_map
- 所有其他未注册角色

## 设计特点

1. **通用兼容** - 对所有角色都能工作的最简连招
2. **可配置** - 通过 FightTactics 配置自定义连招序列
3. **安全回退** - 作为所有未定制角色的后备方案
4. **无状态检测** - 不截图不检测，纯固定序列执行

---

*最后更新: 2026-02-06*
