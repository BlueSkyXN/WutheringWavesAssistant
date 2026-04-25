# NTE-Assistant 独立代码评估报告

> 评估人：Multi-Model Council（executor: claude-opus-4.7，基于 opus46/opus47/sonnet46/codex53 四份提案 + judge 综合）
> 评估对象：`/Volumes/TP4000PRO/GitHub/NTE-Assistant`
> 评估范围：只读源码 + `pytest`/`ruff` 静态运行结果；未在 Windows 实机/反作弊环境验证。
> 评分制：1–10，按 task.md 的 5 个维度算术平均得 Overall。
> 阅读尺度：按“结构良好的 NTE 自动化新 scaffold”衡量，非成熟生产系统。

---

## 0. 复核基线（执行期事实）

| 项目 | 结果 | 证据 |
|---|---|---|
| `pytest -p no:cacheprovider` | **8 passed, 1 skipped**（`tests/service/test_recognition.py` 因当前环境缺少 `cv2` 被 `pytest.importorskip("cv2")` 跳过） | 实测 0.03s |
| `ruff check .` | **失败，27 errors**（25 fixable）：F401×9 unused-import、I001×7 unsorted-imports、UP035×6 deprecated-import、UP037×3 quoted-annotation、E402×2 module-import-not-at-top | `ruff check . --statistics` |
| Core 层依赖 | Core 仅 import `src.core.*`，未引用 `src.service` / `src.ui` / `PySide6` / `win32*` | grep 全量证实 |
| README 免责声明 | 已存在“免责声明”章节（行 193），声明禁用于违反 EULA、封号自负 | `README.md:193-198` |

---

## 1. Architecture Assessment — **9/10**

### 优点（高置信，源码可证）
- **四层单向依赖严格成立**：`src/core/**/*.py` 全文件 grep 未出现 `src.service`、`src.ui`、`src.util`、`PySide6` 或 `win32*` 导入；Core 仅依赖 `src.core.interface` 内部 ABC。
- **ABC 边界清晰**：`src/core/interface.py` 定义 `WindowService` / `CaptureService` / `ControlService` / `RecognitionService` / `OCRService`，Service 层（`PostMessageControlService`、`PrintWindowCaptureService`、`OpenCVRecognitionService` 等）实现这些 ABC，UI 仅持有 Service 句柄并 `start()/stop()`。
- **Core 业务逻辑可独立测试**：`fishing_core.py` 接受 `clock` 注入；`detector.py` 仅依赖 `RecognitionService` 抽象；几何模型在 `geometry.py` 与 `models.py` 中纯数据类。

### 扣分项（高置信）
- **`src/util/hwnd_util.py` 顶层副作用**：第 17 行无平台守卫顶层 `import win32con/win32gui`，第 54 行 `enable_dpi_awareness()` 在 import 时立即执行——导致非 Windows 环境 import Util 即崩，违反“Util 应是平台中立辅助层”的契约（在本仓库的 macOS 上若 import Util 会立即失败；测试只跑 Core）。
- **DPI awareness 三处重复实现**：`hwnd_util.enable_dpi_awareness()`（import 时）+ `service/window_service.py:_enable_dpi_awareness()`（`__init__` 时）+ `main.py` 间接路径，存在“同一副作用调用多次”的风险（虽幂等，但语义混乱）。
- **Util ↔ Service 实现重复**：`util/cv_util.py` 内 `_TEMPLATE_CACHE` 与 `service/recognition_service.py` 内 LRU 模板缓存功能重叠；`util/hwnd_util.py` 部分窗口枚举/类名查找与 `service/window_service.py` 重复。`cv_util._TEMPLATE_CACHE` 在 src/ 下 grep 无 caller，属悬挂死缓存。

### 综合
架构骨架是本项目最强项；ABC 设计与 Core 隔离比绝大多数同体量自动化项目更严谨。扣 1 分主要在“Util 层平台守卫缺失 + 重复实现”这两个工程卫生问题。

---

## 2. Code Quality — **7/10**

