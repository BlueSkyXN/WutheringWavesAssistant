# NTE-Assistant 项目独立评审报告

> 评审对象：`/Volumes/TP4000PRO/GitHub/NTE-Assistant`（v0.1.0，alpha）
> 评审范围：`src/`、`main.py`、`tests/`、`config.yaml`、`docs/`、`pyproject.toml`
> 定位前提：项目自我定位为 *"freshly scaffolded、面向异环（NTE）的、受 WWA 启发的 4 层架构起点"*，按此基准评价（不按成熟生产系统标准）。
> 测试基线：`pytest -q` → 8 passed（macOS 下，无 Win32 覆盖）。
> 静态依赖检查：`grep -E "(PySide|win32|pywin|cv2)"` 在 `src/core/**/*.py` 下 0 命中；`src/util/*.py` 无 `from src` 反向导入。

---

## 1. 架构评估（Architecture）— 9 / 10

### 优点

- **接口与实现真正分离**：`src/core/interface.py` 把 `WindowService` / `ControlService` / `CaptureService` / `RecognitionService` / `TaskService` 全部以 `ABC` 形式声明，并配套不可变数据类（`Point`、`Rect`、`MatchResult`、`FishingDetection`）。Service 层每个文件都显式 `class XxxService(YyyService)` 实现对应 ABC，签名一致、对偶清晰。
- **依赖方向严格单向**：实测 grep 显示 `src/core/**` 没有任何 `import win32 / pywin / cv2 / PySide6`，`src/util/**` 没有反向 `from src.<其他>` 导入。`docs/architecture.md` 第 2.1 节定义的 5 条 *Dependency Rules* 在代码层得到落实，4 层结构 `UI → Service → Core → Util` 真实成立。
- **组合根（Composition Root）规范**：`AppContext`（`src/core/context.py`）以可空字段 + `require_*()` 方式延迟绑定，避免了"半初始化对象传播"的反模式；同时把 `_stop_event` / `_state_lock` 收纳进上下文，给跨线程停止协议留好钩子。
- **几何与坐标抽象到位**：`Rect.scale_from(base, target)` 与 `Scaler` / `make_scaler` / `client_to_screen` 构成完整的"分辨率无关 → 客户区像素 → 屏幕像素"管道，符合文档描述的 *1920×1080 基准 + 运行时缩放* 设计。
- **`TaskService` 抽象**：`FishingService` 与 `ThreadedQuestService` 都遵循 `start / stop / is_running` 的统一生命周期，UI 不需要关心后端细节，便于以后追加 `QuestTrackerService`、`OcrService` 等长任务。

### 瑕疵

- **`ThreadedQuestService` 没有放进 Service 层**（定义在 `main.py`）。`FishingService` 在 `src/service/fishing_service.py` 已经做了线程化封装，`Quest` 完全可以照葫芦画瓢。当前结构让 `main.py` 同时承担"组装容器 + 提供 Service 实现"两件事，是少数破坏对称性的地方。
- **`AppServices` ≠ ABC**：`AppServices` 在 `main.py` 里以 `dataclass` 定义，UI 通过 `getattr` 风格 (`getattr(self.services, "window_service", None)`) 访问，类型契约偏弱。文档建议的 `ServiceContainer` 概念在代码里没有 ABC 化。
- **`OCRService` 未在 `interface.py` 中暴露**，而是直接定义在 `src/service/ocr_service.py`（同时是 ABC + 实现）。属于轻微的"分层不一致"，但 OCR 本身被列为可选 extras，可以接受。
- **`AppContext.config: dict[str, Any]`** 与 `Pydantic` 已经引入（`pyproject.toml`）但完全未使用——配置可以在 Core 层用 Pydantic Model 校验，目前是裸 dict。

---

## 2. 代码质量（Code Quality）— 7.5 / 10

### 优点

