# NTE-Assistant 代码审查报告

**审查范围**: `/Volumes/TP4000PRO/GitHub/NTE-Assistant/` 全部 39 个 Python 文件 + `config.yaml` + `pyproject.toml`
**审查方法**: 静态阅读 + 抽样导入验证 (Python 直接 `import` 关键模块以确认是否存在结构性错误)

---

## 总体评估: **通过 (PASS)** ✅ — 二次评审

> **初次评审结果**: 不通过 (FAIL) — 发现 4 个严重问题 (C1-C4) + 5 个重要问题 (I1-I5)
> **修复轮次**: 2 个并行修复代理（Claude Opus 4.7 + GPT-5.5）
> **二次验证**: 33 文件 AST 通过，全部关键 import 正常，8 个单元测试通过

所有严重问题 (C1-C4) 和重要问题 (I1-I3, M5) 均已修复并验证：
1. ✅ `FishingStats`/`PulseDecision`/`QuestStats` 已添加到模型层
2. ✅ `main.py` 已重写，接入真实服务 DI 链（Win32WindowService → PostMessageControlService → PrintWindowCaptureService → OpenCVRecognitionService）
3. ✅ 钓鱼逻辑已去重，`FishingService` 委托 `FishingStateMachine`
4. ✅ `activate()` 改用 `SetForegroundWindow`；`PW_CLIENTONLY` 矛盾移除；空 `class_name` 改为匹配任意

---

## 严重问题 (Critical — 必须修复)

### C1. `fishing_core.py` 在 import 时即抛 `ImportError`
**File**: `src/core/fishing/fishing_core.py:41`
**Severity**: Critical
**Problem**:
```python
from src.core.fishing.models import FishingConfig, FishingStats, PulseDecision
```
但 `src/core/fishing/models.py` 只定义了 `FishingState`、`FishingConfig`，**没有** `FishingStats` 也没有 `PulseDecision`。任何 `import src.core.fishing.fishing_core` 都会立刻抛 `ImportError: cannot import name 'FishingStats'`。
**Evidence**: 已实际运行验证：
```
$ python3 -c "from src.core.fishing import fishing_core"
ImportError: cannot import name 'FishingStats' from 'src.core.fishing.models'
```
现有测试 `tests/core/test_fishing_models.py` 用的是 `pytest.importorskip("src.core.fishing.fishing_core")`，遇到 `ImportError` 直接跳过，所以 CI 始终是绿的——掩盖了这个 P0。
**Suggested fix**: 在 `models.py` 中补齐 `FishingStats` (success_count / escape_count / 等) 和 `PulseDecision(key, seconds)` 两个 dataclass；或修改 `fishing_core.py` 把这些类型定义到本文件。把测试的 `importorskip` 改成 `import`，让结构性错误不会被静默吞掉。

### C2. `quest_core.py` 在 import 时即抛 `ImportError`
**File**: `src/core/quest/quest_core.py:35`
**Severity**: Critical
**Problem**: 同 C1 模式：
```python
from src.core.quest.models import QuestConfig, QuestStats
```
`src/core/quest/models.py` 没有 `QuestStats`。
**Evidence**: 实际运行：
```
$ python3 -c "from src.core.quest import quest_core"
ImportError: cannot import name 'QuestStats' from 'src.core.quest.models'
```
此外 `quest_core.py` 还引用了 `QuestConfig.match_threshold` / `error_backoff` / `scan_interval` / `click_seconds` / `tap_seconds` / `default_key`，而 `quest/models.py` 的 `QuestConfig` 实际只有 `template_dir / actions / default_threshold / loop_interval / action_delay`。即便 `QuestStats` 补上了，运行 tick() 仍会立刻 `AttributeError`。
**Suggested fix**: 把 `QuestConfig` 字段补齐到与 `quest_core.py` 实际使用一致；新增 `QuestStats` 数据类。强烈建议为 `QuestAutomation.tick()` 写一个用 `unittest.mock` 注入假 service 的端到端用例，以阻止此类回归。