### 优点
- 全仓 `from __future__ import annotations`，类型注解覆盖密集，dataclass / Enum 使用得体。
- docstring 风格基本一致（模块级 + 类级），关键算法（`decide_pulse`、`_apply_pulse`、`_enter_state`）有意图说明。
- `pytest` 全绿，几何/钓鱼模型/识别服务三处都有可执行用例。

### 扣分项（高置信）
- **`main.py:_construct_with_supported_kwargs` 静默 `SimpleNamespace` 回退**（行 335-343）：当 `cls(**supported)` 抛 `TypeError` 时返回 `SimpleNamespace(**kwargs)`，让明显错配的字段名在运行时静默通过，破坏 `FishingConfig` dataclass 类型契约——是 wiring 层的高危反模式。
- **同名 Enum 双份**：`QuestState` 在 `src/core/quest/models.py:13` 与 `src/core/quest/quest_core.py:41` 各定义一次；当 UI 和 Core 比较 state 时，若引用源不同会全部失败。
- **`FishingState` 枚举共 14 项，实际可达仅 6 项**：`models.py` 列出 `IDLE / SEARCH_ENTRY / DETECTING / CONFIRM_FISH / CASTING / FOLLOWING / FOLLOW_BAR / REELING / WAIT_RESULT / SUCCESS / COMPLETE / FAILED / ERROR / STOPPED`，但全文 grep `_enter_state(`/`_transition(` 的调用点仅命中 `IDLE / SEARCH_ENTRY / CASTING / FOLLOW_BAR / COMPLETE / ERROR`。**`REELING` 是死分支**——`_tick_reeling` 在 `_tick(line 194)` 派发表里被引用，但没有任何代码把 state 设为 `REELING`，因此 `_tick_reeling` 永远不会被外部 `tick()` 调用。`tests/core/test_fishing_models.py` 又把 14 项枚举全部写成不变量，反向固化死代码。
- **`FishingConfig` 字段重复**：`entry_actions` 与 `entry_templates` 两个 tuple 在 `main.py` 被填以完全相同内容（行 271-282），`tpl_*` 与 `success_template/escape_template/yellow_template` 又各定义一遍——schema 里同义字段并存，正是 `_construct_with_supported_kwargs` 这种 fallback 存在的根因。
- **依赖膨胀**：`pyproject.toml` 声明 `loguru >=0.7.0`、`pydantic >=2.0`，但 `src/` grep 0 引用。`main.py` 实际用 `logging.basicConfig`（行 178）。
- **`setup_logging` 接入断裂**：`src/util/log_util.py` 定义了完整的 `setup_logging(level, file_path, ...)`，`main.py` 却没调用，改用 `logging.basicConfig`，导致 `config.yaml` 中的 `logging.file_path` 永不生效。
- **`ActionType` 在两处定义**：`src/core/quest/models.py` 与 `src/core/quest/page_rules.py` 各有同名枚举，成员还不完全一致（与 QuestState 同病）。
- **`service/control_service.py:15-21`** 不可达 `try/except ImportError`：`MouseButton` 已经在第 13 行同模块成功 import，第 15 行的回退分支永远走不到。
- **Lint 失败**：`ruff check .` 报 27 处问题，主要为 unused-import / 未排序 import / `typing.Tuple` 等过时导入 / 测试文件 module-level import 顺序——属于纯卫生类。

### 综合
风格与类型基线相当扎实，扣分集中在 wiring 层的“同义字段并存 + 静默回退 + 死枚举固化”，这是质量天花板被压低的主因。

---

## 3. Security & Anti-Cheat Design — **5.5/10**

> 本节涉及反作弊检测面的判断**未在 Windows + NTE 实机或公开反作弊方案上验证**，所有“易被检测/可能黑屏”的措辞均为行业通识推断。

### 安全立场（正面，估值 ~8/10）
- 全仓**零内核驱动 / 零内存读 / 零 DLL 注入 / 零 hook**（grep 无 `pymem`、`ReadProcessMemory`、`SetWindowsHookEx`、`CreateRemoteThread`）。
- 输入路径基于 `PostMessage`（用户态消息泵），截图基于 `PrintWindow`（GDI），均为 Win32 公开 API；不构成“外挂”定义中的内核侵入。
- README 已声明禁止用于违反 EULA 的行为、封号自负。

