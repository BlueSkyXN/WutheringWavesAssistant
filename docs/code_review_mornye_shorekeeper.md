# 莫宁与守岸人代码审查报告 (Mornye & Shorekeeper Code Review)

**日期**: 2026-02-10
**审查范围**: `src/core/combat/resonator/mornye.py`, `src/core/combat/resonator/shorekeeper.py` 及相关文档

## 执行摘要 (Executive Summary)

本次审查发现了莫宁（Mornye）和守岸人（Shorekeeper）角色实现中的关键问题：

1. **严重缺陷**: 莫宁未在 `combat_system.py` 的 `resonator_map` 中注册，导致该角色无法正常使用
2. **文档不符**: 莫宁的文档描述了高级连招逻辑，但实际代码实现极其简化
3. **代码复制**: 莫宁的代码结构明显从守岸人复制而来，但简化了核心战斗逻辑

---

## 1. 代码对比分析 (Code Comparison Analysis)

### 1.1 相似之处 (Similarities)

两个角色共享几乎相同的代码结构模式：

#### 类结构
- **Base类设计**: 均采用 Base + Implementation 双层设计
  - `BaseShorekeeper` / `BaseMornye` - 状态检测与 ColorChecker
  - `Shorekeeper` / `Mornye` - 连招逻辑实现

#### 角色定位
- **职业**: 均为 `CharClassEnum.Healer` (治疗)
- **机制**: 均有"蝴蝶变身"系统
- **连招模式**: 均使用 `3普攻 → 重击进蝴蝶 → E退出 → 跳+普攻清能量` 核心循环

#### 方法命名
两者使用完全相同的方法命名规范：
- `a3()` - 3段普攻
- `za()` / `zaEja()` - 重击相关连招
- `ja()` - 跳+普攻清能量
- `E()`, `Q()`, `R()` - 技能方法

#### 代码注释风格
```python
# 守岸人
self._energy1_checker = ColorChecker(...)  # 能量1 血条上方的5格能量

# 莫宁
self._rest_mass_energy_20_checker = ColorChecker(...)  # 静质量能 满时可重击进入广域观测模式
```

**结论**: 莫宁的代码框架明显从守岸人复制而来，保留了相同的架构和命名约定。

---

### 1.2 关键差异 (Key Differences)

| 特性 | 守岸人 (Shorekeeper) | 莫宁 (Mornye) |
|------|---------------------|---------------|
| **元素** | Spectro (衍射) - 黄色 | Fusion (熔融) - 红色 |
| **协奏检测** | `concerto_spectro()` | `concerto_fusion()` |
| **能量系统** | 5格离散能量条 (1-5格) | 双模式能量系统 |
| **能量颜色** | 黄色 `(114, 241, 255)` | 蓝色/暖色 |
| **代码行数** | 334行 | 265行 |
| **combo()复杂度** | **42行** (293-334) | **10行** (256-265) |
| **注册状态** | ✅ 已注册 (line 64) | ❌ **未注册** |

#### 莫宁独有的复杂性

莫宁拥有更复杂的状态系统：

**基准模式** (常规形态):
- 静质量能 (Rest Mass Energy) - 蓝色 `(63, 119, 250)`
- 检测点: 20%, 50%, 80%
- 重击·位势转换 (Geopotential Shift)

**广域观测模式** (蝴蝶形态):
- 相对动能 (Relative Momentum) - 暖色系
- 检测点: 20%, 50%, 80%
- 重击·反演 (Inversion)
- 特殊退出机制: `exit_special_state()` (244-254行)

对比守岸人只有单一的5格能量条系统。

---

## 2. 严重缺陷分析 (Critical Issues)

### 缺陷 #1: 莫宁未注册 ❌

**位置**: `src/core/combat/combat_system.py:61-74`

