# WutheringWavesAssistant (WWA) — 技术分析报告

> 分析对象：`/Volumes/TP4000PRO/GitHub/WutheringWavesAssistant`，版本 `3.2.1 Alpha`（`src/__init__.py`），上游 `wakening/WutheringWavesAssistant`，许可证 AGPL-3.0。
> 分析方法：直接阅读 `main.py`、`src/` 关键模块（core/service/util/controller/config）、`config.yaml`、`pyproject.toml`、`tests/` 与 `.github/workflows/`、`docs/`。

---

## 1. 技术栈与依赖

### 1.1 语言与运行时
- **Python**：`requires-python = ">=3.10,<3.13"`（`pyproject.toml`）。
- **包管理**：Poetry 2.x（`build-system: poetry-core>=2.0.0`），并显式声明 PyPI / 清华 / 阿里 / NVIDIA / paddle / onnxruntime 多源以适配国内网络。
- **平台**：Windows 专属。`hwnd_util.py` 大量调用 `win32gui/win32api/win32process/ctypes.windll`，`screenshot_util.py` 依赖 `win32ui` + `PrintWindow`。`README` 与 GitHub Actions 均以 windows-latest / Python 3.12.6 portable 运行。
- **管理员权限**：`application.before()` 强制要求 `windows_util.is_admin()`，否则弹通知并 `sys.exit(0)`。

### 1.2 核心依赖（`pyproject.toml` 主体）
| 类别 | 库 | 备注 |
|---|---|---|
| 数值/图像 | `numpy==1.26.4`, `opencv-python>=4.11`, `pillow` | 颜色匹配、模板匹配、缩放 |
| OCR | `rapidocr==3.5.0`（默认）；可选 `paddleocr==3.3.2` | 由 `injector.py` 在导入时探测 `paddleocr` 是否可用，存在则覆盖默认 |
| 推理引擎 | `onnxruntime==1.20.0`（CPU）/ `onnxruntime-directml`（DML）/ `onnxruntime-gpu`（CUDA 11.8/12.6/12.9） | 通过 Poetry extras 切换：`cpu`/`dml`/`cu118`/`cu126`/`cu129` |
| 目标检测 | YOLO ONNX 模型（`assets/model/boss/*.onnx`，`reward.onnx`） | `yolo_util.py` 直接用 `onnxruntime.InferenceSession` 推理，**不依赖 ultralytics** |
| GUI | `pyside6>=6.8`, `pyside6-fluent-widgets[full]==1.7.6` | Qt for Python，FluentUI 风格 |
| DI | `dependency-injector>=4.45` | `Container` 单例式装配整套 service |
| 截图 | `mss>=10`, `pywin32`（PrintWindow/BitBlt）；可选 `dxcam`（仅工具脚本） | 默认使用 win32 PrintWindow（后台截图） |
| 输入 | `pywin32`（`PostMessage`）、`pynput`、`pydirectinput` | 生产路径主要走 `win32gui.PostMessage`，pynput/pydirectinput 仅备用 |
| 配置/校验 | `pydantic`, `omegaconf` | `Context`/`ParamConfig`/`Config` 用 Pydantic v2 |
| 系统/音频 | `psutil>=7`, `pycaw==20240210`, `gputil`, `colorlog` | 进程发现、音量/通知、GPU 信息、彩色日志 |

### 1.3 打包与分发
- **不使用 PyInstaller / Nuitka**。`.github/workflows/release.yml` 与 `alpha.yml` 的方案：
  1. 下载 Python 3.12.6 amd64 zip；
  2. `pip install poetry==2.1.1`，`poetry config virtualenvs.create false`，`poetry install -E <variant> --no-root`；
  3. 把整个目录（含便携 Python、Mingit、依赖）`7z` 打包，按 `cpu / cu118 / cu126 / cu129` 四个 extras 各出一份；
  4. cu129 因体积超限被拆分成多卷上传；最后 `softprops/action-gh-release` 发布。
- 仓库根目录有 `WWA.exe`（启动器，345 KB，已编译二进制）和 `WWA一键更新.bat`（用户层更新脚本）。`main.py` 自身只是 `application.run()` 的轻包装。

