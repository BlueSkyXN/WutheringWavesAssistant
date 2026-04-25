# NTE-Assistant 第二轮复评报告（Round 2 Re-evaluation）

评估对象：`/Volumes/TP4000PRO/GitHub/NTE-Assistant`  
输出位置：`/Volumes/TP4000PRO/GitHub/WutheringWavesAssistant/local/reeval_gpt55.md`  
评估范围：已阅读 `src/` 下全部 Python 文件、`main.py`、`config.yaml`、`tests/`、`pyproject.toml`，并额外抽查 README / docs / CHANGELOG 的一致性。  
基线验证：

```text
python3 -m pytest tests/ -q --tb=short
........ [100%]
8 passed

ruff check .
All checks passed!
```

辅助检查：已 grep `TODO/FIXME/WIP/pass/NotImplemented/SimpleNamespace/ServiceContainer/RuntimeService/loguru/pydantic/max_consecutive_failures/save_frames/stop_hotkey` 等模式，并用 AST 扫描重复 class/function 定义；无重复 class，重复 function 主要为接口实现、UI `append_log` 和工具层窗口函数重复。

---

## 1. 维度评分

| 维度 | 分数 | 评价 |
|---|---:|---|
| Architecture | **7.8 / 10** | `core/service/ui` 分层清楚，`WindowService` / `ControlService` / `CaptureService` / `RecognitionService` ABC 方向正确，状态机与线程外壳分离明显优于早期版本。但 `TaskService` 没有贯穿主装配链，`QuestRuntimeConfig` 与 `QuestConfig` 双轨并存，`LazyTaskService` 仍靠 `Any/getattr` 胶水粘合，架构纸面比真实运行链路更干净。 |
| Code Quality | **7.1 / 10** | ruff 0 errors、类型标注较完整、异常日志比第一轮成熟；但仍有较多 dead code / duplicated concepts，`_construct_with_supported_kwargs` 行为与 docstring 相反，若干命名与状态不一致，UI/service 状态可能漂移。 |
| Security & Anti-Cheat | **6.3 / 10** | 传统安全面没有明显高危：`yaml.safe_load`、模板 `np.fromfile + cv2.imdecode`、GDI finally 清理总体可接受。但游戏自动化天然高风险：`PostMessage` + `PrintWindow` 是低门槛可检测模式；窗口选择仍以标题子串为主，缺少进程/签名校验；缺少全局急停与明确封号/ToS 风险声明。 |
| Completeness | **6.2 / 10** | 主链路已从占位走向真实 Win32 + OpenCV + 状态机闭环，pytest/ruff 全绿。但测试仅 8 条，状态机/规则引擎/线程服务/PostMessage 0 覆盖；`max_session_minutes`、`max_consecutive_failures`、`save_frames`、`stop_hotkey` 等配置没有代码消费者；OCR 仍是 experimental / WIP。 |
| Extensibility | **7.3 / 10** | ABC 边界利于替换 capture/control/recognition；`PageRule` 配置化也方便扩展剧情规则。但当前只有单一实现，多个抽象未真正落地；dead util/geometry/OCR 模块制造“可扩展”的假象；并发共享服务未加锁，扩展为多任务后风险上升。 |

**Overall Score：7.0 / 10**

这个分数略高于上一轮 GPT-5.5 的 7.0 持平、低于上一轮 Opus 的 8.0。理由是：Round 2 的 lint、DI、状态机、模型清理确实提升明显，但从更高标准看，仍存在一个实际功能 bug、若干配置失效、并发风险、测试覆盖不足和文档漂移。项目已从“能看”进入“能跑原型”，但距离可长期稳定运行还有一轮可靠性工程。

---

## 2. Architecture 评估

### 优点

1. **依赖方向基本正确**  
   `src/core/interface.py` 定义抽象和核心数据类，`src/service/*` 实现 Win32/OpenCV，`src/ui/*` 只消费 service facade。核心层没有直接 import win32 / Qt，这是一个重要进步。

2. **状态机与线程外壳分离**  
   `FishingStateMachine.tick()`、`QuestAutomation.tick()` 是单步推进，`FishingService._run()`、`ThreadedQuestService._run()` 负责线程和 sleep。这比长循环塞在 core 里更可测试、可替换。

3. **视觉识别与业务逻辑分离**  
   `FishingBarDetector` 只依赖 `RecognitionService`；`PageRuleEngine` 只依赖 `RecognitionService` 和 `PageRule`。理论上可替换 OpenCV / OCR / WGC 捕获。

