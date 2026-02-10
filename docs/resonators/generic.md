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
| `a4()` | 4段普攻 | 基础普攻连招 |
| `Eaa()` | E+两段普攻 | E技能后接普攻 |
| `E()` | E技能 | 仅E |
| `z()` | 重击 | 重击技能 |
| `Q()` | 声骸技能 | 声骸释放 |
| `R()` | 共鸣解放 | 大招 |

## 连招决策逻辑 (`combo()`)

⚠️ **实际实现为简化版本，不支持自定义配置**

### 当前实际逻辑

```python
def combo(self):
    self.combo_action(self.a4(), False)

    combo_list = [self.Eaa(), self.R(), self.z()]
    random.shuffle(combo_list)  # 随机打乱顺序
    for i in combo_list:
        self.combo_action(i, False)
        time.sleep(0.15)

    self.combo_action(self.Q(), False)
```

**执行流程**：

1. 入场: `a4()` - 4段普攻
2. 随机执行以下技能（顺序随机打乱）:
   - `Eaa()` - E技能 + 两段普攻
   - `R()` - 大招
   - `z()` - 重击
3. 释放声骸: `Q()`

### 实现特点

- **简化设计**: 不进行状态检测，按固定流程执行
- **随机化**: 使用 `random.shuffle()` 打乱技能执行顺序
- **无条件判断**: 不检测能量、技能就绪状态、Boss血量
- **不支持自定义配置**: FightTactics 配置功能未实现

### 规划的功能（未实现）

以下功能在早期规划中但**当前未实现**：

- ❌ `custom_combo_action()` 方法不存在
- ❌ FightTactics 配置解析不存在
- ❌ 自定义连招语法（`a~0.5`, `e~0.1` 等）不支持
- ❌ 不读取 `config.yaml` 中的 FightTactics 配置

## 适用角色

以下角色在编队中使用通用连招：

- 弗洛洛 (Phrolova) - 虽有 BasePhrolova，但继承了 GenericResonator
- 菲比 (Phoebe) - 虽有 BasePhoebe，但未注册到 resonator_map
- 漂泊者 (Rover) - 虽有 BaseRover，但未注册到 resonator_map
- 所有其他未注册角色

**注**: 莫宁 (Mornye) 已注册到 resonator_map (2026-02-10更新)，使用专属连招而非通用连招。

## 设计特点

1. **通用兼容** - 对所有角色都能工作的最简连招
2. **安全回退** - 作为所有未定制角色的后备方案
3. **无状态检测** - 不截图不检测，纯固定序列执行
4. **简化实现** - 当前版本使用随机化简化逻辑，不支持自定义配置

---

*最后更新: 2026-02-10*