---

## 2. 架构与代码组织

### 2.1 总体分层
四层架构（`docs/ARCH.md` 也明确说明）：

```
GUI (PySide6 + FluentWidgets, src/gui/**)
   │  signal/slot
Controller (src/controller/main_controller.py)
   │  ProcessTask / threading.Event / multiprocessing
Service (src/service/**)            ←—— 由 dependency_injector 装配
   │  调用 interface.py 中的抽象
Core (src/core/**)                  ←—— 业务模型、几何、页面、战斗、工作流
   │
Util (src/util/**)                  ←—— 纯工具：hwnd、键鼠、截图、OCR/YOLO 包装
```

- 入口：`main.py` → `environs.load_env()` → `logging_config.setup_logging()` → `application.run()`。
- `application.run()`：管理员检查 → 构造 `MainController` → 绑定 GUI 全局信号 → 启动 Qt (`src.gui.gui.wwa()`)。
- 任务以独立 `multiprocessing.Process` 跑（除录制/回放任务用 `threading`）。`MainController._run_task` 通过 `multiprocessing.Queue` 做 IPC（log_queue + event_queue），`TaskMonitor` 线程负责异常重启与游戏存活检测。

### 2.2 依赖注入容器（`src/core/injector.py`）
- 使用 `dependency_injector.containers.DeclarativeContainer`，所有 Service 都是 `providers.Singleton`。
- **延迟决策**：在类体里 `try import paddleocr`，若可用则 `ocr_engine_impl = PaddleOcrServiceImpl`，否则回退 `RapidOcrServiceImpl`。这是运行期可插拔 OCR 的关键。
- `context = providers.Dependency()` 占位，在 `Container.build(context)` 时通过 `container.context.override(providers.Object(context))` 注入。

### 2.3 接口抽象（`src/core/interface.py`，485 行）
非常完整的 ABC 抽象层，定义了 `WindowService / ImgService / ODService / OCRService / PageEventService / PageService / GlobalPageService / EchoMergeService / GameControlService / PlayerControlService / ExtendedControlService / ControlService / BossInfoService / CombatService`。

- `ControlService = GameControlService + PlayerControlService + ExtendedControlService + ABC`，并通过 `game()/player()/extended()` 提供视图分割（不改对象，仅用于 IDE 可见性收敛）。
- 每个 Impl（`Win32ControlServiceImpl`, `HwndServiceImpl`, `ImgServiceImpl`, `RapidOcrServiceImpl`, `YoloServiceImpl`, `CombatServiceImpl`）都有同名替身的可能，方便后续做 `NSWindowServiceImpl`（注释里已留位）。

### 2.4 配置管理
- **用户配置文件**：根目录 `config.yaml`（旧版自动战斗在用，由 `AppConfig` 解析）+ GUI 写入的 JSON 参数（`ParamConfig.snapshot/build`）。
- **Pydantic 模型**：`src/config/config.py` 的 `Config` 聚合 `AppConfig / EchoModel / KeyboardMappingConfig / ParamConfig` 四块。
- **运行期上下文**：`src/core/contexts.py` 的 `Context`（Pydantic）持有 `config`、`boss_task_ctx`（`BossTaskContext`，含战斗状态机字段如 `roleIndex/bossIndex/status/needHeal/echoIsLockQuantity` 等）、`spec`（`TaskSpec`）和私有 `_container` 引用。
- **按键映射**：`KeyboardMappingConfig.get_mapping_key(reset_key, src_key)` 在 `BaseControlService._get_mapping_key` 中统一调用，允许玩家自定义按键。