- **风格高度一致**：全部模块以 `from __future__ import annotations` 开头；类型标注完整（`int | None`、`tuple[int, int]`、`Sequence[...]` 等 PEP 604 语法）；命名一致（snake_case 函数 / PascalCase 类 / `_protected` 前缀）；行长 100；ruff 规则集 `E/F/I/UP/B`。
- **文档与注释**：Core 层每个模块顶部都有 docstring 说明定位与禁止项；公开方法多数附 Google 风格 docstring（Args / Returns）。`fishing_core.py` 顶部对状态迁移的描述写得相当清楚。
- **错误处理范式统一**：到处使用 `logger.exception("...")` 在 `except Exception:` 中输出栈，且常见模式是"记录日志 + 转 ERROR 状态 + 让外层重试"，没有发现裸 `pass`、`print` 或吞异常。
- **资源释放路径完备**：`PrintWindowCaptureService._capture_window` 以 `try/finally` 释放 GDI 资源（`SelectObject`/`DeleteObject`/`DeleteDC`/`ReleaseDC`），是 win32 截图最常见的内存泄漏雷区，这里处理得正确。
- **单元测试可移植**：`tests/` 在 macOS 上能直接 `pytest -q` 通过，证明 Core 层确实摆脱了 win32 依赖。

### 问题

> 详见第 6 节"已识别问题"清单。这里仅列高频质量问题：

- **重复 / 死代码**：
  - `QuestState` 在 `src/core/quest/models.py`（`IDLE/SCANNING/ACTING/WAITING/STOPPED`）与 `src/core/quest/quest_core.py`（`IDLE/SCANNING/ACTING/ERROR`）**两处定义且枚举成员不一致**。`quest_core.py` 自己定义后从未引用 `models.py` 的版本。
  - `TemplateAction` 在 `models.py` 定义，但实际使用的是 `page_rules.py` 中的 `PageRule`；`TemplateAction` 没有任何引用方。
  - `FishingState` 有 14 个成员，但 `fishing_core.py` 只用到 7 个；多余成员（`DETECTING/CONFIRM_FISH/FOLLOWING/WAIT_RESULT/SUCCESS/FAILED/STOPPED`）只为通过 `test_fishing_state_enum_contains_runtime_states` 这一断言而存在，是测试驱动出来的"占位枚举"。
- **`main.py` 的 `_construct_with_supported_kwargs` 是反模式**：用 `inspect.signature` 过滤合法 kwargs，并在 `TypeError` 时**回退到 `SimpleNamespace`**。这意味着当 `FishingConfig` 字段名漂移时，`FishingService` 将拿到一个伪对象、运行时再以 `AttributeError` 崩溃，**默默丢失类型校验**。同时 `config_kwargs` 里同时塞了 `entry_actions` / `entry_templates`、`confirm_templates` / `cast_confirm_templates`、`tpl_entry_prompt` 与一份重复的别名 dict，是历史遗留兼容层未清理。
- **`MainWindow.setCentralWidget` 被调用两次**（先 `self.tabs`，后 `wrapper`），第一次是死代码；说明重构时遗漏。
- **`PostMessageControlService` 中的 `MouseButton` 兼容 `try/except ImportError`** 不可达——`MouseButton` 始终存在于 `interface.py` 同一个 `from` 语句里。
- **`Win32WindowService` 暴露的方法（`status` / `window` / `get_client_rect` / `get_client_origin` / `get_window_rect`）超出 ABC 契约**，UI 层依赖了非 ABC 字段（`getattr(service, "status", "未连接")`），契约边界被撑开。
- **`humanize_ms` 命名误导**：`PostMessageControlService.humanize_ms` 实际接受的是**秒**（`main.py` 已 `/1000`），名字仍叫 `_ms`，调用方容易传错。
- **`Pydantic` 已是依赖但未使用**；`hwnd_util.py` 与 `Win32WindowService` 同时存在两套窗口查找实现，未复用，未来易漂移。

---

## 3. 安全 & 反作弊设计（Security & Anti-Cheat）— 7 / 10

> 评分基于"对常见反作弊手段的暴露面"，不构成对实际游戏检测策略的承诺。

### 输入侧（PostMessage）