**问题描述**:
```python
# Line 59: 实例已创建
self.mornye = Mornye(self.control_service, self.img_service)

# Lines 61-74: resonator_map 定义
self.resonator_map: dict[ResonatorNameEnum, BaseResonator] = {
    ResonatorNameEnum.jinhsi: self.jinhsi,
    ResonatorNameEnum.changli: self.changli,
    ResonatorNameEnum.shorekeeper: self.shorekeeper,  # ✅ 守岸人已注册
    ResonatorNameEnum.encore: self.encore,
    ResonatorNameEnum.verina: self.verina,
    ResonatorNameEnum.camellya: self.camellya,
    ResonatorNameEnum.sanhua: self.sanhua,
    ResonatorNameEnum.cartethyia: self.cartethyia,
    ResonatorNameEnum.ciaccona: self.ciaccona,
    # ResonatorNameEnum.phoebe: self.phoebe,  # 已注释
    ResonatorNameEnum.phrolova: self.phrolova,
    ResonatorNameEnum.lynae: self.lynae,
    # ❌ 缺失: ResonatorNameEnum.mornye: self.mornye,
}
```

**影响**:
1. 用户选择莫宁时，`set_resonators()` 方法无法从 `resonator_map` 获取实例
2. 回退到 `GenericResonator` (254行)
3. **所有莫宁的专属代码（265行）完全不会被执行**

**证据**:
`docs/resonators/generic.md:93` 中明确记录：
> "莫宁 (Mornye) - 虽有 BaseMornye，但未注册到 resonator_map"

---

### 缺陷 #2: 莫宁的 combo() 逻辑过于简化 ⚠️

**位置**: `src/core/combat/resonator/mornye.py:256-265`

**实际代码**:
```python
def combo(self):
    self.combo_action(self.a4(), False)

    combo_list = [self.Eaa(), self.R(), self.z()]
    random.shuffle(combo_list)  # ⚠️ 随机打乱顺序
    for i in combo_list:
        self.combo_action(i, False)
        time.sleep(0.15)

    self.combo_action(self.Q(), False)
```

**问题**:
1. **无状态检测** - 不截图，不检查能量/技能/血量
2. **随机执行** - 使用 `random.shuffle()` 打乱连招顺序
3. **缺少异常处理** - 无 try-except，无蝴蝶打断保护
4. **缺少条件判断** - 无智能决策

**对比守岸人的 combo()** (293-334行):
```python
def combo(self):
    try:
        # 1. 截图检测大招状态
        img = self.img_service.screenshot()
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)

        # 2. 性价比3段普攻
        self.combo_action(self.a3(), True)

        # 3. 有R优先释放（协星调律）
        if is_resonance_liberation_ready:
            self.combo_action(self.E(), False)
            self.combo_action(self.R(), True)
            return

        # 4. 再次截图检测详细状态
        img = self.img_service.screenshot()
        energy_count = self.energy_count(img)
        is_resonance_skill_ready = self.is_resonance_skill_ready(img)
        is_resonance_liberation_ready = self.is_resonance_liberation_ready(img)
        boss_hp = self.boss_hp(img)

        # 5. 条件判断：3格能量 + E就绪 + Boss存活
        if energy_count == 3 and is_resonance_skill_ready and boss_hp > 0.01:
            self.combo_action(self.zaEja(), False)  # 进阶轴
            self.combo_action(self.Q(), False)
            return

        # 6. 通用流程
        self.combo_action(self.E(), not is_resonance_liberation_ready)
        self.combo_action(self.R(), is_resonance_liberation_ready)
        if energy_count == 5:
            self.combo_action(self.ja(), False)  # 防蝴蝶飞出
        self.combo_action(self.Q(), False)

    except StopError as e:
        self.control_service.jump()  # 打断守岸人变身蝴蝶
        raise e
```

守岸人实现了：
- ✅ 双次截图状态检测
- ✅ 多条件决策树
- ✅ 异常处理与蝴蝶打断
- ✅ Boss血量判断
- ✅ 能量5格特殊处理

莫宁缺失：
- ❌ 所有状态检测
- ❌ 条件判断
- ❌ 异常处理
- ❌ 智能决策

---

### 缺陷 #3: 文档与代码不符 📄

**位置**: `docs/resonators/mornye.md:82-109`