### 2.5 战斗系统抽象（核心亮点）
- `src/core/combat/combat_system.py`：`CombatSystem` 是顶层调度。
  - 在 `__init__` 内**实例化全部 16 个角色**，再用 `resonator_map: dict[ResonatorNameEnum, BaseResonator]` 做名字→实例映射；未注册的角色回退 `GenericResonator`。
  - `_sort_resonators`：按 `Support → DPS → Healer` 重排出场顺序，与 `config.yaml` 的 `FightOrder` 配合（注释里特别强调「奶妈起手」）。
  - `run(event)` 是战斗主循环（while True），每轮：
    1. `event.is_set()` 校验暂停；
    2. 每 5s 主动 `control_service.activate()` 维持窗口焦点消息；
    3. `team_member_selector.toggle(...)` 切人，按编队人数与切人成败做状态机；
    4. `resonator.combo()` 执行该角色定制连招，捕获 `StopError` 快速跳出；
    5. `finally` 释放 `mouse_left_up/right_up`，避免按键残留。
  - 暴露 `start(delay_seconds)`（异步以 daemon thread 跑）、`pause()`、`set_resonators(names_zh)`、`exit_special_state(scenario)`。

- `src/core/combat/combat_core.py`（804 行）：
  - `ResonatorNameEnum`：枚举内置角色中文名，覆盖 v1.0 ~ v3.x（包含尚未实装的 `lucy/rebecca/lucilla` 占位）；提供 `get_enum_by_ocr_text` 做 OCR 容错匹配（如 `chisa` 短名前缀匹配、`luukherssen` 首尾字符匹配）。
  - `ColorChecker`：用 `numpy` 做像素级 BGR 容差匹配（默认 ±30），支持 `LogicEnum.OR/AND` 多点逻辑、`AlignEnum` 对齐、`DynamicPointTransformer` 把 1280×720 基准点动态变换到当前分辨率。封装了 `concerto_*`（衍射/热熔/湮灭/冷凝/气动 5 种协奏能量颜色）静态工厂。
  - `BaseCombo.combo_action(sequence, end_wait, ignore_event)`：执行 `[key, press_time, wait_time]` 三元组列表，特殊键约定：
    - `a`=普攻（左键，按压必须 ≤0.2s）；`z`=重击（左键长按，必须 ≥0.3s）；`w`=空等待；`j`=跳跃（Space）；`d`=右键闪避；`F`=拾取（在 `auto_pickup=True` 时按 ≥0.25s 间隔自动点 F）。
    - 支持 `key_down/key_up` 后缀（`a_down/a_up/...`），并维护 `key_down_caches` 集合，触发 `StopError` 退出时**保证按下的键被释放**——这是防"按键卡死"的工程细节。
    - `end_wait=False` 时跳过最后一段后摇，用于「合轴」（一放就切人）。
  - `BaseResonator`：内置 BOSS 血条 5 档颜色检查器（`_health_01/20/30/50/100_*`，BGR 渐变）、`is_avatar_grey`（多点判断角色阵亡，1 容差三通道相近即灰）、`boss_is_immobilized`、`is_boss_health_bar_exist` 等通用检测；子类按角色实现 `combo()` 与具体技能就绪检测。

- `combat_cache` 装饰器：把不带 `self` 状态参数的连招片段缓存为类共享列表，避免重复构造。

### 2.6 角色实现（`src/core/combat/resonator/*.py`，16 个角色）
以 `changli.py`（长离）为典型样本：
- `BaseChangli` 在 `__init__` 里定义 7 个 `ColorChecker`：
  - 协奏能量（左下血条旁红圈，热熔色）
  - 4 格能量（`(547/595/649/692, 668)` 三点 OR 检测）
  - 共鸣技能 / 声骸技能 / 共鸣解放是否亮起（白色 255,255,255）
- `Changli.combo()` 是显式状态机：根据 `energy_count(img)` + 三个技能就绪状态走不同分支（4 离火走 z；3 离火 + E 就绪走 Ea；低离火有大走 Rz；兜底走 E 或 a3）。每个分支最后会**重新截图重新判断**，体现"事件驱动 + 帧内决策"风格。
- `GenericResonator.combo()`：按 a4 → 随机洗牌 [Eaa, R, z] → Q，作为未实现角色的兜底。

