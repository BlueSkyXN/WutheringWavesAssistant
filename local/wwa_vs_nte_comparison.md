# WWA vs NTE-ai 技术对比报告

> 对比对象
> - **WWA（WutheringWavesAssistant）** — 鸣潮自动化助手（v3.2.1 Alpha，AGPL-3.0）
> 路径：`/Volumes/TP4000PRO/GitHub/WutheringWavesAssistant`
> - **NTE-ai** — "异环薄荷 AI" 自动化工具
> 路径：`/Volumes/TP4000PRO/GitHub/NTE-ai`
>
> 数据来源：`local/wwa_analysis.md`、`local/nte_analysis.md`，以及两个仓库的源码、`pyproject.toml` / `requirements.txt`、`.github/workflows/`、`docs/`、`tests/`。

---

## 1. 技术栈对比

| 维度 | WWA | NTE-ai |
|---|---|---|
| **Python 版本** | `>=3.10,<3.13`（CI 用便携 Python 3.12.6） | `>=3.9`（CI 用 3.10） |
| **依赖管理** | Poetry 2.x + lock，`pyproject.toml` 多源（PyPI/清华/阿里/NVIDIA/paddle/onnxruntime） | 仅 `requirements.txt`，无 lock，无 pyproject |
| **GUI 框架** | PySide6 ≥ 6.8 + `pyside6-fluent-widgets` 1.7.6（Qt for Python，Fluent 风格） | PyQt5 ≥ 5.15（深色霓虹自绘样式） |
| **图像识别** | OpenCV 模板匹配 + ColorChecker 像素颜色判定 + **YOLO ONNX**（自训 BOSS/奖励模型） | OpenCV 模板匹配（`TM_CCOEFF_NORMED`，0.5 缩放）+ HSV 颜色检测，无深度学习 |
| **OCR** | **RapidOCR 3.5（默认）+ PaddleOCR 3.3（可选）**，运行期通过 DI 自动切换 | 无 OCR |
| **推理引擎** | `onnxruntime` 1.20，4 个 extras：CPU / DirectML / CUDA 11.8 / 12.6 / 12.9 | 无 |
| **截图方案** | `win32 PrintWindow(PW_RENDERFULLCONTENT)`（默认 BG 后台）+ `mss`（FG 前台）+ `dxcam`（工具脚本） | `PIL.ImageGrab` + `pyautogui.screenshot`（旧）+ `windows-capture`（WGC，新版钓鱼） |
| **输入模拟** | `win32gui.PostMessage`（WM_KEYDOWN/WM_LBUTTONDOWN 等） | `pyautogui` + `pydirectinput`（DirectInput 风格） |
| **配置/校验** | Pydantic v2 + omegaconf + `config.yaml` + GUI JSON 参数 | 散落的 Python 常量（`config.py` 部分） |
| **辅助** | `psutil`、`pycaw`、`gputil`、`colorlog`、`dependency-injector` | `pynput`（F12 热键）、`pygetwindow`、`pywin32` |
| **打包/分发** | **不用 PyInstaller**：便携 Python + Poetry 离线安装 + `7z` 整目录打包，按 4 个 GPU/CPU extras 分别发布；外加预编译 `WWA.exe` 启动器 | **不出 exe**：CI 仅把 `*.py` + 资源打 zip 发 release；本地兼容 PyInstaller (`sys._MEIPASS`) 但仓库无 spec |

**小结**：WWA 是工业级技术栈（深度学习 + GPU + DI + 多源 + 多变体打包），NTE-ai 是轻量个人工具栈（脚本 + 模板匹配 + zip 分发）。

---

## 2. 架构设计对比

### 2.1 分层与目录组织

**WWA**（`docs/ARCH.md` 明确四层架构）：
```
GUI (PySide6) → Controller (multiprocessing) → Service (DI) → Core/Util
```
- `src/core/interface.py`（485 行）定义 14 个 ABC 抽象服务（`WindowService` / `ImgService` / `ODService` / `OCRService` / `ControlService` 等）。
- `src/core/injector.py` 用 `dependency_injector` 装配单例 Container；OCR 引擎在容器装配时**运行期探测**（`try import paddleocr`），实现可插拔。
- 任务（`AutoBoss / AutoPickup / AutoStory / DailyActivity / EchoMerge / SoarToTheBeat`）以独立 `multiprocessing.Process` 跑，`TaskMonitor` 线程做存活检测和异常重启。
- 16 个角色每人一个 `BaseResonator` 子类（`src/core/combat/resonator/*.py`），通过 `combat_system.resonator_map` 注册；战斗循环是显式 `while + threading.Event`。