### 主要问题

1. **`TaskService` ABC 没有真正贯穿**  
   `src/core/interface.py` 定义了 `TaskService`，但只有 `FishingService` 继承。`main.py` 中真正给 UI 的 `LazyTaskService`、`ThreadedQuestService` 都未继承，仍靠 `hasattr/getattr` 鸭子类型。结果是架构上有“统一任务接口”，运行链路却没有强制执行。

2. **Quest 配置双轨**  
   `src/core/quest/models.py` 有 `QuestConfig`，`main.py` 又定义 `QuestRuntimeConfig`，实际传给 `QuestAutomation(config: QuestConfig)` 的是后者。字段当前碰巧满足运行需要，但类型注解不真实，后续新增字段容易出现 silent mismatch。

3. **`AppContext` 的 run-state API 是死代码**  
   `_stop_event/_running/_state_lock/mark_started/mark_stopped/request_stop/reset_stop/is_running` 当前无生产调用。它显示曾尝试做全局运行态，但现在服务各自维护线程状态，形成未清理的架构残留。

4. **坐标系没有类型化约束**  
   `Point`/`Rect` 注释称 client-area coordinates，但 `WindowService.get_client_rect_on_screen()` 返回 screen coords，`QuestAutomation._window_center()` 把 screen coords 直接传给 `ControlService.click()`，导致实际 bug。建议引入 `ClientPoint` / `ScreenPoint` 或至少在方法名和测试中固化契约。

---

## 3. Code Quality 评估

### 已改善项

- ruff 全绿，`E/F/I/UP/B` 都通过。
- 多数文件启用 `from __future__ import annotations`。
- `setup_logging()` 已接入主入口，日志落盘和 console handler 可用。
- `FishingState` 已清理为 6 个实际可达状态。
- `SimpleNamespace` fallback 已移除，真实 service chain 已在 `main.py` 装配。

### 剩余质量问题

#### 3.1 `_construct_with_supported_kwargs` 静默吞字段

`main.py:317-327` docstring 写的是“让 config field mismatches 在启动时暴露”，但实现会过滤掉 dataclass 不认识的 kwargs：

```python
valid_fields = {f.name for f in dataclasses.fields(cls)}
filtered = {k: v for k, v in kwargs.items() if k in valid_fields}
return cls(**filtered)
```

这会让配置 typo 静默失效。例如未来新增或误写 `pulse_min_ns`、`max_consecutive_failures`，不会报错也不会 warning。对用户可观测性很差。

#### 3.2 Dead code / duplicated concepts 仍然不少

较明确的 dead code / 未接入项：

- `src/core/geometry.py`：生产代码几乎无引用，`Rect.scale_from` 已覆盖核心缩放需求。
- `src/util/cv_util.py`：功能与 `OpenCVRecognitionService` 重叠，无生产引用。
- `src/util/hwnd_util.py`：功能与 `Win32WindowService` 重叠，无生产引用。
- `src/util/resource_util.py`：`main.py` 使用自己的 `_resolve_app_path()`，未使用该模块。
- `src/service/ocr_service.py`：自标 Experimental / WIP，无 main/src 调用方。
- `src/core/context.py` run-state API：无调用方。
- `QuestState.WAITING` / `QuestState.STOPPED`：当前自动机不会赋值。
- `TemplateAction`：无真实调用方。
- `QuestAutomation.run()`：线程驱动走 `ThreadedQuestService._run()`，该 blocking loop 无调用方。
- `FishingConfig.tpl_entry_prompt/tpl_start_button/tpl_click_blank/tpl_judge_fishing/tpl_yellow_marker/tpl_fish_confirm`：与 `entry_templates/cast_confirm_templates/yellow_template_name` 重叠。
- `FishingConfig.reel_timeout`：未读取。

这些不是立即崩溃的问题，但会显著拉低维护效率：贡献者无法判断哪份工具函数、哪套配置类、哪组模板字段才是“真入口”。

#### 3.3 UI 状态和 service 状态可能漂移

`QuestTab` / `FishingTab` 自己维护 `is_running` bool。若 service 启动失败、线程异常退出、窗口失联，UI 仍可能显示 running。`LazyTaskService.start()` 在窗口未连接时只设置 `status='未连接'` 并 return，但 tab 仍会把 `self.is_running = True`，这是一个实际 UX bug。