### 2.7 任务体系（`src/core/tasks.py`，720 行）
- `ProcessTask` 抽象基类，封装 `multiprocessing.Process` 的启动/停止/重启统计。
- 具体任务：`MouseResetProcessTask / AutoBossProcessTask / AutoPickupProcessTask / AutoStoryProcessTask / DailyActivityProcessTask / EchoMergeProcessTask / SoarToTheBeatMacroReplayTask / SoarToTheBeatMacroRecordTask`（在 `MainController.tasks` 字典里注册）。
- `TaskSpec`（`workflow.py`）是不可变启动参数：`run_id / leader_pid / gui_win_id / cli_args / platform / game_path / param_config / skip_is_open / ocr_use_gpu`。
- `IPCManager` 使用 `multiprocessing.Queue` 做日志和事件传递；GUI 通过 `globalSignal` 接收任务完成回调。

---

## 3. 反作弊与风险控制

> 简短结论：**纯外部辅助路径**，不读写游戏内存，不注入 DLL，不 hook DirectX。所有交互通过 Win32 窗口消息 + 屏幕截图完成。

### 3.1 与游戏的交互方式
- **截图**（只读）
  - 默认 `BG`（后台）模式：`screenshot_util.screenshot()` = `GetWindowDC` + `CreateCompatibleBitmap` + **`PrintWindow(hwnd, dc, 3)`**（flag=3 = `PW_RENDERFULLCONTENT`，可在窗口非前台/被遮挡时仍取到内容）。失败重试 1 次。
  - 备选 `FG`（前台）模式：`mss` 抓全屏区域；项目里也保留 `dxcam_util.py` 与 `screenshot_bitblt`，但生产路径默认走 PrintWindow。
  - `ImgService.set_capture_mode(BG/FG)` 由各 service 自行决定（`AutoBossServiceImpl.__init__` 里强制设为 `BG`）。
- **输入**（单向写）
  - `keymouse_util.py` 全部使用 `win32gui.PostMessage`：
    - 键盘：`WM_KEYDOWN/WM_KEYUP`（`tap_key/key_down/key_up`）
    - 鼠标：`WM_LBUTTONDOWN/UP`、`WM_RBUTTONDOWN/UP`、`WM_MBUTTONDOWN/UP`、`WM_MOUSEWHEEL`（`MAKELONG(x, y)` 编码窗口相对坐标）
    - 字符输入：`WM_CHAR`（一次一个字符 + 30 ms 延迟）
  - 这意味着游戏窗口可以在后台、被遮挡甚至最小化时仍接收消息——**不需要 SendInput / DirectInput / 模拟硬件层**。
  - `pynput` / `pydirectinput` 在 `pyproject.toml` 中存在，但代码里没看到关键路径使用，可能用于 `macro_record_util.py` 录制等次要场景。

### 3.2 窗口句柄管理（`src/util/hwnd_util.py`，428 行）
- 通过 **窗口类名 `UnrealWindow`** + **窗口标题 `["鸣潮  ", "Wuthering Waves  "]`** 用 `EnumWindows` 找句柄；多开时再用 `filter_hwnds(hwnds, filter_path)` 比对 `psutil.Process(pid).exe()` 路径定位指定实例。
- 还能识别多种附属窗口：官服登录（`#32770`）、B 服登录（`CLoginDlg_P_8340_\d{10}`）、UE4-Client 崩溃弹窗（`UE4-Client Game已崩溃，即将关闭`），后者会被 `force_close_process` 关掉。
- `enable_dpi_awareness()`：`SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)`，并通过 `Scaler`/`get_ratio()`（基准 1280px）把 1280×720 设计坐标动态映射到当前客户区。
- `force_close_process`：`OpenProcess(PROCESS_TERMINATE)` + `TerminateProcess(handle, -1)`，被 `TaskMonitor._restart_game / _close_game` 调用，实现「游戏崩溃自动重启」（`config.yaml: RestartWutheringWaves` 与 `autoRestartPeriod`）。