**NTE-ai**（扁平脚本式）：
```
ui.py (大 GUI + 进程管理 + 业务调度) → automation_thread.py / fishing.py / controlfishing_v2.py
```
- 全部 14 个 Python 文件放在仓库根目录，无包结构。
- `ui.py` 是最大单文件，承担窗口、Tab、日志、子进程管理、窗口枚举、兑换码硬编码等。
- 设计模式仅有 Qt 信号槽 + 单槽 `Queue(maxsize=1)`（实时控制丢旧帧）+ 资源路径适配函数。

### 2.2 抽象与可替换性

| 项 | WWA | NTE-ai |
|---|---|---|
| ABC 抽象 | ✅ 14 个服务接口 | ❌ 无 |
| DI 容器 | ✅ `dependency_injector` 单例装配 | ❌ 直接 import |
| 可插拔识别后端 | ✅ OCR（RapidOCR↔PaddleOCR）、截图（PrintWindow↔MSS↔DXcam）、ONNX 后端（CPU/DML/CUDA） | ❌ 控制器有 v1/v2 双实现但其他全硬编码 |
| 任务进程隔离 | ✅ multiprocessing + IPC Queue | ⚠ 仅开发态用子进程，frozen 态用线程（行为不一致） |
| 状态/上下文 | ✅ Pydantic `Context` + `BossTaskContext` + `TaskSpec` | ❌ 散落全局变量（`global_stop`、`fish_count`、env var `FISHING_TARGET_HWND`） |

### 2.3 模块化程度
- **WWA**：分层清晰，但部分 service 仍是单文件巨型类（`auto_boss_service.py` 1636 行、`page_event_service.py` 2856 行、`pages.py` 1332 行、`combat_core.py` 804 行）。
- **NTE-ai**：文件少（~14 个）、入门快，但 `ui.py` 承担过多职责，ROI 常量在 5 个文件重复定义。

**小结**：WWA 是企业级"接口先行 + DI 装配"的架构，NTE-ai 是个人工具的"脚本 + 大 UI"扁平架构。

---

## 3. 反作弊与风控对比

### 3.1 与游戏的交互方式

| 交互方式 | WWA | NTE-ai |
|---|---|---|
| 内存读写 | ❌ 无 | ❌ 无 |
| DLL 注入 | ❌ 无 | ❌ 无 |
| DirectX/驱动 hook | ❌ 无 | ❌ 无 |
| 截图 | `PrintWindow(PW_RENDERFULLCONTENT)` **后台截图**，可在窗口被遮挡时取内容 | `ImageGrab` 全屏 + WGC（新版钓鱼） |
| 输入路径 | `win32gui.PostMessage(WM_KEYDOWN/WM_LBUTTONDOWN/WM_CHAR)` — **后台/最小化也可发送** | `pyautogui.click/press` + `pydirectinput.press/keyDown` — **必须前台、模拟硬件层** |
| 进程管理 | `OpenProcess(PROCESS_TERMINATE)` + `TerminateProcess`（崩溃自动重启） | 仅 `psutil`/`win32gui` 枚举 |

**关键差异**：WWA 是**真正的"后台脚本"**（PostMessage 路径），游戏可被遮挡甚至最小化；NTE-ai 是**前台脚本**，必须把游戏窗口放到最前才能接收输入。

### 3.2 拟人化措施