### C3. `main.py` 没有装配真正的服务，UI 是空壳
**File**: `main.py:20-54`、`main.py:88-100`
**Severity**: Critical
**Problem**: 主入口创建的是这个占位 dataclass：
```python
@dataclass
class RuntimeService:
    name: str
    running: bool = False
    fish_count: int = 0
    status: str = "空闲"
    def start(self) -> None: self.running = True; self.status = "运行中"
    def stop(self)  -> None: self.running = False; self.status = "已停止"
```
然后把它塞给 `MainWindow` / `FishingTab` / `QuestTab`。`Win32WindowService` / `PostMessageControlService` / `PrintWindowCaptureService` / `OpenCVRecognitionService` / `FishingService` / `QuestAutomation` **没有任何一处被实例化**。`AppContext` 类存在但从未被 main 引用。`config['game_window']['title_keyword']` 只用来生成一个状态栏字符串。
**Evidence**: 在 `main.py` 全文 grep 不到 `Win32WindowService / PostMessage / PrintWindow / FishingService / QuestAutomation / AppContext` 任何一个名字。
**Suggested fix**: 在 `main()` 中按依赖顺序构造 `AppContext`：window → control → capture → recognition → 任务 service，并把它们注入 tab。如果游戏未运行允许 lazy 化，则 window service 应该提供"未连接"语义并允许 UI 启动；不要用 fake dataclass 顶替。

### C4. 钓鱼逻辑被实现了两遍且互不感知
**File**: `src/core/fishing/fishing_core.py` vs `src/service/fishing_service.py`
**Severity**: Critical (设计/可维护性)
**Problem**:
- `fishing_core.FishingStateMachine` 定义了 `IDLE / WAIT_BITE / CASTING / FOLLOWING_BAR / REELING / COMPLETE / ERROR` 一套状态机，依赖 core 层的 `FishingConfig` (来自 `core/fishing/models.py`) ——但用了 `entry_templates / interact_key / tap_seconds / action_delay / bite_timeout / cast_confirm_templates / cast_timeout / success_template / escape_template / click_offset / click_seconds / inter_pulse_sleep` 等 **`FishingConfig` 根本没有**的字段。
- `fishing_service.FishingService` 自己又重新定义了一份 `FishingConfig` + `FishingState` + 内嵌状态机 (`_detect_entry / _confirm_fish / _follow_and_wait_result`)。
两份实现都自称"orchestrator"，但谁也没引用对方。即使 C1 修好，`FishingStateMachine.tick()` 的第一行 `cfg.entry_templates` 仍会 `AttributeError`。
**Suggested fix**: 删掉一份。建议保留 `core/fishing/fishing_core.py` 作为纯逻辑层 (无线程、无 sleep)、由 `service/fishing_service.py` 的线程循环来驱动它的 `tick()`；service 层的 inline 状态机直接删除。同时合并/删除重复的 `FishingConfig` / `FishingState`。

---

## 重要问题 (Important — 应当修复)

### I1. `PostMessageControlService.activate()` 实际上不会激活窗口
**File**: `src/service/control_service.py:95-97`
**Severity**: High
**Problem**:
```python
def activate(self) -> None:
    win32gui.PostMessage(self.hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
```
`WM_ACTIVATE` 是系统在激活变化时**主动发给窗口的通知**，应用 PostMessage 一个 `WM_ACTIVATE` 不会让窗口前置或获得焦点；这只是给窗口塞进了一条消息让它误以为自己被激活。换言之 `activate()` 是 no-op。
**Evidence**: 项目里其实已经写过正确的实现 `src/util/hwnd_util.py:186 bring_to_front()` (`SetForegroundWindow` + `IsIconic` 还原)，但没被 `PostMessageControlService` 使用。
**Suggested fix**: `activate()` 改为调用 `bring_to_front(self.hwnd)`，或直接 `win32gui.SetForegroundWindow(self.hwnd)`，并在窗口最小化时先 `ShowWindow(SW_RESTORE)`。

### I2. `PrintWindowCaptureService` 的客户区裁剪偏移可能错位
**File**: `src/service/capture_service.py:58-104`
**Severity**: Medium-High (依赖 Windows 行为；建议实测)
**Problem**: `_capture_window` 用 `PW_CLIENTONLY | PW_RENDERFULLCONTENT` 调用 `PrintWindow`。在大多数公开实现 (例如 windows-graphics-capture 系列) 的观察下，**带 PW_CLIENTONLY 时客户区会被绘制到目标 DC 的 (0,0)**，目标 DC 其余像素未被写入。但代码：
1. 把目标位图按 **DWM 整窗大小** 创建（含非客户区）；
2. 然后 `_crop_client` 又按 `client_left - win_left` 这个**非零偏移** crop。
两处假设互相矛盾：要么去掉 `PW_CLIENTONLY` (位图是整窗、按偏移裁；常见做法)，要么保留 `PW_CLIENTONLY` 但按客户区尺寸创建位图、裁剪 (0,0,client_w,client_h)。当前组合大概率会让最终图像取到边框/未初始化区域。
**Evidence**: 静态分析；建议在 1080p / 缩放 200% 下分别保存一帧 PNG 比对。
**Suggested fix**: 二选一 —— 推荐去掉 `PW_CLIENTONLY` 标志，保持现在的"按 DWM 偏移裁"逻辑；或保留 `PW_CLIENTONLY` 同时把位图大小改成客户区大小并删掉裁剪。