**文档声称的逻辑**:
```
连招决策逻辑 (combo()):

截图检测大招状态

入场: a3() 性价比3段普攻

1. 有R（协星调律）:
   ├─ E()
   ├─ R()
   └─ return

2. 再次截图检测:
   检查能量、E技能、R、Boss血量

3. 能量3格 且 有E 且 Boss未击败:
   ├─ zaEja() 进阶轴核心循环
   ├─ Q()
   └─ return

4. 通用处理:
   ├─ E() (无R时等待合轴)
   ├─ R() (有R时释放)
   ├─ 能量5格 → ja() 清能量
   └─ Q()

异常处理:
└─ StopError → jump() 打断蝴蝶变身防止飞出场外
```

**实际代码**: 仅有 `a4() → shuffle([Eaa(), R(), z()]) → Q()`

**问题**: 文档描述的是守岸人的逻辑，但莫宁实际实现完全不同。

---

## 3. 代码演进历史分析 (Historical Analysis)

### 3.1 文件创建时间

根据 git 历史：
- 两个角色的文件在同一次提交中引入 (`b6f9ce6`)
- 这是一次合并 PR #4 的提交

### 3.2 开发推断

基于代码结构分析，推测开发过程：

1. **阶段1**: 开发者创建守岸人，实现完整的战斗逻辑
2. **阶段2**: 复制守岸人代码作为莫宁模板
   - 保留了相同的类结构
   - 保留了相同的方法命名
   - 保留了相同的注释风格
3. **阶段3**: 定制莫宁的状态检测系统
   - 实现了双模式能量系统（更复杂）
   - 实现了多个ColorChecker
   - 实现了 `exit_special_state()`
4. **阶段4**: 简化莫宁的 combo() 逻辑
   - 可能是时间限制
   - 可能是测试不足
   - **忘记注册到 resonator_map**
5. **阶段5**: 编写文档时，错误地复制了守岸人的逻辑描述

---

## 4. 其他发现 (Additional Findings)

### 4.1 共同的设计模式

两个角色均使用"蝴蝶防飞"设计模式：

**守岸人** (333行):
```python
except StopError as e:
    self.control_service.jump()  # 打断守岸人变身蝴蝶
    raise e
```

**问题**: 莫宁的 `combo()` 缺少此保护，可能导致蝴蝶飞出场外。

### 4.2 方法完整性对比

| 方法 | 守岸人 | 莫宁 | 说明 |
|------|--------|------|------|
| `a2()` | ✅ | ❌ | 2段普攻 |
| `a3()` | ✅ | ❌ | 3段普攻 |
| `a4()` | ❌ | ✅ | 4段普攻 |
| `zaEja()` | ✅ | ❌ | 进阶轴核心 |
| `zE()` | ✅ | ❌ | 重击+E |
| `Eja()` | ✅ | ❌ | E+跳+普攻 |
| `ja()` | ✅ | ❌ | 跳+普攻 |
| `za()` | ✅ | ❌ | 重击+普攻 |
| `Eaa()` | ❌ | ✅ | E+两段普攻 |

**结论**: 莫宁缺少大量连招片段，只实现了基础方法。

### 4.3 测试覆盖率

**守岸人**:
- `tests/core/combats_test.py:256-319` - 两个测试方法
- `test_combo_Shorekeeper()`
- `test_combo_Shorekeeper_AdvancedCombo()`

**莫宁**:
- `tests/core/combats_test.py:1056+` - 一个测试方法
- `test_combo_mornye_AdvancedCombo()`

---

## 5. 修复建议 (Recommendations)

### 优先级 1 - 严重 (Critical)

#### 修复 #1: 注册莫宁到 resonator_map
**文件**: `src/core/combat/combat_system.py:73`

**修改**:
```python
self.resonator_map: dict[ResonatorNameEnum, BaseResonator] = {
    ResonatorNameEnum.jinhsi: self.jinhsi,
    ResonatorNameEnum.changli: self.changli,
    ResonatorNameEnum.shorekeeper: self.shorekeeper,
    ResonatorNameEnum.encore: self.encore,
    ResonatorNameEnum.verina: self.verina,
    ResonatorNameEnum.camellya: self.camellya,
    ResonatorNameEnum.sanhua: self.sanhua,
    ResonatorNameEnum.cartethyia: self.cartethyia,
    ResonatorNameEnum.ciaccona: self.ciaccona,
    # ResonatorNameEnum.phoebe: self.phoebe,
    ResonatorNameEnum.phrolova: self.phrolova,
    ResonatorNameEnum.lynae: self.lynae,
    ResonatorNameEnum.mornye: self.mornye,  # 新增
}
```