| 拟人化项 | WWA | NTE-ai |
|---|---|---|
| 按键时间抖动 | `np.random.uniform(0, 0.01)` 给每次按下加 0~10ms 抖动；`__sleep` 在 `seconds<0` 时取 40~60ms 随机 | 钓鱼控制器脉冲 5~40ms；剧情按键固定 `ACTION_DELAY=0.01` |
| 鼠标坐标抖动 | 战斗中无；`fight_click` 在窗口坐标点固定 | `random_click(pos, offset=10)` 给 ±10 像素随机 |
| 动作顺序随机 | `GenericCombo` 用 `random.shuffle` 打乱兜底连招 | ❌ |
| 鼠标曲线/贝塞尔 | ❌ 无 | ❌ 无 |
| 真实节奏建模 | ❌ 无 | ❌ 无 |
| 速率限制/疲劳/休息 | `MaxFightTime / MaxIdleTime / autoRestartPeriod`（运维向，非反检测） | ❌ 无（成功 1s/失败 3s 重试，固定循环） |

### 3.3 检测规避与安全性

| 维度 | WWA | NTE-ai |
|---|---|---|
| 反 EAC/BattlEye/自有 AC | ❌ 无主动对抗 | ❌ 无 |
| 焦点/前台校验 | 不需要（PostMessage 后台） | ❌ 缺少；输入到错误窗口的风险存在 |
| 异常停机条件 | `TaskMonitor` 检测崩溃自动重启 | 仅 UI 停止 / F12 / 进程结束 |
| 长时连续运行特征 | 显著（专为长时挂机设计） | 显著（无疲劳模型） |
| 主要风险来源 | PostMessage 模式被识别（可能性低于 SendInput） | `pyautogui`/`pydirectinput` 行为模式可被检测；固定 `ACTION_DELAY=0.01` 远快于真人 |

### 3.4 安全性评级（仅相对评估，不构成"安全"承诺）

| 项 | WWA | NTE-ai |
|---|---|---|
| 侵入性 | ⭐⭐⭐⭐⭐（极低，纯外部消息） | ⭐⭐⭐⭐（低，前台模拟） |
| 拟人化 | ⭐⭐（仅 ms 级抖动） | ⭐⭐（坐标 ±10px、脉冲随机） |
| 抗检测主动对抗 | ⭐（无） | ⭐（无） |
| 工程级风控（停机/限速） | ⭐⭐⭐（运维级监控） | ⭐（基本缺失） |
| **综合风控成熟度** | **6/10** | **3/10** |

**结论**：两者都是"靠不碰内存被动避险"，但 WWA 的 PostMessage 后台路径在隐蔽性上明显优于 NTE-ai 的前台 `pyautogui` 路径，且具备崩溃自重启等运维健壮性。

---

## 4. 可移植性对比

### 4.1 跨平台支持

| 平台 | WWA | NTE-ai |
|---|---|---|
| Windows | ✅ 唯一支持 | ✅ 唯一支持 |
| macOS | ❌（`interface.py` 留 `# class NSWindowServiceImpl: pass` 占位） | ❌ |
| Linux | ❌ | ❌ |
| 关键 Win32 绑定点 | `hwnd_util / screenshot_util / keymouse_util / winreg_util / pycaw / pywin32 / dxcam` | `ctypes.windll.user32/dwmapi`、`win32gui`、`windows-capture`、`pydirectinput` |

WWA 因为有 ABC 接口层，**理论上**重写 util + 提供 macOS 实现可移植，但工程量巨大；NTE-ai 没有抽象层，移植等于重写。

### 4.2 适配新游戏的难度

| 项 | WWA | NTE-ai |
|---|---|---|
| 游戏窗口识别 | 类名 `UnrealWindow` + 标题白名单（写死在 `hwnd_util.py`） | 标题关键字"异环"（5 处硬编码） |
| 视觉识别资产 | YOLO 模型 + OCR + 大量像素颜色坐标 | 50+ PNG 模板 |
| 适配新游戏成本 | **极高** — 需重训 YOLO、改全部 ColorChecker 坐标、写新角色类、改窗口标识、可能改 OCR 词典 | **中** — 替换模板、改窗口标题、改 ROI、改控制算法 |
| 是否有"游戏抽象层" | ❌ 业务和鸣潮强耦合（角色枚举、协奏属性、BOSS 列表都写在代码里） | ❌ 业务和异环强耦合 |

### 4.3 分辨率适配