#### 3.4 `humanize_ms` 与精确脉冲冲突

`input.humanize_ms` 默认 `[20, 80] ms`，在 `PostMessageControlService._sleep()` 中加到所有 `tap_key` 的按住时长上。`decide_pulse()` 计算出的 5-40ms A/D pulse 会变成 25-120ms，这会破坏钓鱼 FOLLOW_BAR 的小步控制。Round 2 提到“humanize bypass for fishing pulse”，但当前代码仍调用 `self.control.tap_key(decision.key, seconds=decision.seconds)`，没有传 `humanize=False`；接口 ABC 甚至没有该参数。这一点仍未真正闭环。

---

## 4. Security & Anti-Cheat 评估

### 传统安全

- `yaml.safe_load()` 使用正确，无反序列化高危。
- 模板读取使用 `np.fromfile + cv2.imdecode`，是图像解码，不执行内容。
- 未发现 secrets、shell 注入、eval、pickle 等明显危险模式。

### 游戏自动化与反作弊风险

1. **PostMessage 可检测性高**  
   `src/service/control_service.py` 使用 `WM_KEYDOWN/WM_KEYUP/WM_LBUTTONDOWN/WM_LBUTTONUP`。这类 background input 对部分游戏有效，但也容易被反作弊或游戏自身输入栈识别为非真实输入。项目 README/文档应明确“可能违反 ToS / 可能封号 / 自行承担风险”。

2. **PrintWindow 可检测/兼容性有限**  
   `src/service/capture_service.py` 使用 `PrintWindow`，失败后 `BitBlt` fallback。对 DX/Vulkan/受保护窗口可能黑屏或返回旧帧。安全角度不是漏洞，但可靠性和反作弊兼容性一般。

3. **窗口定位可被同名窗口劫持**  
   `Win32WindowService` 主要按 `title_keyword in title` + optional class name 筛选。`config.yaml` 默认 `class_name: ""`，即默认不校验 class。任何标题包含“异环”的窗口都有机会被选中。建议至少默认使用 `UnrealWindow` 或进程名 / exe path 校验。

4. **缺少全局急停**  
   `config.yaml` 仍只有 `stop_hotkey` TODO。对自动化工具而言，急停是安全功能，不只是 UX。当前 UI 停止按钮依赖 Qt 可操作；若窗口、线程、输入卡住，用户缺少外部 emergency stop。

---

## 5. Completeness 评估

### 已完成闭环

- `main.py` 已能装配 window/control/capture/recognition。
- Fishing：`FishingService` + `FishingStateMachine` + `FishingBarDetector` + `OpenCVRecognitionService` 主链路完整。
- Quest：`ThreadedQuestService` + `QuestAutomation` + `PageRuleEngine` 主链路完整。
- UI：主窗口、剧情 tab、钓鱼 tab、悬浮日志基本可用。
- 日志：`setup_logging` 已真正调用，文件日志可落盘。

### 未完成 / 名实不符

1. **配置字段未消费**
   - `fishing.control.max_session_minutes`：未读取。
   - `fishing.control.max_consecutive_failures`：未读取；`FishingService._run()` ERROR 后无限重启。
   - `fishing.debug.save_frames` / `frame_dir`：未读取；UI 的 ROI toggle 只是本地 bool 和日志。
   - `input.stop_hotkey`：TODO，未实现。
   - `logging.max_lines_ui` 已消费，`ui.floating_log_max_lines` 已消费。

2. **OCR 仍是 WIP**  
   `RapidOCRService` 在 docstring 明确未接入。`pyproject.toml` 暴露 `ocr` extra，但安装 extra 后主流程不会使用 OCR。

3. **文档滞后明显**  
   README / docs / CHANGELOG 仍出现 `ServiceContainer`、`RuntimeService`、Loguru、Pydantic 等旧描述。真实代码已经改为 `AppServices`、`LazyTaskService`、`ThreadedQuestService`、stdlib logging、dataclasses。文档会误导新贡献者。

4. **测试覆盖不足**  
   当前只有 8 条测试：数据类、Rect、OpenCV 模板/HSV 基础路径。缺失：
   - `decide_pulse()` 边界测试。
   - `FishingStateMachine.tick()` 状态迁移测试。
   - `FishingService` ERROR/COMPLETE 自动重启与 stop 响应测试。
   - `PageRuleEngine.find_first/find_best` priority 和声明顺序测试。
   - `QuestAutomation.tick()` action 分支测试。
   - `PostMessageControlService` 的 `_vk`、`release_all`、humanize 行为测试。
   - `_construct_with_supported_kwargs` 配置 typo 测试。