- **`PostMessageControlService` 实现正确性**：
  - `_key_lparam` 调用 `MapVirtualKey(vk, 0)` 取真实扫描码并组装 `lparam`，`WM_KEYUP` 加上 `KF_REPEAT(30) | KF_UP(31)` 位，符合 Windows 文档；不是常见的"`lparam=0`"草率写法。
  - 使用 `WM_LBUTTONDOWN/UP` + `MK_LBUTTON` 以及 `MAKELONG(x, y)` 编码鼠标坐标——这是 PostMessage 鼠标点击的标准做法。
  - `release_all()` 维护 `_pressed: set[int]` 并在停止时全部 `WM_KEYUP`，避免"按键卡死"。
  - `humanize_ms` 抖动给输入加上 0–10ms 随机延迟，能稍微打散机械周期。
- **可改进点**：
  1. **未发送 `WM_MOUSEMOVE`** 与 `WM_SETCURSOR`：很多 Unreal 游戏在 LBUTTONDOWN 之前需要 hover 信号才会触发 hitbox，这是导致"PostMessage 点击无效"的最常见单点。
  2. **方向键未设置 `KF_EXTENDED`（bit 24）**：`Left/Up/Right/Down/Insert/Delete/Home/End/PageUp/PageDown` 在 lparam 上需要置位，否则部分 UE 游戏的 InputComponent 不会识别。
  3. **`PostMessage` 对 `RawInput / DirectInput` 完全无效**：异环（NTE）作为 UE5 项目，移动操作很可能走 RawInput，需要确认实测；当前架构允许换成 SendInput / Interception，但 ABC 没有暴露"是否走前台输入"的 capability flag。
  4. **`activate()` 主动 `SetForegroundWindow`**：在 `_tick_wait_bite` / 启动路径中如被调用，会把窗口拉到前台，**抹掉了 PostMessage 后台输入的最大价值**。建议把 `activate()` 调用收紧为"用户显式请求"。
  5. **`humanize_ms = (0.0, 0.010)`** 默认范围只有 10ms，过窄；YAML 默认 20–80ms 反而更合理，但 `PostMessageControlService` 默认参数应同步改宽。

### 截图侧（PrintWindow + GDI）

- **实现正确**：使用 `PW_RENDERFULLCONTENT(0x2)` 标志，是 Win10+ 抓取硬件加速 UE 窗口的关键；`PrintWindow` 失败时回退 `BitBlt(SRCCOPY)`。`DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` 用于裁出"真实客户区"，规避 DWM 投影边距，思路与 WWA / OBS 一致。
- **风险**：
  1. **`PrintWindow` 在某些 UE5 D3D12 全屏独占模式下返回纯黑帧**，需要外部约束玩家以"无边框窗口"模式运行；项目文档目前没强调这一点。
  2. 没有节流——`screenshot()` 每次都做完整 GDI 路径（`GetWindowDC` → `CreateCompatibleDC` → `CreateCompatibleBitmap` → `PrintWindow` → `cvtColor`），10–20Hz 调用下 CPU 与 GDI 句柄消耗不低；可考虑复用 DC / bitmap 池。
  3. 未来若切到 Windows Graphics Capture（WGC）可显著降低开销，当前 `CaptureService` ABC 已经能容纳替换，是好的预留。

### 反作弊视角

- **加分**：纯外部进程 + PostMessage + GDI 截图，**无 hook、无内存读、无 DLL 注入、无驱动**，对 AC 暴露面比 SendInput 注入小很多。
- **扣分**：所有按键/点击均带固定 lparam scan code 与"发包-松开"间隔 ≤ 50ms 的极小抖动，**节奏指纹明显**；建议引入正态分布抖动 + 宏观节奏混淆（按键间隔从 50–250ms 变化）。
- **License & 法律面**：项目 AGPL-3.0，README 与 CHANGELOG 多处明示"游戏自动化"用途；建议在 README 加入"使用风险自负 / 不挑战 ToS"的免责声明（对开源仓库本身无强制要求，只是工程惯例）。

---

## 4. 完整度 & 生产就绪度（Completeness & Production Readiness）— 6 / 10

### 已就绪