| 项 | WWA | NTE-ai |
|---|---|---|
| 基准分辨率 | 1280×720 | 1920×1080 |
| 缩放机制 | `Scaler / DynamicPointTransformer / get_ratio()`（按 1280px 自动缩放） | 0.5 固定缩放模板，无 ROI 自适应 |
| 多比例支持 | 16:9 OK；21:9 偏移 | 严格 1920×1080 |
| DPI 感知 | `SetProcessDpiAwareness(PER_MONITOR)` | Qt 高 DPI 开了，识别层未适配 |

**小结**：两者都是单游戏专用工具；WWA 在分辨率适配上更成熟，但 NTE-ai 改个新游戏的边际成本反而更低（毕竟没那么多硬编码资产要重做）。

---

## 5. 易用性与易开发性

### 5.1 开发者上手难度

| 项 | WWA | NTE-ai |
|---|---|---|
| 入门曲线 | 陡峭 — 需理解 DI、Pydantic、ABC、multiprocessing、Qt signal | 平缓 — 14 个文件、过程式代码 |
| 添加新功能成本 | 写 Service Impl + 注册 Container + 改 Controller + 加 GUI Tab | 直接加 `*.py` + 在 `ui.py` 加按钮 |
| 添加新角色（WWA 专属） | 文档化（`docs/CONTRIBUTING_COMBO.md`），3 步：枚举 → 实现 `BaseResonator` → 注册 `combat_system.py`；每角色 200~300 行 | N/A |
| 添加新剧情自动化（NTE 专属） | N/A | 加 `images/*.png` + 改 `config.TEMPLATES_CONFIG` 一行；近乎零代码 |

### 5.2 文档质量

| 文档 | WWA | NTE-ai |
|---|---|---|
| README | ✅ 详细，含使用说明 / 提示项 | ✅ 简短 |
| 架构文档 | ✅ `docs/ARCH.md` 明确分层 | ❌ |
| 贡献指南 | ✅ `docs/CONTRIBUTING_COMBO.md` 教如何写新角色连招 | ❌ |
| Changelog | ✅ `CHANGELOG.md` 维护，CI 自动抽取写入 release body | ❌ 无 |
| 内联注释 | 中文为主、密度中 | 中英混用、密度低 |

### 5.3 配置管理

| 项 | WWA | NTE-ai |
|---|---|---|
| 配置文件 | `config.yaml`（用户）+ Pydantic 模型 + GUI JSON | `config.py` 部分 + 5+ 处硬编码 |
| 配置驱动度 | 高 — 游戏路径/BOSS 列表/连招 DSL/按键映射/阈值都在 yaml | 低 — 仅模板表，钓鱼 ROI/兑换码/QQ 群号/窗口标题硬编码 |
| 用户可改连招 | ✅ `FightTactics` 字符串 DSL + `KeyboardMappingConfig` 按键映射 | ❌ |
| 配置热加载 | ❌（重启任务生效） | ❌ |

**小结**：WWA 对**最终用户**易用（GUI + 配置 + 文档全），对**开发者**陡峭（需懂企业级框架）；NTE-ai 反过来——对**开发者**极易上手（脚本风格），对**用户**不够友好（很多东西硬编码）。

---

## 6. 测试与质量保证

| 项 | WWA | NTE-ai |
|---|---|---|
| 测试目录 | ✅ `tests/`，~4200 行（util / core / service / config 子目录） | ❌ 无 |
| 测试框架 | pytest + conftest + `.env` 加载 | 无 |
| 测试性质 | 多为**实机半集成测试**（需游戏开着） | 无 |
| 覆盖率报告 | ❌ | ❌ |
| Mock 框架 | ❌ | ❌ |
| CI 跑测试 | ❌（CI 只验证"装得上、打得出包"） | ❌（CI 只打 zip） |
| 类型检查 | mypy 配置存在（`ignore_missing_imports`，排除 tests）；现代类型注解（PEP 604） | 无类型注解 |
| Lint/Format | `.pre-commit-config.yaml` 本地存在但 CI 不强制 | 无 |
| 标准 logging | ✅ `logging_config.setup_logging` + `colorlog` | ❌ 大量 `print` |
| 日志分级 | ✅ DEBUG/INFO/WARN/ERROR | ❌ |
| 错误处理风格 | 自定义 `StopError` + try/finally 释放按键 | 散落 try/except，部分 bare `except:` 吞异常 |