---

## 6. Extensibility 评估

### 强项

- ABC 设计方向对：window / control / capture / recognition 可替换。
- `PageRule` 配置化，使新增剧情模板规则不必改 core。
- `FishingConfig` 参数化程度较高，ROI / HSV / thresholds / pulse 都可调。
- OpenCV service 已支持 template cache 和 scale 参数，后续扩 multi-scale 有基础。

### 弱项

1. **扩展点未被真实替换实现验证**  
   目前只有 Win32 PostMessage、PrintWindow、OpenCV 一套实现。架构说可替换，但缺少第二实现或 fake service 测试来证明边界稳定。

2. **共享 service 的并发扩展风险**  
   Fishing 与 Quest 两个线程共享同一个 `OpenCVRecognitionService` 和 `PostMessageControlService`。
   - `_template_cache: OrderedDict` 无锁。
   - `_pressed: set[int]` 无锁。
   当前可能低概率，但一旦增加更多任务或 OCR 线程，问题会放大。

3. **配置 schema 缺失**  
   目前是裸 dict + 手写转换，缺少 schema validation。Round 2 移除 Pydantic/死依赖是好事，但至少需要 dataclass validation 或显式 unknown key warning。

4. **工具模块重复削弱扩展性**  
   `hwnd_util.py` 与 `window_service.py`、`cv_util.py` 与 `recognition_service.py`、`resource_util.py` 与 `main._resolve_app_path()` 重叠。扩展时容易改错位置。

---

## 7. Remaining Issues（按优先级）

### P0 / 高优先级功能问题

1. **`center_click` 坐标系 bug**  
   文件：`src/core/quest/quest_core.py:211-221` + `src/service/control_service.py:108-132`  
   `_window_center()` 使用 `get_client_rect_on_screen()` 计算 screen coords，但 `PostMessageControlService.click()` 的 lParam 需要 client coords。窗口不在屏幕原点时，`不可跳过.png` 的 `center_click` 会点偏。应改为 `get_client_size()` 的 `(w//2, h//2)`，或显式 screen-to-client 转换。

2. **Fishing pulse 被 humanize 放大**  
   文件：`src/core/fishing/fishing_core.py:373`、`src/service/control_service.py:103-106`  
   5-40ms pulse 被默认 20-80ms jitter 放大为 25-120ms。应让 fishing bar 控制调用 `tap_key(..., humanize=False)`，并把该参数纳入 `ControlService` ABC。

### P1 / 可靠性和配置问题

3. **未知配置字段静默丢弃**  
   文件：`main.py:317-327`  
   应 fail-fast 或 warning。当前行为与 docstring 相反。

4. **`max_consecutive_failures` / `max_session_minutes` 未实现**  
   文件：`config.yaml:49-50`、`src/service/fishing_service.py:73-99`  
   ERROR 后无限自动重启，缺少熔断和会话上限。

5. **`PostMessageControlService._pressed` 无锁**  
   文件：`src/service/control_service.py:76,134-141`  
   quest/fishing 双线程共享时可能出现 release/tap 交错，极端情况下卡键或漏释放。

6. **`OpenCVRecognitionService._template_cache` 无锁**  
   文件：`src/service/recognition_service.py:19-36`  
   `OrderedDict` LRU 在多线程下没有保护。建议加 `threading.RLock` 或用 `functools.lru_cache`。

7. **UI running 状态与 service 状态可能不一致**  
   文件：`src/ui/tabs/fishing_tab.py`、`src/ui/tabs/quest_tab.py`、`main.py:45-62`  
   service 未启动成功时 tab 仍会设置 `is_running=True`。

8. **PageRule 同优先级排序与 docstring 不一致**  
   文件：`src/core/quest/page_rules.py:116-123`  
   文档说同 priority 按声明顺序，代码按 `(priority, template_path)` 排序，可能改变 yaml 声明顺序。

### P2 / 清理与维护问题

9. **大量 dead code / dead fields 需要删除或接入**  
   包括 `geometry.py`、`cv_util.py`、`hwnd_util.py`、`resource_util.py`、`ocr_service.py`、`TemplateAction`、`QuestState.WAITING/STOPPED`、`FishingConfig.tpl_*`、`reel_timeout`、`QuestAutomation.run()`、`AppContext` run-state API。

