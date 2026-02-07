# 发现的程序问题

本文档记录代码审查过程中发现的程序问题，包括 Bug、潜在风险和改进建议。

---

## ✅ 已修复的 Bug (v3.1.0 Alpha)

### 1. [已修复] 莫宁 (Mornye) `rest_mass_energy_count` 方法调用错误

**文件**: `src/core/combat/resonator/mornye.py` 第 126 行

**修复状态**: ✅ 已在 commit 1100d78 中修复

**问题**: 对列表对象调用了 `.check()` 方法，而不是对检测器对象调用。

```python
# 错误代码
if self._rest_mass_energy_80_point.check(img):   # ← _point 是列表，没有 check 方法

# 修复后
if self._rest_mass_energy_80_checker.check(img):  # ← 使用 _checker
```

**影响**: 调用 `rest_mass_energy_count()` 时会抛出 `AttributeError`，导致莫宁角色在检测静质量能时崩溃。

**严重程度**: 🔴 高 - 运行时错误

---

### 2. [已修复] 卡提希娅 (Cartethyia) `is_resonance_skill_fleurdelys_2_ready` 使用错误的 checker

**文件**: `src/core/combat/resonator/cartethyia.py` 第 154 行

**修复状态**: ✅ 已在 commit 1100d78 中修复

**问题**: `is_resonance_skill_fleurdelys_2_ready` 方法检查的是 E1 的 checker 而不是 E2 的 checker。

```python
# 错误代码
def is_resonance_skill_fleurdelys_2_ready(self, img: np.ndarray) -> bool:
    is_ready = self._resonance_skill_fleurdelys_checker.check(img)  # ← 用了E1的checker
    logger.debug(f"芙露德莉斯-共鸣技能 E2: {is_ready}")

# 修复后
def is_resonance_skill_fleurdelys_2_ready(self, img: np.ndarray) -> bool:
    is_ready = self._resonance_skill_fleurdelys_2_checker.check(img)  # ← 使用E2的checker
    logger.debug(f"芙露德莉斯-共鸣技能 E2: {is_ready}")
```

**影响**: E2 技能的就绪状态检测始终返回与 E1 相同的结果，无法正确区分两个技能状态。

**严重程度**: 🟡 中 - 逻辑错误

---

### 3. [已修复] 卡提希娅 (Cartethyia) `fleurdelys_to_avatar_cartethyia_Ra3` 日志名称错误

**文件**: `src/core/combat/resonator/cartethyia.py` 第 718 行

**修复状态**: ✅ 已在 commit 1100d78 中修复

**问题**: 方法名是 `fleurdelys_to_avatar_cartethyia_Ra3`（大卡切小卡），但日志输出的名称是 `avatar_cartethyia_to_fleurdelys_Ra3`（小卡切大卡），方向完全相反。

```python
# 错误代码
def fleurdelys_to_avatar_cartethyia_Ra3(self):
    logger.debug("avatar_cartethyia_to_fleurdelys_Ra3")  # ← 日志名称反了

# 修复后
def fleurdelys_to_avatar_cartethyia_Ra3(self):
    logger.debug("fleurdelys_to_avatar_cartethyia_Ra3")  # ← 名称正确
```

**影响**: 调试时日志信息误导，不影响运行时功能。

**严重程度**: 🟢 低 - 仅影响调试

---

## 🐛 待修复的 Bug

### 1. 菲比 (Phoebe) `combo()` 方法为空实现

**文件**: `src/core/combat/resonator/phoebe.py` 第 516-530 行

**问题**: `Phoebe` 类的 `combo()` 方法只有 `pass`，没有任何连招逻辑。

```python
def combo(self):
    # ... 注释说明了菲比的机制 ...
    pass  # ← 没有实现
```

**影响**: 菲比上场后不会执行任何操作，角色原地站立。不过菲比未注册到 `resonator_map`（第 72 行被注释），所以实际使用时会回退到通用连招。

**严重程度**: 🟢 低 - 未完成功能，已通过注释禁用

---

## ⚠️ 潜在风险点

### 1. 莫宁 (Mornye) `energy_count` 使用未实现的 `BaseResonator.energy_count`

`Mornye` 类的 `combo()` 方法在第 386 行调用了 `self.energy_count(img)`，但 `Mornye` 没有重写 `energy_count()` 方法，而 `BaseMornye` 中的 `rest_mass_energy_count()` 才是正确的能量检测方法。这里调用的是 `BaseResonator` 中的默认实现，可能返回不正确的结果。

### 2. 硬编码像素坐标

所有角色的技能检测坐标和颜色值都是基于 1280×720 分辨率硬编码的。虽然 `DynamicPointTransformer` 提供了分辨率适配，但颜色值在不同显示设置（HDR、色彩配置、显卡滤镜）下可能不匹配。

### 3. 夏空 (Ciaccona) 唱歌状态超时硬编码

`Ciaccona._singing_timeout_seconds = 34.5` 这个超时时间是硬编码的。如果游戏版本更新改变了大招持续时间，需要手动修改代码。

---

## 💡 改进建议

### 1. 连招中断恢复机制

当前连招被打断后，部分角色会进入"发呆"状态（等待时间未消耗完）。虽然已通过拆分长等待时间来缓解，但可以考虑增加全局的打断检测和恢复机制。

### 2. 声骸技能随机策略

多个角色（如长离、安可）有梦魇摩托和普通摩托的随机选择逻辑，但随机比例不同（0.33 vs 0.5），建议统一或使配置可调。

### 3. 弗洛洛 (Phrolova) 使用通用连招

弗洛洛继承了 `GenericResonator` 而不是 `BasePhrolova`，使用的是通用普攻连招，未利用角色特有的技能检测能力。后续可基于 `BasePhrolova` 实现定制连招。

---

*最后更新: 2026-02-07*