### 反作弊检测面（负面，估值 ~4/10，**推断**）
- **`PostMessage` 自构 lparam**：`control_service.py:67-72` 的 `_key_lparam` 手工拼装 scancode、bit 30 / bit 31，是经典“非真实键盘事件”签名；行业通识层面 EAC / BattlEye / 部分国产反作弊会扫描此模式。**未对 NTE 实测**。
- **`PrintWindow + BitBlt` 兜底**：`capture_service.py` 当 `PrintWindow` 返回非 1 时回退 `BitBlt(SRCCOPY)`（行 75-78）。两种 GDI 路径在 D3D11/12 + UE5 全屏窗口上都有大量公开报告会黑屏 / 仅得到桌面背景；具体在 NTE（异环）上**是否可用未实测**，但 `BitBlt` 的回退在 D3D 场景中通常仅是“形式兜底”，并非真实可用路径。
- **`activate()` 与“后台输入”自相矛盾**：`control_service.py:95-100` 调用 `SetForegroundWindow` + `ShowWindow(SW_RESTORE)`——这是前台抢焦点行为，与 PostMessage 选择后台输入的初衷冲突；若 UI 真的调 `activate()`，等于主动暴露脚本运行迹象。
- **`PostMessage` 鼠标事件对 UE5 子 viewport 的兼容性**（行业通识，未实测）：`PostMessage` 投递到顶层 hwnd 的鼠标消息，常被 UE5 的 SlateViewport / 子窗口忽略，需要枚举子 hwnd 投递。`window_service` 仅暴露顶层 hwnd，`control_service.click` 直接打到 `self.hwnd`。

### 综合
评分采纳 sonnet46 的 5.5：在“无注入”这条线上立场清晰，但在“怎么投递输入 / 怎么截屏”两条具体技术路径上选择了行业里**已知有检测 signature 与兼容性问题**的实现。建议在 README/EULA 章节进一步明确反作弊与封号风险（不作为重扣项，因 README 已有免责声明）。

---

## 4. Completeness & Production Readiness — **5.5/10**

### P0 真实 bug（高置信，grep 实证）
- **🐞 `fish_count` UI 永远 ≤1**（codex53 + sonnet46 独立命中）：
  - `src/core/fishing/fishing_core.py:141-146` 的 `start()` 内执行 `self.stats = FishingStats()`，把 `success_count` 重置为 0。
  - `src/service/fishing_service.py:84-89` 的 `_run` 在每次 `tick()` 返回 `COMPLETE` 后又调用 `self.machine.start()` “re-arm for the next fish”。
  - 结果：每钓完一条立即清零，`FishingService.fish_count` 属性（行 70-71）读取的是刚被重置的 `stats.success_count`，UI 永远看不到累计计数。
  - 修法建议：把累计 `stats` 移出 `FishingStateMachine`，或给 `start(reset_stats: bool = True)` 增加可选参数，re-arm 时传 `False`。
- **`_construct_with_supported_kwargs` SimpleNamespace fallback**（main.py:335-343）：上文已述。把字段名漂移从启动期 `TypeError` 降级为运行期 `AttributeError`——用户视角下表现为“某次钓鱼/任务突然无声崩溃”。

### P1（应修，需复核或低频）
- **`humanize_ms` jitter 拉长 pulse 精度**（codex53 独家，复核成立）：
  - `control_service.py:91-115` 的 `tap_key(key, seconds)` 实现是 `key_down → _sleep(seconds) → key_up`；`_sleep(s) = time.sleep(s + uniform(*humanize_ms))`。
  - `main.py:217` 把 `humanize_ms` 默认 `[20, 80]` 转换为 `(0.02, 0.08)` 秒；`fishing_core._apply_pulse` 调 `tap_key(decision.key, seconds=decision.seconds)`，`decision.seconds` 物理范围是 `pulse_min=0.005 ~ pulse_max=0.040` 秒。
  - 即 5–40ms 的细粒度 pulse 之上**强制叠加 20–80ms 的 jitter**，pulse 物理时长被放大 1.5–17×，bar follower 的精度模型实际失效。
  - 修法建议：`tap_key` 在 fishing pulse 路径上禁用 humanize，或把 humanize_ms 默认调到 `(0, 5)` ms 量级。