### CI/CD

| 项 | WWA | NTE-ai |
|---|---|---|
| CI 平台 | GitHub Actions (windows-latest) | GitHub Actions (ubuntu-latest) |
| 工作流 | `release.yml`（4 变体打包 + 自动写 release body）+ `alpha.yml`（artifact）+ `sync_to_cnb.yml`（国内镜像） | `build.yml`（tag → zip → `gh release create`） |
| 构建产物 | 4 个 7z（cpu/cu118/cu126/cu129），cu129 因体积超限分卷 | 1 个 zip（源码 + 资源） |
| 产物可执行性 | ✅ 解压即用（含便携 Python） | ❌ 需用户自备 Python 环境 |

**小结**：WWA 测试虽以实机半集成为主、CI 不跑，但至少**有**；NTE-ai 完全无测试体系。两者 CI 都不验证逻辑，仅验证打包。

---

## 7. 综合评估矩阵（1-10 分）

| 维度 | WWA | NTE-ai | 备注 |
|---|---:|---:|---|
| 技术栈先进性 | **9** | 4 | WWA 用 ONNX/CUDA/DML、双 OCR、Pydantic v2、DI；NTE 仅 OpenCV+pyautogui |
| 架构清晰度 | **8** | 4 | WWA 四层 + ABC + DI；NTE 扁平脚本，UI 高耦合 |
| 模块化与可替换性 | **8** | 3 | WWA 14 个接口可换实现；NTE 仅控制器 v1/v2 双版本 |
| 反作弊隐蔽性 | **7** | 5 | WWA PostMessage 后台优于 NTE 前台 pyautogui |
| 拟人化程度 | 3 | 3 | 都仅基础随机，无鼠标曲线/真实节奏 |
| 风控/运维健壮性 | **8** | 3 | WWA 有 TaskMonitor/崩溃重启/UE4 弹窗处理 |
| 跨平台 | 2 | 1 | 都仅 Windows，WWA 有占位接口 |
| 适配新游戏成本 | 3 | **5** | WWA 资产太多反而更难迁；NTE 轻量易换 |
| 用户易用性 | **8** | 6 | WWA 有 Fluent GUI + 配置 + 文档；NTE 有 Tab GUI 但配置硬编码 |
| 开发者上手难度（越易越高分） | 5 | **8** | NTE 几个文件就能改；WWA 需懂企业级框架 |
| 配置驱动度 | **8** | 4 | WWA 大量 yaml/JSON；NTE 多处硬编码 |
| 文档质量 | **8** | 3 | WWA 有 ARCH/CONTRIBUTING/CHANGELOG；NTE 仅 README |
| 测试覆盖 | 5 | 1 | WWA 4200 行实机测试但 CI 不跑；NTE 完全无 |
| CI/CD 成熟度 | **8** | 4 | WWA 4 变体 + 便携 Python；NTE 仅 zip |
| 打包/分发 | **9** | 3 | WWA 解压即用；NTE 需用户自备环境 |
| 日志/可观测性 | **7** | 3 | WWA 标准 logging+colorlog；NTE 全靠 print |
| 战斗/自动化系统设计 | **9** | 5 | WWA 16 角色独立类 + 帧内决策；NTE 状态机用 if/while |
| **加权总分** | **6.8 / 10** | **3.9 / 10** | — |

---

## 8. 结论与建议

### 8.1 总体定位

| | WWA | NTE-ai |
|---|---|---|
| **项目定位** | 工业级游戏自动化平台，面向长期维护与社区贡献 | 个人/小团队工具，快速迭代实验性质 |
| **代码量级** | 数万行 + 4200 行测试 | < 5000 行核心代码 |
| **目标用户** | 普通玩家（有 GUI、有便携包、有文档） | 偏开发者用户（需要自己跑 Python） |
| **典型用例** | 长时挂机刷 BOSS / 声骸 / 日常 / 主线（多任务并发） | 剧情跳过 + 钓鱼跟随（单任务） |

### 8.2 WWA 可向 NTE-ai 借鉴

