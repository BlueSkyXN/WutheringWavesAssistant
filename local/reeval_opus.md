# NTE-Assistant 第二轮独立评估报告（Opus）

> 评估对象：`/Volumes/TP4000PRO/GitHub/NTE-Assistant`
> 评估范围：`src/`、`main.py`、`config.yaml`、`tests/`、`pyproject.toml`
> 基线：`pytest tests/ -q` → **8 passed**；`ruff check .` → **All checks passed**
> 上轮分数：Opus 8.0 / GPT-5.5 7.0

---

## 维度评分

| 维度 | 分数 | 简评 |
|---|---|---|
| 1. Architecture（架构） | 8.5 | 分层清晰、ABC 干净；`AppContext` 与 `QuestRuntimeConfig` 仍有冗余 |
| 2. Code Quality（代码质量） | 7.5 | ruff 全过、类型完整；但仍存在 dead code 和未消费配置 |
| 3. Security & Anti-Cheat（安全与反封号） | 8.0 | PostMessage + PrintWindow 后台输入路径稳；jitter 默认值得当 |
| 4. Completeness（完整度） | 6.5 | 测试仅 8 条且无 quest/fishing 状态机覆盖；多处 config 字段未消费 |
| 5. Extensibility（可扩展性） | 8.0 | ABC + 工厂注入良好，加新 service / rule 容易 |

---

## 1. Architecture — 8.5

**优点**
- `src/core/interface.py` 给出干净 ABC（`WindowService` / `ControlService` / `CaptureService` / `RecognitionService` / `TaskService`），core 层不引入任何 win32/Qt 依赖（验证：`grep "win32\|PySide6" src/core/` 无结果）。
- `main.py` 的 `create_service_chain` + `create_app_services` 组合根（composition root）模式干净；`LazyTaskService` 在 UI 未连接窗口前不实例化真实 service，符合"按需启动"的预期。
- `core/fishing/fishing_core.py` 的状态机与 I/O 完全解耦；`decide_pulse` 是纯函数，便于单测（虽然目前没人写）。
- `PageRuleEngine` / `FishingBarDetector` 单一职责，且能按 config 热重载（`detector.reload`）。

**待改**
- **`QuestConfig` vs `QuestRuntimeConfig` 双轨制**（`main.py:83` vs `src/core/quest/models.py:55`）：两者字段重叠（template_dir / match_threshold / scan_interval / action_delay / error_backoff / click_seconds / tap_seconds / default_key），`QuestAutomation` 类型注解写的是 `QuestConfig`，但运行时 `main.py` 注入的是 `QuestRuntimeConfig`，靠 duck-typing 凑齐。这正是上轮 P0 "QuestState/ActionType dedup" 该顺手处理掉的最后一块——还没合并。
- **`AppContext` 的运行态 API 全是死代码**：`mark_started` / `mark_stopped` / `request_stop` / `reset_stop` / `stop_event` / `is_running`（`context.py:73-96`）在 `src/`、`main.py`、`tests/` 中**零调用方**（grep 已确认）。每个 service 自己持 `_stop_event`，context 这层 API 等于 vestigial。要么删掉，要么真正接管所有 service 的 stop 协议。
- `core/__init__.py` 重新导出了 `AppContext`，但 `AppContext` 本质属于 application-glue 层而非 core abstractions，分类有歧义。

## 2. Code Quality — 7.5

**优点**
- `pyproject.toml` 的 ruff 规则（E/F/I/UP/B）全过；`from __future__ import annotations` 在每个文件，类型注解相当完整。
- 日志统一走 `logging.getLogger(__name__)`，`setup_logging` 已在 `main.py:configure_logging` 中接好（兑现了 P1 修复）。
- `_construct_with_supported_kwargs`（main.py:317）使用 `dataclasses.fields` 过滤 kwargs，并且**不再做 SimpleNamespace 兜底**（兑现 P0 修复）；构造失败会抛 `TypeError`，符合"快速失败"原则。
- `FishingConfig.entry_templates` 使用元组而非 list，frozen dataclass 防止在运行期被改动。