- **Core / Service / Util / UI 四层骨架完整**，端到端可走通："启动 → 加载 YAML → 组装 Win32 服务 → UI 启动 → 点击开始 → 后台线程 tick → PostMessage / PrintWindow"。
- **配置系统可用**：`config.yaml` 字段齐全，覆盖钓鱼 ROI / HSV / 模板 / 控制脉冲、剧情模板表、输入抖动、日志、UI 主题。
- **日志体系**：根 logger 在 `main.configure_logging()` 初始化；`src/util/log_util.py` 还提供了带颜色、TTY 检测、Rotating file 的更完整版本；UI 通过 Qt `Signal` 转发到全局日志区与悬浮日志窗。
- **测试**：`tests/core/test_geometry.py`、`test_fishing_models.py`、`tests/service/test_recognition.py` 共 8 例全部通过；覆盖了 `Rect.scale_from`、`FishingDetection` 几何、模板匹配 + HSV 检测的端到端能力。

### 不足

- **`util/log_util.py` 未被 `main.py` 使用**：实际仍是 `logging.basicConfig`，`max_bytes` / 文件轮转 / 颜色全部失效；`config.yaml` 的 `logging.file_path` 未被消费。
- **测试覆盖偏单元**：没有 `FishingStateMachine.tick` 的状态机回放测试（用 fake `CaptureService/RecognitionService/ControlService` 喂帧序列的集成测试）。`page_rules.PageRuleEngine.find_first/find_best` 也没有用例。`test_fishing_state_enum_contains_runtime_states` 是反过来推动 enum 添加成员，**测试驱动了死代码**。
- **错误恢复**：`FishingService._run` 在 `ERROR` 后 `machine.start()` 重试，但**无退避上限 / 无连续失败计数**（`config.yaml` 的 `max_consecutive_failures` 字段没有任何 Python 端读取者）；类似地 `result_timeout_s` / `max_session_minutes` / `inter_pulse_sleep_ms` / `debug.show_roi` / `debug.save_frames` / `debug.frame_dir` 全部在 YAML 里写明、**代码里未读取**。即"配置承诺 ≫ 代码兑现"。
- **桥接代码异味**：`main.py` 里大量 `_construct_with_supported_kwargs` / `LazyTaskService` / `SimpleNamespace` fallback 表明 Core 数据类与 Service / 配置层签名仍在演化。当前可跑通，但任何字段变更都需要再读一遍 `main.py`，不是稳定状态。
- **Windows 实测缺位**：所有 Win32 路径在 macOS 上没有 mock 测试覆盖，`PrintWindowCaptureService.screenshot` 的回归依赖手测。
- **CHANGELOG 与 README 与代码已存在小幅漂移**（如"`fishing_core.py` 仍处于待修复状态"vs. 实际可运行）。

---

## 5. 可移植性 & 可扩展性（Portability & Extensibility）— 8.5 / 10

- **新增一个游戏内特性**（如"识别紫色提示并触发动作"）：`docs/development.md` 给出了清晰 Step1–6 路径——只需扩 `FishingConfig` 字段、在 `detector.py` 加纯函数、在 `fishing_core.py` 接入、在 YAML 注册参数。Core 改动**完全无需碰 win32 / Qt**。这条路径在代码里是真实可走的（不是只在文档里画饼）。
- **替换截图后端**（PrintWindow → WGC / DXCam）：只需新增一个实现 `CaptureService` 的类，并在 `create_service_chain` 里换一行；`PrintWindowCaptureService` 的实现也已经把 DPI、DWM 偏移、4→3 通道转换封装在内，新后端只要返回 RGB ndarray 即可对齐。
- **替换输入后端**（PostMessage → SendInput / Interception）：同样只需新 `ControlService` 实现。**唯一要补的**是在 `interface.py` 暴露"是否需要前台 / 是否走 RawInput"等 capability flag，目前 ABC 没体现这一约束。
- **跨游戏复用**：核心抽象（`Rect.scale_from`、`PageRule` 优先级匹配引擎、`FishingStateMachine` 的 tick 模型）与"异环"无强绑定。要新增一款游戏：替换 `assets/`、改 `game_window` 段、提供新的 `PageRule` 列表即可；状态机骨架可以共用。
- **可测试性**：Core 完全无 Qt / win32 依赖，`FishingStateMachine.__init__` 把所有协作者注入，配 `clock` 钩子；可以用 `MagicMock` 喂任意帧序列做回放测试，门槛极低（**虽然项目还没写**）。