1. **最小可行配置表（`TEMPLATES_CONFIG`）思路**：NTE-ai 用 `(模板文件名, 动作, 参数)` 三元组的策略表驱动剧情跳过——这种轻量"模板即配置"非常适合 WWA 用来重写部分页面识别（目前 `pages.py` 1332 行硬编码）。
2. **WGC 实时调试器**：NTE-ai 的 `roi_debugger.py` 用 `windows-capture` 实时叠加 ROI/HSV/FPS——WWA 调试 ColorChecker 坐标时也能用类似工具替代手工 print。
3. **HSV 颜色检测互补**：WWA 全靠 BGR 容差，对动态光照不鲁棒；可在部分场景引入 HSV 范围匹配作为补充。
4. **轻量启动门槛**：NTE-ai 的"脚本即程序"对临时贡献者友好，WWA 的 DI/Pydantic 框架对小贡献者门槛偏高。

### 8.3 NTE-ai 可向 WWA 借鉴

1. **接口抽象层（ABC + DI）**：定义 `Detector / ActionExecutor / Task / WindowProvider`，把 `pyautogui`/`pydirectinput`/模板匹配/HSV 全部封装；同时支持后续接入 OCR/YOLO。
2. **PostMessage 后台输入**：从 `pyautogui`/`pydirectinput`（前台）切到 `win32gui.PostMessage`（后台）能显著降低对用户体验的影响（不抢焦点）和被识别的特征。WWA 的 `keymouse_util.py` 是现成参考。
3. **PrintWindow 后台截图**：替换 `ImageGrab` 全屏抓取为 `PrintWindow(PW_RENDERFULLCONTENT)`，减少全屏抓取被安全产品观察的特征。
4. **TaskMonitor 模式**：增加游戏崩溃检测、UE4 弹窗自动处理、异常自重启、最大运行时长等运维级风控。
5. **Pydantic 配置 + YAML**：把 ROI、阈值、窗口关键字、兑换码、QQ 群号、模板路径全部移入 `config.yaml`，支持多分辨率 profile。
6. **结构化日志**：用 `logging` 替代 `print`，分级 + 文件落盘 + 模块级 logger。
7. **测试体系**：哪怕只是引入"模板离线测试集"——给定 `screenshots/*.png`，断言 detector 输出——也能极大提升迭代信心。
8. **CI 真打 exe**：用 windows runner + PyInstaller 出可执行文件，比让用户装 Python 友好得多。
9. **Changelog 自动化**：维护 `CHANGELOG.md`，CI 自动抽取最新版块写入 release body。

### 8.4 各自的核心优势

**WWA 的不可替代优势**：
- **后台脚本（PostMessage + PrintWindow）** — 用户可以一边挂机一边干别的；
- **GPU 加速的 ONNX YOLO + OCR** — 对复杂识别场景的鲁棒性远高于纯模板匹配；
- **多任务进程隔离 + IPC + 监控自重启** — 真正能 7×24 跑的"挂机平台"；
- **16 个角色的独立战斗类 + 帧内决策** — 这种"配置即代码"的连招表达力是字符串 DSL 望尘莫及的；
- **便携 Python 一键解压** — 普通用户体验远超"需要装 Python"。

**NTE-ai 的不可替代优势**：
- **极低入门门槛** — 看几小时源码就能改；新增剧情跳过模板只要拖个 PNG + 配一行；
- **WGC + DWM extended frame bounds** — 客户区精确裁剪比 `GetWindowRect` 更适合 WGC 场景，这是 WWA 也没做的；
- **实时 ROI 调试器** — 调参体验比 WWA 的"改代码 + 跑测试 + 看 print" 流畅；
- **轻量足以应付简单玩法** — 钓鱼/剧情跳过这类 "模板 + 短脉冲" 场景，没必要上 DI 容器和 ONNX。

### 8.5 一句话总结

> **WWA 是"长期维护的工业级自动化平台"，NTE-ai 是"快速迭代的个人工具"**——前者在架构、隐蔽性、运维健壮性、识别能力上全面领先；后者在轻量、易上手、调试友好上仍有自己的位置。两者最值得相互借鉴的方向：**WWA 学 NTE 的"配置表 + 实时调试器"降低贡献者门槛；NTE 学 WWA 的"后台输入 + 接口抽象 + 配置化 + 测试集"提升工程成熟度**。