**待改**
- **`src/util/cv_util.py`（107 行）、`src/util/hwnd_util.py`（245 行）、`src/util/resource_util.py`（73 行）零引用**——`grep "from src\.util\.\(cv_util\|hwnd_util\|resource_util\)"` 全无命中。`recognition_service` 自己用 `np.fromfile + cv2.imdecode` 复刻了 `imread_unicode`，逻辑重复。建议要么删除，要么让 `recognition_service` / `capture_service` 改用这些 util。
- **`FishingConfig` 仍残留 7 个未消费字段**：`tpl_entry_prompt` / `tpl_start_button` / `tpl_click_blank` / `tpl_judge_fishing` / `tpl_yellow_marker` / `tpl_fish_confirm` / `reel_timeout`（`models.py:84-90, 75`）——上轮 P1 "FishingConfig synonym cleanup" 只清掉了一部分，这批仍在。会让人误以为它们影响行为。
- **`config.yaml` 中多个 key 未被读取**：`fishing.control.max_session_minutes`（line 49）、`fishing.control.max_consecutive_failures`（line 50）、`fishing.debug.save_frames`（line 54）、`fishing.debug.frame_dir`（line 55）。`grep` 确认 `src/`、`main.py` 均不消费——配置写了等于谎言。
- `quest_core.py:191` `key.upper() if isinstance(key, str) and len(key) == 1 else key`——多余转换：`_vk` 内部已 `key.upper()`。
- `Win32WindowService.refresh()`（`window_service.py:83-88`）覆盖 `self._hwnd` 时未给出"窗口消失了"的 warning，仅 debug 级。
- `PrintWindowCaptureService._capture_window` 在 `if old_obj:` 处对 `PyCBitmap` 真值判断不严谨（GDI 句柄非 0 即真，写法上更应为 `if old_obj is not None`）。
- 大量 `except Exception:` 捕获——可接受但每处都应明确 logger.exception，目前 capture_service 有几处只 `logger.warning`。

## 3. Security & Anti-Cheat — 8.0

**优点**
- 控制层完全走 `PostMessage`（`control_service.py:95/100/130/132`），不调用 `SendInput` / `mouse_event` / `keybd_event`，鼠标键盘事件不进入全局输入队列，对反作弊检测更友好。
- 截屏使用 `PrintWindow + PW_RENDERFULLCONTENT`（`capture_service.py:16, 72`），不需要前景化，DPI 自适应；BitBlt 仅作 fallback。
- 鼠标点击带随机抖动（`fishing_core._click_with_jitter`），按键 jitter 默认 20-80ms（`config.yaml:123`），确实偏向"非定时机器人"特征。
- `release_all` 在 stop / 状态切换 / 异常路径都被调用（`fishing_core.py:164/285/299/308/324`、`fishing_service.py:62/101`），按键卡住的风险低。

**待改 / 风险**
- **🟥 严重：humanize bypass for fishing pulse 实际未生效。** `FishingStateMachine._apply_pulse`（`fishing_core.py:373`）调用 `self.control.tap_key(decision.key, seconds=decision.seconds)`，**未传 `humanize=False`**；`PostMessageControlService.tap_key` 默认 `humanize=True`，导致每次 5–40 ms 的脉冲叠加 20–80 ms jitter。结果 5 ms 脉冲变成 25–85 ms，整段反馈控制被"打糊"。整个 codebase grep 无任何 `humanize=False`：

  ```
  $ grep -rn "humanize=False" src/ main.py
  (no matches)
  ```

  这条上轮被列为已修复的 P1，**实际未兑现**——是本轮最值得马上处理的 bug。
- `bring_to_front` / `activate` 调用 `SetForegroundWindow` 但未配 `AttachThreadInput` trick，Windows 锁焦时可能静默失败；属于已知限制，不算严重。
- PostMessage 投递的鼠标 lparam 未 hi-test 客户区有效性，越界点击会被服务端正常忽略，但日志层无 warning。

## 4. Completeness — 6.5

**功能模块**
- ✅ 剧情跳过（`QuestAutomation`）、AI 钓鱼（`FishingStateMachine`）核心逻辑均功能完整且接通 UI。
- ✅ Win32 三件套（窗口 / 控制 / 截屏）实现完整。
- ✅ `LazyTaskService` 在游戏窗口未连接时 graceful 拒绝启动并 log warn（兑现上轮 main.py DI 修复）。
- ⚠️ `OCRService` / `RapidOCRService` 文档已自标 "Experimental / WIP"（兑现 P2），但 quest 中仍有"调查 F""手 F"等模板未来会需要 OCR 兜底——目前无消费方。

**测试覆盖**
- 仅 **8 个测试**：`test_fishing_models`（4 条数据类断言）、`test_geometry`（4 条几何断言）、`test_recognition`（3 条 OpenCV 断言）。
- **没有任何测试覆盖**：
  - `decide_pulse`（一个明确为方便单测而提取的纯函数，目前 0 测试 ← 最浪费）
  - `FishingStateMachine.tick` 各分支（success / escape / detect None / pulse coalesce）
  - `QuestAutomation.tick` 各 action（click / key / center_click / wait）
  - `PageRuleEngine.find_first / find_best`
  - `FishingBarDetector.detect`（fake recognition 即可写）
- 只测了 6 个 enum name 和几个 dataclass 字段，覆盖深度不达"圆环"项目对核心状态机的最低期望。