### 3.3 反检测/拟人化措施
- **实际存在的拟人化**仅限"小抖动"层面：
  - `Win32PlayerControlServiceImpl.fight_click/right_click/fight_tap`：`seconds = round(np.random.uniform(0, 0.01), 5)`，并用 `while ... == 0: pass` 强制非零，给每次按下加 0~10 ms 抖动。
  - `keymouse_util.__sleep`：当 `seconds < 0` 时改用 `random.uniform(0.04, 0.06)` 作为按下保持时间。
  - `GenericCombo.combo`：动作组之间 `random.shuffle` 改变释放顺序。
  - `combat_core.combat_cache` 装饰器**不会**重新随机——这意味着已被缓存的连招序列里的 `press_time/wait_time` 是常量。
- **不存在**的措施：未发现任何反 Easy AntiCheat / BattlEye / 鸣潮自有反作弊（KrCheck/Sentinel 之类）的对抗代码；没有内核驱动加载、没有 DLL 注入、没有 ETW 抑制、没有进程隐藏；游戏检测脚本工具的能力**完全依赖宿主防护**，即"靠 PostMessage 后台输入 + 不碰内存"这条朴素路径来降低被识别概率。
- 文档（`README`）里也提示用户关闭 HDR、关闭显卡滤镜、关闭 MSI 小飞机、游戏内开"镜头重置/移动镜头修正/战斗镜头修正"——属于规避截图错位、而非反作弊。
- 一个潜在风险点：`force_close_process` 直接调用 `TerminateProcess` 杀游戏，加上对登录窗口/崩溃弹窗的判断逻辑，行为上比较"敏感"；但它发生在自动重启流程里，对玩家透明。

### 3.4 多开/多游戏隔离
- `MainController` 在新进程中跑任务，避免 GUI 与战斗逻辑互相阻塞。
- `gui_is_exist()`：通过 `globalSignal` 检测同路径多开，提示「同一路径下只能启动一个实例」。
- `HwndServiceImpl` 在多游戏并存时，按 `param_config.gamePath` 强匹配执行路径选择句柄。

---

## 4. 战斗/自动化系统

### 4.1 连招的定义方式
- **DSL（受限）**：`config.yaml.FightTactics` 提供面向用户的连招描述串，例如 `"q~0.1,e~0.1,a"`、`"r,e,q~0.1,s,a(0.1),a"`。语义见 `config.yaml` 第 31 行注释：`e/q/r` 技能，`l` 后退闪避，`a` 普攻（默认连点 0.3s），`a~0.5` 普攻按下 0.5s，`a(0.5)` 连续普攻 0.5s，纯数字为间隔时间。这套字符串由旧版自动战斗（`AppConfig`）解析。
- **代码 DSL（主流路径）**：每角色文件在 `combat_core.BaseCombo.combo_action()` 接受 `[key, press_time, wait_time]` 列表。比如长离的 `Ea()` 返回 `[["E",0.05,0.30], ["a",0.05,0.30], ...]`。这种「配置即代码」相比纯字符串更易做条件分支与帧内决策，但**新增角色必须写 Python**，不是热加载配置。

### 4.2 状态检测机制
- 完全基于像素颜色（`ColorChecker`）：技能图标亮 = 接近 (255,255,255)，灰 = 偏暗，能量条按特定 BGR 颜色判定。
- BOSS 血条 5 档颜色采样（黄→红渐变）→ `boss_hp(img)` 返回 0.01/0.20/0.30/0.50/1.00 离散估值。
- 角色阵亡：右侧编队头像三通道差 ≤1 容差认为灰（`is_avatar_grey`）。
- 协奏能量：5 种属性各自的 BGR（如气动 `(168, 226, 87)`、湮灭 `(153, 77, 201)`）。
- 文字识别（`ocr_service`）+ 模板匹配（`ImgServiceImpl.match_template`，`cv2.matchTemplate` + 阈值缓存）+ YOLO 目标检测（声骸/奖励，`assets/model/boss/boss_v310.onnx` 等）三套互补识别。