**影响**: 使莫宁可用，玩家选择莫宁时将使用专属代码。

---

### 优先级 2 - 重要 (High)

#### 修复 #2: 更新莫宁文档以反映实际实现

**选项A**: 修改文档以匹配当前简化的实现
**选项B**: 实现文档中描述的高级逻辑（更大工作量）

**建议**: 先修改文档，在后续版本中逐步完善代码。

**文件**: `docs/resonators/mornye.md:82-109`

**修改为**:
```markdown
## 连招决策逻辑 (`combo()`)

⚠️ **当前实现为简化版本**

### 当前逻辑
1. 4段普攻 `a4()`
2. 随机执行以下技能：
   - E + 两段普攻 `Eaa()`
   - 大招 `R()`
   - 重击 `z()`
3. 释放声骸 `Q()`

### 局限性
- 不检测能量状态
- 不检测技能就绪
- 不判断Boss血量
- 无异常处理
- 连招顺序随机

### 规划的高级逻辑（未实现）
未来版本将实现状态检测和条件判断，类似守岸人的逻辑。
```

---

### 优先级 3 - 增强 (Enhancement)

#### 建议 #3: 实现莫宁的完整 combo() 逻辑

参考守岸人的实现，为莫宁添加：
1. 状态检测（能量、技能、Boss血量）
2. 条件决策树
3. 异常处理与蝴蝶打断
4. 实现缺失的连招片段（`a3()`, `zaEja()`, `ja()` 等）

---

## 6. 结论 (Conclusion)

### 确认的事实

1. ✅ **莫宁确实是从守岸人复制而来**
   - 相同的类结构
   - 相同的方法命名
   - 相同的设计模式

2. ✅ **作者对莫宁进行了部分定制**
   - 实现了更复杂的双模式能量系统
   - 定制了ColorChecker检测点
   - 添加了特殊状态退出逻辑

3. ✅ **作者简化了战斗逻辑**
   - combo() 从42行减少到10行
   - 移除了所有状态检测
   - 使用随机化替代条件判断

4. ❌ **严重缺陷：莫宁未注册**
   - 导致角色完全不可用
   - 代码从未被执行过

5. ❌ **文档错误**
   - 描述了未实现的功能
   - 可能直接复制了守岸人的文档

### 影响评估

**当前状态**:
- 莫宁实际上**无法使用**（未注册）
- 即使注册后，战斗表现将**远逊于守岸人**（简化逻辑）
- 文档**误导用户**（描述了不存在的功能）

**修复后**:
- 修复 #1 后：莫宁可用，但战斗效果一般
- 修复 #2 后：文档准确反映实现
- 实施建议 #3 后：莫宁达到与守岸人同等的战斗水平

---

## 7. 附录 (Appendix)

### 存储的记忆 (Repository Memories)

审查过程中验证了以下现有记忆的准确性：

1. ✅ **combat system** - "Mornye instantiated but not registered in resonator_map"
2. ✅ **mornye bug fix** - "rest_mass_energy_count() must use _rest_mass_energy_80_checker.check(img)"
3. ✅ **project structure** - "phoebe is commented out and mornye is instantiated but not registered"

### 相关文件清单

**源代码**:
- `src/core/combat/combat_system.py` - 战斗系统主文件
- `src/core/combat/resonator/mornye.py` - 莫宁实现
- `src/core/combat/resonator/shorekeeper.py` - 守岸人实现

**文档**:
- `docs/resonators/mornye.md` - 莫宁文档
- `docs/resonators/shorekeeper.md` - 守岸人文档
- `docs/resonators/generic.md` - 通用连招文档（提到莫宁未注册）

**测试**:
- `tests/core/combats_test.py` - 战斗测试文件

---

**报告完成日期**: 2026-02-10
**审查人**: Claude Code
**版本**: 1.0