**配置消费**
- `max_session_minutes`、`max_consecutive_failures`、`debug.save_frames`、`debug.frame_dir`、`stop_hotkey` 五个 key 都在 yaml 里**没有消费方**——要么实现，要么删除并加 CHANGELOG。
- `ui.theme` / `ui.language` 仅作为 QLabel 显示文本（`main_window.py:115-116`），未真正驱动主题切换或 i18n。

**日志**
- `setup_logging` 已正确接入 `configure_logging`，写入 `local/logs/nte-assistant.log`（rotating, 2 MB × 3）。颜色仅在 TTY 时启用，文件中干净。日志覆盖各服务关键路径，不错。

## 5. Extensibility — 8.0

**优点**
- 新增一种识别后端：实现 `RecognitionService` ABC → 在 `create_service_chain` 替换；切换 OpenCV → ONNX 不动 core。
- 新增一条剧情规则：在 `config.yaml.quest.templates` 加一项即可，`_build_quest_rules` 自动转 `PageRule`。
- 新增一种钓鱼阶段：在 `FishingState` 加 enum + 在 `_enter_state` / `tick` 加分支即可，所有 timer 走 `_PhaseTimers`。
- `PostMessageControlService` 与 `PrintWindowCaptureService` 通过 `WindowService` 注入，单元测试可以替成 fake hwnd。

**待改**
- `LazyTaskService` 的 `__getattr__` 透传虽然便利，但破坏了静态类型检查，IDE 跳转受阻。
- `QuestRuntimeConfig` 与 `QuestConfig` 并存，未来想给 quest 加 `actions: tuple[TemplateAction, ...]` 字段时会同步两份。
- 新增"全局热键"功能时无现成插槽，因为 `AppContext` 的 stop_event 还没 wire；当下需要先填 context 这一层。

---

## 6. 仍存在的问题清单

按严重度排序（🟥 = 必须修；🟧 = 应当修；🟨 = 整理性优化）：

1. 🟥 **`fishing_core._apply_pulse` 未传 `humanize=False`**（`fishing_core.py:373`）。脉冲被 20–80 ms jitter 拉糊，跟杆响应严重劣化。修复一行：`self.control.tap_key(decision.key, seconds=decision.seconds, humanize=False)`，并在 ABC 中把 `humanize` 提升为正式参数（默认 True，子类一致）。
2. 🟧 **`QuestRuntimeConfig` 与 `QuestConfig` 双 dataclass 重复**。建议删 `main.py:QuestRuntimeConfig`，直接在 `_construct_with_supported_kwargs(QuestConfig, ...)` 中构造；`QuestAutomation` 已正确 type-hint `QuestConfig`。
3. 🟧 **`AppContext` 的运行态 API 死代码**（`mark_started`/`mark_stopped`/`request_stop`/`reset_stop`/`stop_event`/`is_running`）。要么删除，要么让 `LazyTaskService` / `FishingService` 真正使用它，避免"看起来有协调机制实际没有"。
4. 🟧 **3 个 util 模块全死**：`cv_util.py`（107 LoC）、`hwnd_util.py`（245 LoC）、`resource_util.py`（73 LoC），共约 425 LoC 无引用。建议删除或让 `recognition_service`/`capture_service`/`window_service` 重构为复用它们（消除 `imread_unicode` / `find_game_window` / `get_client_rect` 的重复实现）。
5. 🟧 **`FishingConfig` 7 个未消费字段**：`tpl_entry_prompt` / `tpl_start_button` / `tpl_click_blank` / `tpl_judge_fishing` / `tpl_yellow_marker` / `tpl_fish_confirm` / `reel_timeout`。直接删除。
6. 🟧 **`config.yaml` 5 个未消费 key**：`fishing.control.max_session_minutes`、`max_consecutive_failures`、`fishing.debug.save_frames`、`frame_dir`、`input.stop_hotkey`（注释 TODO 的也应有占位 issue）。要么实现，要么从 yaml 删掉。
7. 🟨 **测试覆盖严重不足**：`decide_pulse`、`FishingStateMachine.tick`、`QuestAutomation.tick`、`PageRuleEngine` 完全无测。建议优先补 `decide_pulse`（5 分钟即可写 6 条参数化测试）和 `PageRuleEngine.find_first`（fake recognition）。
8. 🟨 **`quest_core._execute` 中 `key.upper()` 多余**——`_vk` 已经 upper。删除即可，少一处歧义。
9. 🟨 **`PrintWindowCaptureService._capture_window` 错误处理**：`if old_obj:` → `if old_obj is not None:`；PrintWindow 失败 fallback 到 BitBlt 时仍可能拿到全黑帧，建议加一次 "frame is all zero?" sanity check 并 log warning。
10. 🟨 **`Win32WindowService.refresh()`** 日志只到 debug；连接丢失应至少 info 级，方便用户排查。
11. 🟨 **`ActionType` 中 "skip" / "wait"** 在 `DEFAULT_PAGE_RULES` 与 `config.yaml` 都没规则使用；`TemplateAction` dataclass 整个未实例化。是 dead literal/dataclass，但保留作 future API 也可——最少在 docstring 标注。
12. 🟨 `core/__init__.py` 把 `AppContext` 当成 core 概念导出；`AppContext` 实际是 application glue，建议从 `src/app/` 这种新包导出。