- **`stop_hotkey: "F12"` 配置无消费**：`config.yaml:125` 声明，但 `main.py / src/` 全文 grep 无任何 `keyboard.add_hotkey` 或全局热键注册——纯死配置。
- **`logging.file_path` 死配置 + `setup_logging` 死代码**：上文已述。
- **`_cast_seen` 动态属性可能 AttributeError**（opus47 + sonnet46）：`fishing_core.py:349/352` 仅在 `_enter_state(SEARCH_ENTRY)` / `_enter_state(CASTING)` 时初始化 `self._cast_seen`，但 `_tick_casting` 内若被先于这两条路径触达即抛 `AttributeError`。当前调用链下未观察到，但属脆弱设计。
- **`quest action="wait"`** 在 worker 线程内 `time.sleep(seconds)`（`quest_core.py:213-218`），不响应 stop 事件——用户按停止后最长卡 `seconds` 秒。

### 死代码 / 死服务
- **`FishingState` 14 → 实际可达 6**，`REELING / DETECTING / CONFIRM_FISH / FOLLOWING / WAIT_RESULT / SUCCESS / FAILED / STOPPED` 共 8 个枚举与对应 `_tick_reeling` 死分支，且被 `tests/core/test_fishing_models.py` 反向固化为不变量。
- **`RapidOCRService`**（`src/service/ocr_service.py:34-`）实现完整但 src/ 全文 grep 无 caller；属 WIP 死服务，应明确标注或移入 `experimental/`。
- **`util/cv_util.py:_TEMPLATE_CACHE`** 无 caller，与 `recognition_service` LRU 重复。
- **`MainWindow.__init__` 双重 `setCentralWidget`**：`src/ui/main_window.py:68` 先把 `self.tabs` 设为 central widget；行 83 又把 `wrapper` 设为 central widget，第一次调用属 dead call（QMainWindow 会丢弃旧 central widget），属卫生类残留代码。

### 关于 `inter_pulse_sleep_ms`
- **该字段并非死配置**：`src/core/fishing/fishing_core.py:386` 的 `_apply_pulse` 实际读取 `self.config.inter_pulse_sleep`，用作连续 pulse 之间的合并窗口。
- 但需指出：`config.yaml:46` 的 `inter_pulse_sleep_ms: 10` 当前**未在 `main.py:create_fishing_service` 的 `config_kwargs` 中被透传**，`FishingConfig.inter_pulse_sleep` 始终是 dataclass 默认 `0.0`。这是 wiring 层的小遗漏，但不应将该字段本身称为“dead config”。

### 测试覆盖
- 仅 3 个测试文件、169 行；状态机 / 服务层 / wiring 层 0 测试。`test_fishing_models` 把 14 项枚举写死，反而锁住了 8 个死成员的“实在性”。

### 综合
架构与单元粒度的 Core 测试令人放心，但**有 1 个 P0 真实 bug（fish_count）+ 1 个 P0 wiring 反模式（SimpleNamespace 回退）+ 死配置/死代码若干**。

---

## 5. Portability & Extensibility — **8/10**

### 优点
- ABC 替换路径清晰：要换截图实现（如 Windows Graphics Capture / DXGI），只需新写一个 `CaptureService` 实现并在 `create_service_chain` 替换；要换识别（OCR、ONNX、CLIP），同理。
- `FishingConfig` / `QuestConfig` 全部走 dataclass，`config.yaml` 路径以 `_resolve_app_path` 兜底，方便挪到其他游戏。
- 状态机与 Win32 完全解耦，理论上 Linux/X11 下只要写一份 `xdotool` 版 `ControlService` + `xwd` 版 `CaptureService` 就能跑核心算法。