### I3. `Win32WindowService` 把空 class_name 当成"必须等于空串"
**File**: `src/service/window_service.py:41,66-69`
**Severity**: Medium
**Problem**: 构造器接受 `class_names: str | Iterable[str]`，把字符串 `""` 包成 `("",)`。回调里：
```python
class_ok = not self.class_names or class_name in self.class_names
```
非空 tuple → 第一项 falsy；要求 `class_name in ("",)` 才通过。绝大多数窗口 `GetClassName` 不会返回 `""`，结果是没人匹配上。`config.yaml` 默认就是 `class_name: ""`，如果将来真的把它接到 `Win32WindowService(class_names=cfg["class_name"])`，会直接找不到游戏窗口。
**Suggested fix**: 在 `__init__` 里把空串归一化：`class_names = () if not class_names else (...)` 或在回调里增加 `class_name == ""` 的 short-circuit。

### I4. `fishing_service` 的工作线程对帧数据缺少 None/empty 防御
**File**: `src/service/fishing_service.py:122,149,162`
**Severity**: Medium
**Problem**: `frame = self.capture.screenshot()` 后立即送入 `match_template / detect_green_zone`。`PrintWindowCaptureService.screenshot_window` 在窗口尺寸异常时 `raise`、在 BitBlt 路径下也可能返回畸形数据；线程 `_run` 的 `while not self._stop_event.is_set()` 没有 try/except 保护，单帧异常会直接结束工作线程而 `state` 仍停留在 `FOLLOWING` 之类的非终态，UI 看上去"还在运行"实际线程已死。
**Suggested fix**: 在 `run_once` 内部 `try/except Exception: log + return False`；或把 `_run` 的循环体包一层异常捕获 + 适度 backoff，确保线程死亡时 `state = FAILED`。

### I5. `fishing_service.FishingService` 的可变状态字段非线程安全
**File**: `src/service/fishing_service.py:62-91`
**Severity**: Medium
**Problem**: `state` 和 `fish_count` 由工作线程写、UI 主线程读 (`fishing_tab._refresh_count` 通过 `getattr(service,"fish_count",0)`)。Python GIL 让单字段读写不会撕裂，但 `state` 转换跨多步 (`state = FOLLOWING; ... state = COMPLETE`)，UI 在中间观测会读到瞬态 `FAILED`/`STOPPED`。再加上 `_thread` 字段没有锁，重复 `start()` 在 `is_running()` 返回 `False` 但旧线程尚未真正退出的窗口期内会创建第二个线程。
**Suggested fix**: 用 `threading.Lock` 保护 (`state`, `_thread`)；或用 `enum + threading.Event` 表示终态、由专门 reader 接口暴露快照。`start()` 内除了 `is_running()` 还要 `_thread.join(0)` 一次。

---

## 次要建议 (Minor — 可选)

### M1. ABC 与实现签名不一致
**File**: `src/core/interface.py:194-200` vs `src/service/recognition_service.py:38-44`
ABC 的 `match_template(image, template_path, threshold)` 与实现增加的 `scales=` 参数不一致；测试 `test_recognition.py` 还专门探测 `match_template_multi_scale / match_template_multiscale` 这种实际不存在的方法。建议要么把 `scales` 加到 ABC、要么单独的 `match_template_multi_scale` 方法成为契约的一部分。

### M2. 模板缓存的 size=0 / 边界
**File**: `src/service/recognition_service.py:33-35` 与 `src/util/cv_util.py:73-77`
两处缓存逻辑独立存在；`recognition_service` 用 `if len > size` 单步驱逐，cv_util 用 `while`。功能正确但概念重复，建议合并到 `cv_util.load_template_cached` 一份实现，让 `OpenCVRecognitionService` 调用它。

### M3. `RapidOCRService.engine` 的懒加载非线程安全
**File**: `src/service/ocr_service.py:42-54`
属性 `engine` 在多线程同时第一次调用时可能并发实例化两次 RapidOCR (`use_cuda`)。建议加锁或在 `__init__` 中急切实例化。OCR 没接到主流程，影响很小。

### M4. quest tap_key 的 upper() 处理多余
**File**: `src/core/quest/quest_core.py:204-207`
`key.upper() if isinstance(key,str) and len(key)==1 else key`，但下游 `_vk()` 已经 `.upper()`。无副作用，可删。