---

## 7. Delta Assessment（与上一轮对比）

**真实兑现的修复 ✅**
- P0 `fish_count` reset：`FishingService.fish_count` 直接读 `machine.stats.success_count`，`stop()` 不会清零（只有 `start(reset_stats=True)` 才清）— ✓
- P0 `SimpleNamespace` 兜底移除：`_construct_with_supported_kwargs` 现在直接用 `dataclasses.fields` 过滤后构造，失败抛 `TypeError` — ✓
- P0 `QuestState/ActionType` 去重：枚举只在 `quest/models.py` 一处定义；`page_rules.py` 与 `quest_core.py` 都从该处 import — ✓
- P0 `FishingState` 14→6 枚举瘦身：`models.py:12-25` 确认仅 6 个状态（IDLE/SEARCH_ENTRY/CASTING/FOLLOW_BAR/COMPLETE/ERROR），与 state machine 实际 transition 完全对齐 — ✓
- P1 `setup_logging` wired：`main.py:175-182` 调用 `setup_logging(level, log_file)` — ✓
- P1 `setCentralWidget` dedup：`main_window.py` 仅在 `__init__` 调用一次 — ✓
- P1 platform guard：`setup_dpi_awareness` (`main.py:153-162`) `if sys.platform != "win32": return` — ✓
- P1 quest wait stop-responsive：`quest_core._execute` 的 wait 分支用 `while time.monotonic() < deadline` + `if self._stop: return` — ✓
- P1 `inter_pulse_sleep` passthrough：`main.py:269` 从 control_cfg 读取并传入 `FishingConfig`，`fishing_core._apply_pulse` 用其 coalesce — ✓
- P2 OCR 标注 experimental：`ocr_service.py:38-42` 有 .. note:: — ✓
- P2 ruff 0 errors：`ruff check .` 全过 — ✓

**未兑现的修复 ❌**
- 🟥 **P1 "humanize bypass for fishing pulse" 未实际生效**——见上文 §3 / §6.1。代码中无任何 `humanize=False`。

**新发现的问题（上轮未列）**
- `QuestConfig` vs `QuestRuntimeConfig` 仍并存（虽然 P0 已合并 enum/literal，但 dataclass 没合）。
- `AppContext` 运行态 API 是孤儿。
- `cv_util` / `hwnd_util` / `resource_util` 三个 util 模块实质无引用。
- `FishingConfig` 仍有 7 个未引用字段（P2 synonym cleanup 没扫干净）。
- yaml 5 个未消费 key。

---

## 8. Overall Score & Justification

**综合分：7.5 / 10**（较上轮 8.0 略降）

**为什么降而不升**：本轮多数已声明的修复是真实落地的，工程基线（ruff / pytest / 类型 / 日志 / DI）确实改善；但有两条扣分理由：

1. 上轮被列为"已修复 P1"的 humanize bypass 在代码里压根没写——这是评测最忌的"声称兑现实未兑现"，必须扣 0.5。
2. 二轮评估的"放大镜效应"暴露了三类此前未发现的结构性整洁问题（双 dataclass、孤儿 context API、3 个死 util、7 个死 config 字段、5 个死 yaml key），合计大约 500+ LoC 的"假代码"，对 onboarding 与维护成本是真实负担——再扣 0.5。

**亮点（撑住 7.5 而非更低）**：
- 架构分层与 ABC 设计扎实；新增 service / rule 的扩展路径明确。
- 反作弊取向正确（PostMessage + PrintWindow + jitter + release_all 全路径）。
- ruff / pytest / 类型 / logging 工程化基线齐备，dev experience 良好。
- main.py 的 LazyTaskService + 工厂注入是这一轮最优雅的设计改进。

**到 8.5+ 的关键三步**：
1. **修 humanize bypass**（一行加 `humanize=False`，并在 ABC 加正式参数）。
2. **删/合 dead code**：QuestRuntimeConfig 合入 QuestConfig；AppContext 死 API 删除或真正接管 stop 协议；3 个 util 模块和 7 个 FishingConfig 字段、5 个 yaml key 二选一（实现 or 删除）。
3. **核心状态机补测**：`decide_pulse` 参数化 6 条 + `FishingStateMachine.tick` 用 fake services 写 4 条 + `QuestAutomation.tick`/`PageRuleEngine` 写 4 条；从当前 8 条扩到 ~25 条，状态机回归保护就立住了。

做完这三步，9 分可期。