### 4.3 状态机/事件驱动
- **战斗循环**是显式 while + 事件标志，不是 statemachine 库。`threading.Event` 充当"暂停/启动"信号，`StopError` 充当"立即跳出连招"快速通道。
- **页面驱动**：`src/service/page_event_service.py`（2856 行，未细读）+ `PageService`/`PageEventService` 抽象，外加 `Page / ConditionalAction / TextMatch / OcrResult` 等模型（`src/core/pages.py`，1332 行），呈现典型的"页面识别 → 触发 Action"模式：`AutoBossServiceImpl._build_boss_pages()` 等方法注册一组页面，主循环 OCR 当前画面 → 匹配页面 → 调用绑定的 `action(positions)`。这是除战斗外的"导航"实现核心。
- **任务级监控**：`TaskMonitor._run_restart` 每 ~10s 巡检：
  1. 检查 UE4 崩溃窗，存在则关掉；
  2. 按 `autoRestartPeriod` 定时关游戏；
  3. 用 `psutil`/`hwnd_util.get_hwnd` 看游戏是否存活，挂掉则 `subprocess.Popen(game_path, ...DETACHED_PROCESS)` 重启，最多等 300s；
  4. 任务进程挂了用 20s 冷却后 `process_task.restart()`。

---

## 5. 测试与质量

### 5.1 测试目录（`tests/`，~ 4200 行）
- 使用 `pytest`，`tests/conftest.py` 在 `pytest_configure` 中加载 `.env`、配置 logger。
- 子目录：
  - `tests/util/`：12 个文件覆盖 `hwnd / keymouse / screenshot / mss / rapidocr / paddleocr / yolo / img / file / audio / windows / winreg`。
  - `tests/core/`：`combat_core_test.py`、`combats_test.py`（1295 行，非常大）、`combats_record.py`（连招回放素材）。
  - `tests/service/`：`control_service_test.py`、`page_event_service_test.py`。
  - `tests/config/`：日志配置测试。
- **特征**：很多测试是「**实机半集成测试**」——例如 `keymouse_util_test.py` 直接 `hwnd_util.get_hwnd()` 取真实游戏窗口、对其 `tap_key/middle_click`，需要游戏开着才能跑。这些测试的目的更像是**人工调参 fixture**，不是 CI 用的纯单元测试。
- 没有测试覆盖率报告、没有 mock 框架、没有 pytest-xdist，没有性能基线。

### 5.2 CI/CD（`.github/workflows/`）
- `release.yml`（主）：手动触发 → 在 windows-latest 上构建 4 个 extras 变体（cpu/cu118/cu126/cu129）→ 7z 打包 → 自动写 `release_body.txt`（夹带固定使用说明 + `CHANGELOG.md` 抽取的最新版块）→ `softprops/action-gh-release` 发布到 `v${VERSION}` tag。
- `alpha.yml`：与 release 等价但**不发 Release**（注释掉了），仅产 artifact，用于测试构建。
- `sync_to_cnb.yml`：同步到 cnb（国内 git 镜像）。
- **CI 不跑测试**——pytest 在工作流里完全缺席，CI 只验证"装得上、打得出包"。

### 5.3 代码质量基础设施
- `pyproject.toml` 仅配置 `[tool.mypy] ignore_missing_imports = true; exclude = "tests/.*"`，没看到 ruff/black/isort/pre-commit 实际接入（`release.yml` 提到 `.pre-commit-config.yaml` 会被打包前删除，说明本地存在但未在 CI 强制）。
- 类型注解使用现代语法（`tuple[int, int]`, `str | None`, PEP 604 union），但混用 `Optional[...]` 风格；`interface.py` 用 ABC 强契约。
- 依赖了 `dependency-injector` 与 Pydantic，整体显得"企业风"但部分 service（如 `auto_boss_service.py` 1636 行、`page_event_service.py` 2856 行）仍是单文件巨型类，模块化粒度不均。

---

## 6. 可移植性与扩展性

### 6.1 平台移植性
- **强 Windows 绑定**：`hwnd_util / screenshot_util / keymouse_util / winreg_util / pycaw / pywin32 / dxcam` 全是 Windows-only。`interface.py` 留了 `# class NSWindowServiceImpl: pass` 的 macOS 占位但未实现。要移植到 Linux/macOS 需要重写整个 util 层与 control_service。