### 扣分项
- **缺插件注册机制**：当前要新增一个 “quest 第三种动作”，需要同时改 `models.py` 的 `ActionType` + `quest_core.py` 的 dispatch + `page_rules.py` 的 `ActionType` 副本，没有装饰器/注册表来集中扩展。
- **平台守卫缺失**：`util/hwnd_util.py` 顶层 `import win32*` 没有 `sys.platform == "win32"` 守卫，跨平台 import 即崩。
- **缺 `import-linter` / CI 强制依赖方向**：当前 Core 干净是约定俗成，没有机器化守门，未来一个 `from src.service` 的反向 import 会直接合入。

### 综合
ABC 替换与配置驱动两条路径都已铺开；扣分在“扩展点尚未机械化”。

---

## 6. Identified Issues（汇总，按优先级）

> 凡是“代码事实可 grep 证实”的标 ✅；凡是依赖未实测假设的标 🅿️（推断）。

### P0 — 必修
| # | 问题 | 证据 | 类型 |
|---|---|---|---|
| 1 | `fish_count` UI 永远 ≤1，`start()` 重置 stats + `_run` re-arm | `fishing_core.py:141-146` + `fishing_service.py:84-89` | ✅ |
| 2 | `_construct_with_supported_kwargs` 静默 `SimpleNamespace` 回退，破坏 dataclass 类型契约 | `main.py:335-343` | ✅ |
| 3 | `QuestState` 同名双份枚举（models / quest_core） | `quest/models.py:13` + `quest/quest_core.py:41` | ✅ |
| 4 | `FishingState` 14→6 可达，`REELING` 等 8 项死代码且被 `test_fishing_models` 反向固化 | `fishing_core.py` grep `_enter_state` / `_transition` | ✅ |

### P1 — 应修
| # | 问题 | 证据 | 类型 |
|---|---|---|---|
| 5 | `humanize_ms` jitter 拉长 pulse：5–40ms pulse 上叠加 20–80ms sleep | `control_service.py:91-115` + `main.py:217` + `fishing_core._apply_pulse` | ✅（设计冲突） |
| 6 | `stop_hotkey: F12` 配置无消费 | `config.yaml:125` + grep 无 hotkey | ✅ |
| 7 | `setup_logging` 死代码，`logging.file_path` 死配置（main.py 改用 `basicConfig`） | `util/log_util.py` + `main.py:178` | ✅ |
| 8 | `MainWindow.__init__` 双重 `setCentralWidget` | `src/ui/main_window.py:68` 与 `:83` | ✅ |
| 9 | `_cast_seen` 动态属性可能 AttributeError（仅在 SEARCH_ENTRY/CASTING 进入时初始化） | `fishing_core.py:349/352` | ✅（边界） |
| 10 | `hwnd_util` 顶层 `import win32*` + import 时执行 `enable_dpi_awareness()` | `util/hwnd_util.py:17/54` | ✅ |
| 11 | `quest action="wait"` 用 `time.sleep` 阻塞 worker，stop 后最长卡 `seconds` 秒 | `quest/quest_core.py:213-218` | ✅ |
| 12 | `FishingConfig` 同义字段并存（`entry_actions`/`entry_templates`、`tpl_*` 与 `success_template` 等） | `models.py:50-110` + `main.py:271-303` | ✅ |
| 13 | `inter_pulse_sleep_ms` 在 `config.yaml` 已声明但未被 `main.py` 透传到 `FishingConfig.inter_pulse_sleep`（字段本身被 `_apply_pulse` 使用，非死字段） | `config.yaml:46` + `main.py:256-305` + `fishing_core.py:386` | ✅ |