10. **文档与代码不一致**  
    README/docs/CHANGELOG 仍提旧 DI 容器和旧依赖，应同步，否则 round 2 修复成果在文档层不可见。

11. **UI 日志与 Python logging 双轨**  
    业务 `logger.info/exception` 不会进入 Qt log view / floating log。建议增加 `logging.Handler -> Qt Signal`。

12. **`PageRuleEngine.find_first()` 每帧重复 `Path.exists()` / 多次灰度化**  
    性能不是当前最大问题，但 scan_interval=50ms、13 条规则时浪费可见。可在 set_rules 预解析路径，或在 recognition 层支持 preloaded templates / gray frame。

13. **Win32 service 模块缺少非 Windows import guard**  
    `window_service.py`、`control_service.py`、`capture_service.py` 顶层直接 import pywin32。项目定位 Windows 可以接受，但在 macOS/Linux import 这些模块会失败。当前 main.py 延迟 import 避免测试失败，但包级可移植性仍弱。

---

## 8. Delta Assessment：相对 Round 1 的变化

### 明显改善

1. **关键占位被真实实现替换**  
   `RuntimeService` / `SimpleNamespace` 风格占位已不在主链路，Win32 window/control/capture + OpenCV recognition 已装配。

2. **状态模型更收敛**  
   Fishing 从死 enum 清理到 6 个核心状态；`QuestState/ActionType` 的重复有所减少。

3. **DI wiring 更完整**  
   `main.py` 能实际创建 AppContext 和 service chain，不再只是 UI mock。

4. **Lint 基线显著提升**  
   ruff 0 errors，import/style/bugbear 基线干净。

5. **日志基础设施接入**  
   `setup_logging` 已被 `configure_logging()` 调用，文件日志可用。

6. **钓鱼逻辑可测试性提高**  
   `decide_pulse()` 独立为纯函数，`FishingBarDetector` 与 state machine 分离。

### 仍然薄弱

1. **测试没有跟上架构演进**  
   8 条测试不足以覆盖 round 2 修过的核心问题，尤其是状态机、配置消费、线程停止、坐标系。

2. **配置完整度仍不足**  
   yaml 暴露了比代码更多的承诺字段，且未知字段静默吞掉。

3. **并发安全仍是盲点**  
   两个任务线程共享 control/recognition，但共享状态未加锁。

4. **文档债务扩大**  
   代码已进化，README/docs/CHANGELOG 仍停在旧架构术语，会降低可维护性。

5. **反作弊/合规说明缺失**  
   对游戏自动化项目，这是必须正视的非功能需求。

---

## 9. 建议的 Round 3 修复顺序

1. 修 `center_click` 坐标系，并加单测。
2. 为 `ControlService.tap_key` 增加 `humanize` 参数或拆出 `precise_tap_key`，钓鱼 pulse 禁用 humanize。
3. `_construct_with_supported_kwargs` 改为 unknown key warning / fail-fast。
4. 把 `max_consecutive_failures`、`max_session_minutes` 接入 `FishingConfig` 和 `FishingService._run()`。
5. 给 `_pressed` 和 `_template_cache` 加锁。
6. 修 UI tab 启动状态：service start 失败时不应置 running。
7. 补测试：`decide_pulse`、`FishingStateMachine`、`PageRuleEngine`、`QuestAutomation`、配置 typo、center_click。
8. 删除或接入 dead modules/fields。
9. 同步 README/docs/CHANGELOG，补充 ToS / anti-cheat 风险声明。
10. 增加 logging-to-Qt handler，让 UI 日志显示业务 logger。

---

## 10. 总结

Round 2 后，NTE-Assistant 的“基础工程形态”已经明显成型：分层清楚、真实 service chain 可装配、ruff/pytest 全绿、钓鱼/剧情主链路不再只是占位。若只按原型标准，可给到 7.5 左右。

但本轮是 second-round evaluation，期望应更高。现在最影响评分的不是 lint 或目录结构，而是：实际功能 bug（`center_click`）、配置承诺未兑现、状态机缺测试、共享服务无锁、文档和代码漂移、反作弊风险未声明。因此综合给 **7.0 / 10**：比第一轮 GPT-5.5 视角没有明显涨分，但质量内核更扎实；若 P0/P1 和测试补齐，有机会稳定进入 **8.0+**。