扣分点：
- 没有 CI / `import-linter`，分层规则纯靠人盯 grep；未来很容易被新贡献者无意打破。
- `OCRService` ABC 写在 `src/service/ocr_service.py` 而不是 `src/core/interface.py`，新人模仿时可能也把 ABC 写到 service 层。

---

## 6. 已识别问题清单（Identified Issues）

> 严重度：🔴 阻塞 / 🟠 应修 / 🟡 建议改进。

### 🟠 应修（可能在运行期暴露）

| # | 位置 | 问题 |
|---|------|------|
| A1 | `src/core/quest/models.py` vs `quest_core.py` | `QuestState` 双重定义且成员不一致；`TemplateAction` 是死代码。需统一到一个文件，并删除未引用版本。 |
| A2 | `src/core/fishing/models.py` `FishingState` | 14 个成员中 7 个未被状态机引用，仅为满足旧测试断言而存在；与 `fishing_core.py` 的真实状态集对不齐，调试时会产生混淆。 |
| A3 | `main.py:_construct_with_supported_kwargs` | `TypeError` fallback 到 `SimpleNamespace` 会**静默掩盖配置漂移**，下游 `FishingStateMachine` 拿到伪对象后才崩。建议直接 raise，或在 `FishingConfig` 引入 Pydantic 校验。 |
| A4 | `main.py:create_fishing_service` `config_kwargs` | 同时塞入 `entry_actions/entry_templates`、`confirm_templates/cast_confirm_templates`、`tpl_*` 等多份别名——是历史兼容层；建议清理为唯一权威字段。 |
| A5 | `src/service/control_service.py:click` | 缺 `WM_MOUSEMOVE` / `WM_SETCURSOR` 前置消息；UE 项目下点击命中率会受影响。 |
| A6 | `src/service/control_service.py:_key_lparam` | 方向键 / Insert / Delete / Home / End / PageUp / PageDown 未设 `KF_EXTENDED (bit 24)`；部分游戏识别失败。 |
| A7 | `main.py:configure_logging` | 没有用 `src/util/log_util.setup_logging`；YAML 中 `logging.file_path` / `max_bytes` / 颜色全部失效。 |
| A8 | `main.py / FishingService` | `config.yaml` 中 `max_consecutive_failures` / `max_session_minutes` / `inter_pulse_sleep_ms` / `debug.*` 等字段从未被读取。配置与代码承诺不一致。 |
| A9 | `src/ui/main_window.py:78–83` | `setCentralWidget(self.tabs)` 立即被 `setCentralWidget(wrapper)` 覆盖，第一次调用是死代码。 |
| A10 | `src/service/control_service.py:activate` | 主动调用 `SetForegroundWindow`，与"PostMessage 后台输入"的设计意图冲突；建议默认不触发，由 UI 显式请求。 |

### 🟡 建议改进

| # | 位置 | 问题 |
|---|------|------|
| B1 | `Win32WindowService` | 公开了一组 ABC 之外的属性（`status`/`window`/`get_client_rect`/`get_window_rect`），UI 已经依赖；建议把这些晋升到 `WindowService` ABC，或在 UI 侧只走 ABC。 |
| B2 | `PostMessageControlService.humanize_ms` | 字段命名是 `_ms` 但实际单位是秒（`main.py` 已 `/1000`）。建议改名 `humanize_seconds` 或转回毫秒。默认值 `(0, 0.010)` 也比 YAML 配的 20–80ms 窄太多。 |
| B3 | `PostMessageControlService` | `MouseButton` 的 `try/except ImportError` 分支不可达。 |
| B4 | `OCRService` | ABC 应迁到 `src/core/interface.py` 或 `src/core/ocr/`，与其他 Service 对齐。 |
| B5 | `Pydantic` 已是依赖但未使用 | 给 `FishingConfig` / `QuestConfig` / 整个 `config.yaml` 做 Pydantic 校验，能干掉 `_construct_with_supported_kwargs` 与多个 `_pair/_triple/_rect` helper。 |
| B6 | `hwnd_util.py` 与 `Win32WindowService` | 两套窗口查找/客户区计算实现；建议 Service 层复用 util 函数。 |
| B7 | `tests/` | 缺 `FishingStateMachine.tick` 的状态机回放测试与 `PageRuleEngine` 用例；`test_fishing_state_enum_contains_runtime_states` 反向驱动死代码，建议删除或重写。 |
| B8 | `ThreadedQuestService` | 定义在 `main.py`，应迁到 `src/service/quest_service.py` 与 `FishingService` 对称。 |
| B9 | `PrintWindowCaptureService` | DC / bitmap 每帧重建，可池化复用以降低 GDI 开销。 |
| B10 | CI | 缺 GitHub Actions / `import-linter` 配置，分层规则没有自动护栏。 |
| B11 | `PostMessageControlService._sleep` | 抖动只在 `humanize_ms` 范围内、且非高斯，节奏指纹明显；建议 `random.gauss(mu, sigma)` + 宏观节奏混淆。 |
| B12 | `FishingService._run` | `ERROR` 后只 sleep `action_delay`（默认 0.02s）就 `machine.start()` 重试，相当于无退避；应做指数退避 + 上限。 |