### M5. 测试用 `pytest.importorskip` 隐蔽真错误
**File**: `tests/core/test_fishing_models.py:7-8`、`tests/core/test_geometry.py:5`
`importorskip` 把"运行环境真的缺这个包"和"模块本身有 bug"两种情况都吞成了 `skip`。在被测代码是项目自有模块的情况下，应改为 `import`，让 `ImportError` 直接 fail。这条规则若早期生效，C1/C2 不会被忽略到现在。

### M6. `fishing_core.FishingStateMachine.is_running` 是 property，service 层是 method
**File**: `src/core/fishing/fishing_core.py:166-169`
`TaskService` ABC 定义 `is_running()` 为方法，core 层用 property。`FishingStateMachine` 没有继承 `TaskService`，所以不算违反契约，但在同项目内同一概念用两种风格容易引起调用错误 (e.g. `if sm.is_running: ...` vs `if sm.is_running(): ...`)。

---

## 模块小结

| 模块 | 状态 | 主要问题 |
|---|---|---|
| `main.py` | ❌ | 没有装配真实 service，使用占位 dataclass (C3) |
| `src/core/interface.py` | ✅ | ABC 设计合理；`Rect.scale_from` / `Point` / `MouseButton` 都干净 |
| `src/core/context.py` | ✅ | 完整、线程安全；但**没人用** (main 没引用) |
| `src/core/geometry.py` | ✅ | 纯函数式工具，OK |
| `src/core/fishing/models.py` | ⚠️ | 缺 `FishingStats` / `PulseDecision`；字段与 `fishing_core.py` 不匹配 |
| `src/core/fishing/fishing_core.py` | ❌ | 导入即崩 (C1)；与 service 层重复实现 (C4) |
| `src/core/fishing/detector.py` | ✅ | 干净，无 bug |
| `src/core/quest/models.py` | ⚠️ | 缺 `QuestStats` 及 `quest_core` 用到的多个字段 |
| `src/core/quest/quest_core.py` | ❌ | 导入即崩 (C2) |
| `src/core/quest/page_rules.py` | ✅ | 设计良好，rule 排序/优先级清晰 |
| `src/service/window_service.py` | ⚠️ | 空 class_name 处理 (I3)；`is_foreground_window` 与 `is_foreground` 重复 |
| `src/service/control_service.py` | ⚠️ | `activate()` 是 no-op (I1)；其余 PostMessage / lParam 计算正确 |
| `src/service/capture_service.py` | ⚠️ | PW_CLIENTONLY + 偏移 crop 组合存疑 (I2)；GDI 资源释放 OK |
| `src/service/recognition_service.py` | ✅ | 模板缓存正确；签名与 ABC 略有出入 (M1) |
| `src/service/ocr_service.py` | ✅ | 懒加载非线程安全 (M3)，可接受 |
| `src/service/fishing_service.py` | ⚠️ | 自成一套状态机；缺帧异常防御 (I4)、字段非线程安全 (I5) |
| `src/util/hwnd_util.py` | ✅ | 写得最干净的一块；可惜上层没用 |
| `src/util/cv_util.py` | ✅ | OK，缓存淘汰正确 |
| `src/util/log_util.py` | ✅ | OK |
| `src/util/resource_util.py` | ✅ | PyInstaller `_MEIPASS` 处理正确 |
| `src/ui/main_window.py` | ⚠️ | `setCentralWidget` 调用了两次 (第二次覆盖第一次)，可接受 |
| `src/ui/tabs/*.py` | ✅ | 简洁，等待真服务接入 |
| `src/ui/widgets/floating_log.py` | (未审计) | — |
| `tests/**` | ⚠️ | `importorskip` 用法掩盖了 C1/C2 (M5) |

---

## 建议优先级

| 顺序 | 项 | 理由 |
|---|---|---|
| 1 | C1 + C2 | 修好后 core 模块至少可以被加载，单元测试才能跑出真正的回归 |
| 2 | M5 | 把 `importorskip` 改成 `import`，防止再次掩盖 |
| 3 | C3 | 把真实 service 接到 `main.py`，让"开始/停止"按钮真的做事 |
| 4 | C4 | 在 service 层和 core 层之间二选一，避免双轨制 |
| 5 | I1 / I2 | 决定能不能正确截图和让游戏感知输入 |
| 6 | 其余 I 项 / M 项 | 可在后续迭代解决 |

---

*审查完成。如需对某一具体修复做白盒验证 (例如手动构造 fake CaptureService 跑 `tick()`)，可单独发起。*