### 6.2 添加新角色
- 流程见 `docs/CONTRIBUTING_COMBO.md`：
  1. 在 `combat_core.ResonatorNameEnum` 添加枚举（中文名值）；
  2. 在 `src/core/combat/resonator/` 新建 `xxx.py`，继承 `BaseResonator` 实现 `resonator_name / char_class / energy_count / is_*_ready / combo`；
  3. 在 `combat_system.CombatSystem.__init__` 实例化并注册到 `resonator_map`。
- 工程化代价适中：每个角色 200~300 行，主要是**取色坐标 + 连招序列**。**未注册**的角色自动 fallback 到 `GenericResonator`，体验不致崩溃但也不智能。
- 没有插件加载机制（不会扫目录自动注册），新角色必须改 `combat_system.py` 三处。

### 6.3 配置驱动 vs 硬编码
- **配置驱动**：游戏路径、目标 BOSS 列表、战斗策略字符串、按键映射、各种阈值（`MaxFightTime / MaxIdleTime / SearchEchoes / EchoLock` 等）。
- **硬编码**：
  - 全部像素坐标都基于 1280×720 写死（`(513, 669)`、`(1195, 168)` 等），靠 `Scaler/DynamicPointTransformer` 在运行时缩放——理论上对其他分辨率透明，但**比例不是 16:9 的窗口（如 21:9 超宽）会偏移**。
  - 所有颜色阈值（容差 30/20/1）写死在类常量。
  - BOSS 名称、模型路径、模型版本（v10 / v310）都在 `yolo_util.py` 里硬编码 `Model` 列表。

### 6.4 模块化与可替换性
- 由于 `interface.py` 抽象齐全 + DI 容器，理论上可以替换 OCR 引擎（已演示 RapidOCR↔PaddleOCR）、替换截图实现（PrintWindow ↔ MSS ↔ DXcam）、替换控制后端（PostMessage ↔ DirectInput）。但实际只有 OCR 与截图模式有"可切换"封装，其它仍是直接用 Win32 实现。
- GUI 层（`src/gui/**`）与业务层通过 `globalSignal` 单向解耦，命令行模式下注释里写「无 gui 运行」可以走宽松模式句柄选择，但没看到完整 CLI 入口。

---

## 7. 关键观察与小结

| 方面 | 评价 |
|---|---|
| **架构清晰度** | 高——四层 + DI + ABC 抽象规范，便于阅读 |
| **战斗系统设计** | 高——颜色检测 + 帧内决策 + 16 角色独立类，工程上务实 |
| **反作弊对抗** | 低（按设计就是低）——纯 PostMessage + PrintWindow，对硬反作弊毫无主动对抗，靠"不碰内存"被动避免 |
| **拟人化程度** | 弱——只有 0~10 ms 抖动 + 偶发 random.shuffle，没有鼠标曲线/真实人类节奏建模 |
| **测试质量** | 偏弱——多为实机半集成测试，CI 不运行 |
| **打包方案** | 反常规——不用 PyInstaller，整目录便携 Python + Poetry，分 4 个 GPU/CPU 变体 7z 发布 |
| **跨平台** | 仅 Windows，且短期看不会扩展 |
| **新角色扩展** | 中等——需写 Python 类并改 `combat_system.py` 注册，没有插件机制；连招坐标基于 1280×720 |
| **运维健壮性** | 较高——`TaskMonitor` 有游戏崩溃检测、UE4 弹窗自动关闭、定时重启、任务冷却重启 |

### 与同类工具对比时建议关注的点
1. **是否走内核/驱动 vs 用户态 PostMessage**：WWA 是后者，安全、便携，但抗检测靠运气。
2. **是否真正"读取"游戏状态**：WWA 完全靠像素+OCR+YOLO，不读内存——逻辑稳定性受游戏 UI 改版影响极大（每次游戏更新可能要改坐标/颜色）。
3. **DSL vs 写死代码**：WWA 旧版有 `FightTactics` 字符串 DSL，新版已转向"Python 类即配置"，灵活性更高但学习成本更高。
4. **GPU 加速**：OCR 与 YOLO 都可走 ONNX-CUDA / DirectML，CPU 也能跑——同类工具大多只支持其一。