### 🔴 阻塞

无。当前所有阻塞级问题（C1–C4）按用户描述已在 0.1.0 修复，本次评审未在静态阅读中发现新的阻塞缺陷（动态阻塞需在 Windows 实机上跑过才能确认）。

---

## 7. 总体评价（Overall Assessment）

**综合分：8.0 / 10**（按"刚搭好的、定位为可演进起点的项目"基准）

### 关键优势

1. **架构纪律真实落地**：分层不是 PPT，是代码。Core 完全脱离 win32 / Qt，可在非 Windows 跑测试，是这类项目少见的优秀基线。
2. **接口设计成熟**：`CaptureService`、`ControlService`、`RecognitionService`、`TaskService` 的粒度恰当，既覆盖现有需求，又给 WGC / SendInput / 多模型 OCR 等替换留出干净接缝。
3. **PostMessage + PrintWindow 实现技术细节正确**：`KF_REPEAT/KF_UP` 位、`PW_RENDERFULLCONTENT`、`DwmGetWindowAttribute` 裁剪、Unicode 路径 `imdecode`、GDI `try/finally` 释放、模板 LRU 缓存——这些都是踩过坑才会写出来的代码。
4. **代码风格 / 类型 / 注释一致性高**，新人 onboarding 成本低；`docs/architecture.md` 与 `docs/development.md` 写得务实，可直接当 contributor 手册。

### 关键弱点

1. **配置 ↔ 代码契约松**：`config.yaml` 里有大量字段无人消费（`max_consecutive_failures`、`debug.*`、`logging.file_path` 等），`main.py` 用 `inspect.signature` + `SimpleNamespace` fallback 桥接 `FishingConfig`，是当前最大的工程债。
2. **死代码 / 重复定义**：`QuestState` 双重定义、`TemplateAction` / 多余 `FishingState` 成员、`MouseButton` 兼容分支、`hwnd_util` 与 `Win32WindowService` 双实现等，提示重构尚未收敛。
3. **输入侧的"反作弊指纹"未优化**：抖动窗过窄、扩展键标志位缺失、点击前缺 hover——在 UE5 游戏上有真实命中率风险。
4. **测试只盖到了纯函数**：状态机、规则引擎、Win32 服务都没有集成测试或 fake 化测试；`test_fishing_state_enum_contains_runtime_states` 甚至反向制造了死代码。
5. **CI / 静态架构守护缺位**：当前的"4 层不互染"完全靠 review 与人脑 grep，技术债很容易复发。

### 一句话定性

> **作为"为异环重构 NTE-ai"的 0.1.0 起点，这是一份分层架构与接口契约都做对了的工程骨架；离生产就绪还差一轮"配置-代码闭环 + 状态机集成测试 + 输入策略硬化"，但底子很好，沿着 `docs/development.md` 的路径推下去几乎不会走偏。**

### 分项评分汇总

| 维度 | 分数 |
|------|------|
| 架构 | **9.0** |
| 代码质量 | **7.5** |
| 安全 / 反作弊 | **7.0** |
| 完整度 / 生产就绪 | **6.0** |
| 可移植 / 可扩展 | **8.5** |
| **综合** | **8.0** |

---

*评审完成。如需对某一具体问题（A1–A10 / B1–B12）出修复 PR 草案，可单独发起。*