### P2 — 卫生 / 文档
| # | 问题 | 证据 | 类型 |
|---|---|---|---|
| 14 | `pyproject.toml` 声明 `loguru` / `pydantic` 但 src/ 0 引用 | `pyproject.toml:34/38` + grep | ✅ |
| 15 | `RapidOCRService` 整模块无 caller，属 WIP 死服务 | `service/ocr_service.py` + grep | ✅ |
| 16 | `cv_util._TEMPLATE_CACHE` 无 caller，与 `recognition_service` LRU 重复 | `util/cv_util.py` + grep | ✅ |
| 17 | `ActionType` 在 `quest/models.py` 与 `quest/page_rules.py` 重复，成员不完全一致 | grep | ✅ |
| 18 | `service/control_service.py:15-21` 不可达 `try/except ImportError`（同模块第 13 行已 import 成功） | 源码静态可证 | ✅ |
| 19 | `ruff check .` 27 errors（F401/I001/UP035/UP037/E402），25 项 fixable | 实测 | ✅ |
| 20 | DPI awareness 三处重复实现（`hwnd_util` import 时 + `window_service.__init__` 时） | grep `enable_dpi_awareness` | ✅ |
| 21 | 缺 `import-linter` / CI 强制依赖方向 | 仓库无 `.importlinter` | ✅ |
| 22 | README 免责声明可进一步明确 EULA 条款引用与反作弊封号风险（**不作扣项**，已有基础免责） | `README.md:193-198` | ✅ |
| 23 | `PrintWindow + BitBlt` 在 D3D11/12 + UE5 上有黑屏风险 | 行业通识 | 🅿️（未实测） |
| 24 | `PostMessage` 自构 lparam 是常见反作弊检测 signature | 行业通识 | 🅿️（未实测） |
| 25 | `PostMessage` 鼠标事件对 UE5 子 viewport hwnd 可能被忽略 | 行业通识 | 🅿️（未实测） |

---

## 7. Overall Assessment

### 7.1 维度评分

| 维度 | 分数 |
|---|---|
| Architecture | 9.0 |
| Code Quality | 7.0 |
| Security & Anti-Cheat | 5.5 |
| Completeness & Production Readiness | 5.5 |
| Portability & Extensibility | 8.0 |
| **Overall（算术平均）** | **7.0 / 10** |

### 7.2 双重叙述（推荐管理者快速读这两行）

- **架构 9 / 10**：四层 ABC 隔离、Core 零平台依赖、可测试粒度高，是同体量项目里少见的“工程上有节制”的 scaffold。
- **实现 6 / 10**：wiring 层（main.py 的 SimpleNamespace 回退、stats 重置、humanize 淹没 pulse、setup_logging 未接入、stop_hotkey 死键）有真 P0 bug 与多处死代码/死配置；测试覆盖薄。

### 7.3 核心优势
1. Core 真正不依赖 win32/Qt（grep 实证），ABC 设计可替换。
2. 类型注解、docstring、dataclass、`pytest` 全绿——代码风格基线高于多数自动化项目。
3. README 已有免责声明、AGPL-3.0 许可、明确指向 WWA 的工程渊源。

### 7.4 核心弱点
1. **`fish_count` UI 永远归零** 是用户立即可感的 P0 bug。
2. **`_construct_with_supported_kwargs` 静默回退 + `FishingConfig` 同义字段并存** 是 wiring 层最大健壮性威胁。
3. **`humanize_ms` 完全淹没 `decide_pulse` 5–40ms 物理模型**，bar follower 控制精度名存实亡（设计层洞察）。
4. **测试体量过小、状态机 0 测试、`test_fishing_models` 反向固化死枚举**，未来重构风险高。
5. **反作弊检测面（PostMessage + PrintWindow）在行业通识层面易被识别**，需在 Windows + NTE 实机验证（本评估**未实测**）。

### 7.5 评分尺度声明
- 本次给 7.0/10，与 four-proposer 中位完全一致。
- 不给 ≥7.5：忽略 fish_count P0 bug 与 SimpleNamespace fallback 不诚实。
- 不给 ≤6.5：本项目自我定位为 alpha scaffold，README 已声明 status，按“结构良好的 NTE 自动化起点”尺度衡量，过分苛责架构外的 wiring 失误违背 task.md。

### 7.6 未在本评估中验证（明确声明）
- PrintWindow / BitBlt 在 NTE 实际窗口（UE5 + D3D11/12）上是否能拿到非黑屏画面。
- NTE 是否使用 EAC / BattlEye / 自研反作弊，及 PostMessage + 自构 lparam 是否会触发其检测。
- PostMessage 鼠标事件在 NTE 顶层 hwnd 上是否被 SlateViewport 接收。
- `_cast_seen` AttributeError 是否在真实运行路径上被触发（当前 grep 调用链未发现可达路径）。

以上四点应由 Windows + NTE 实机回归补充。
