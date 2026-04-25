# NTE 游戏自动化项目安全框架与架构提案

> 基于 `local/wwa_analysis.md` 与 `local/nte_analysis.md` 的综合设计。本文档的“安全”目标是：**低侵入、用户授权、可审计、可限速、可停机、可回滚**。本文不提供绕过反作弊、隐藏进程、规避内存扫描、DLL 注入检测规避、驱动/内核对抗、ETW 抑制等可操作方案；这些能力在本架构中被定义为红线并禁止实现。

---

## 0. 执行摘要

NTE-ai 当前的优势是低侵入：只做屏幕/窗口捕获、OpenCV 模板/HSV 识别、pyautogui/pydirectinput 输入，不读写内存、不注入、不 hook、不改包。但它仍处于“脚本式自动化”阶段：固定 ROI、固定循环、固定阈值、固定按键节奏、缺少统一窗口指纹、缺少安全停机、缺少日志脱敏与审计、业务层可直接调用输入库。相比之下，WWA 的成熟点在于四层架构、接口抽象、依赖注入、后台截图/后台输入封装、任务进程隔离、DPI/Scaler、页面/状态机模型和较完整的窗口句柄管理。

建议 NTE 新项目不要直接追求“更隐蔽”，而应建立 **Safety Runtime + Core Abstractions + Platform Adapters**：所有截图、输入、窗口、识别、任务调度都必须经过网关；所有危险对抗能力从架构层不存在；每个功能在发布前通过限流、停机、窗口归属、隐私日志与红线门禁。

---

## 1. 当前安全态势分析

### 1.1 NTE-ai 当前安全弱点和风险点

#### 1.1.1 架构弱点

| 维度 | 当前状态 | 风险 |
|---|---|---|
| 代码组织 | 根目录脚本式：`ui.py`、`automation_thread.py`、`fishing.py`、`controlfishing_v2.py` 等直接协作 | UI、任务、识别、输入耦合；难以做统一安全审计 |
| 输入抽象 | 剧情用 `pyautogui`，钓鱼用 `pydirectinput`，没有统一 `InputBackend` | 无全局限流、无强制前台校验、无统一 KillSwitch |
| 截图抽象 | `ImageGrab`、`pyautogui.screenshot`、WGC 混用 | 捕获来源、坐标系、失败回退分散，难以定位风险 |
| 窗口定位 | 标题关键字“异环”多处硬编码，部分使用 hwnd | 同名窗口、调试窗口、浮窗可能被误操作 |
| 状态机 | 钓鱼流程是 while/if；剧情跳过逐模板扫描 | 异常路径不可控；卡状态时可能持续输入 |
| 配置 | ROI、阈值、HSV、循环间隔分散 | 版本更新后静默失效；用户难以安全调参 |
| 日志 | `print`/UI 文本为主，无结构化脱敏 | 可能泄露窗口标题、路径、截图调试信息；难审计 |

#### 1.1.2 行为风险

- **确定性时序**：剧情跳过使用固定 `ACTION_DELAY=0.01`、`LOOP_INTERVAL=0.05`；钓鱼部分 F 键、点击、重试也存在固定节奏。
- **固定 ROI 和模板阈值**：旧版钓鱼固定 ROI `(597, 61, 1328, 85)`；新版虽使用 WGC，但绿色 HSV 和黄色模板阈值仍固定。
- **缺少会话治理**：没有单次运行时长、每日累计、失败次数、失焦时长、识别异常率等停机阈值。
- **缺少前台/目标校验**：现有流程多校验 hwnd 存在，但缺少“窗口仍属于目标 exe、窗口类名一致、前台策略符合输入 backend”的统一校验。
- **业务旁路 OS API**：任何业务模块都可直接导入 `pyautogui`/`pydirectinput`/`win32gui`，安全规则无法强制。

#### 1.1.3 隐私和供应链风险

- 全屏截图或 debug 截图若落盘，可能包含账号、聊天、好友、支付或个人信息。
- `pynput` 全局热键、`pyautogui` 全局输入、`windows-capture` 原生组件均应纳入依赖审计。
- 当前没有锁文件与哈希校验，依赖被动升级会带来不可重复构建风险。

### 1.2 WWA 中值得借鉴的安全实践

| WWA 实践 | 可借鉴价值 | NTE 迁移方式 |
|---|---|---|
| GUI → Controller → Service → Core → Util 分层 | 业务与 OS 能力分离 | 改为 GUI → Controller → Service → Core Abstractions → Platform Adapters |
| `src/core/interface.py` 的 ABC 抽象 | 统一 Window/Img/OCR/OD/Page/Control 契约 | 为 NTE 定义 `WindowGateway`、`CaptureGateway`、`InputGateway`、`VisionGateway` |
| `dependency-injector` 容器 | 运行期替换 OCR、截图、输入实现 | 按环境选择 WGC/PrintWindow/mss 和 PostMessage/SendInput |
| `multiprocessing.Process` 任务隔离 | GUI 不被业务卡死，便于强制停止 | 每个自动化任务独立进程，主控 watchdog 可终止 |
| hwnd + exe 路径匹配 | 多窗口/多开时降低误操作 | 目标窗口必须通过 pid、exe_path、class_name、title 四元指纹 |
| DPI awareness + Scaler | 消除固定 1280×720/1920×1080 坐标假设 | ROI 全部用基准坐标 + 动态映射 |
| PrintWindow 后台截图、mss 前台截图 | 提供截图后端抽象与回退 | NTE 主路径优先 WGC，兼容 PrintWindow/mss |
| `PostMessage` 封装 | 不影响真实鼠标，后台输入可控 | 作为后台输入候选；必须经过限流与窗口校验 |
| `finally` 释放按键 | 防止按键卡死 | 所有 `key_down` 必须由上下文管理器托管 |

需要注意：WWA 也并不存在对抗反作弊的高危能力；它的安全优势主要来自低侵入、工程抽象和较少触碰游戏进程。因此 NTE 应学习工程化，而不是学习“规避”。

### 1.3 游戏反作弊系统常见检测手段（高层风险视角）

以下仅用于风险建模，不提供绕过方法：

1. **进程与模块观察**：枚举进程、窗口、模块、加载库、签名、命令行、父子进程关系。
2. **内存完整性与调试痕迹**：检查进程内存、调试器、hook、异常处理链、代码段修改。
3. **输入行为分析**：统计输入事件频率、反应时间、按压时长、循环周期、异常后台输入。
4. **图形捕获/叠加观察**：观察持续捕获、overlay、窗口消息模式、DWM/WGC 相关行为。
5. **文件与网络完整性**：检查客户端文件、资源、shader、网络协议是否被修改或重放。
6. **运行环境关联**：虚拟机、驱动、注入器、调试工具、已知作弊工具特征。

本方案的原则是：**不触碰内存/注入/hook/驱动/网络/文件篡改等高危面；对输入和截图做最小必要使用，并让用户可见、可控、可审计。**

---

## 2. 安全框架设计

### 2.1 总体架构

```text
┌────────────────────────────────────────────────────────────┐
│ GUI Layer                                                   │
│  PySide6 MainWindow · Task Panel · Consent Dialog · Logs    │
│  Red KillSwitch Button · Visible Automation Overlay          │
└───────────────┬────────────────────────────────────────────┘
                │ Qt signal / IPC command
┌───────────────▼────────────────────────────────────────────┐
│ Controller Layer                                            │
│  TaskController · SessionController · SafetyController       │
│  starts/stops worker processes, owns global policy           │
└───────────────┬────────────────────────────────────────────┘
                │ multiprocessing Queue / Event
┌───────────────▼────────────────────────────────────────────┐
│ Service Layer                                               │
│  StoryService · FishingService · DailyTaskService            │
│  CombatAssistService · MiniGameService                       │
│  only calls Core Abstractions, never calls OS APIs directly   │
└───────────────┬────────────────────────────────────────────┘
                │ typed protocols
┌───────────────▼────────────────────────────────────────────┐
│ Core Abstractions                                           │
│  WindowGateway · CaptureGateway · InputGateway               │
│  VisionGateway · PageService · TaskStateMachine              │
└───────────────┬────────────────────────────────────────────┘
                │ mandatory gates
┌───────────────▼────────────────────────────────────────────┐
│ Safety Runtime (cross-cutting, cannot be disabled)           │
│  ConsentGate · ForegroundGuard · RateLimiter                 │
│  SessionBudget · Watchdog · KillSwitch · AuditLogger         │
└───────────────┬────────────────────────────────────────────┘
                │ only layer allowed to call native libraries
┌───────────────▼────────────────────────────────────────────┐
│ Platform Adapters                                           │
│  Win32WindowAdapter · WgcCaptureAdapter                      │
│  PrintWindowCaptureAdapter · MssCaptureAdapter               │
│  PostMessageInputAdapter · ForegroundSendInputAdapter        │
└────────────────────────────────────────────────────────────┘
```

核心规则：业务层不能直接导入 `pyautogui`、`pydirectinput`、`win32gui`、`ctypes.windll.user32`、`windows_capture`。这些只能出现在 `platform_adapters/` 与 `safety_runtime/`，并由 CI 静态检查强制。

### 2.2 窗口交互安全层：后台操作 vs 前台操作

#### 推荐策略

| 模式 | 适用场景 | 优点 | 风险 | NTE 建议 |
|---|---|---|---|---|
| 前台模式 | 自动战斗、需要真实焦点/鼠标锁定的场景 | 与用户可见行为一致，误判少 | 会抢占用户输入 | 默认推荐，需 overlay 提示与热键停机 |
| 后台模式 | 剧情确认、钓鱼条追踪、低频 UI 点击 | 不影响用户真实鼠标 | 后台消息可能被游戏忽略或被视为异常路径 | 仅对低频、可验证动作开放 |
| 混合模式 | WGC 后台识别 + 前台授权输入 | 捕获稳定，输入保守 | 状态切换复杂 | 作为 v0.1 主线，失败即停机 |

#### 窗口指纹

```python
@dataclass(frozen=True)
class WindowFingerprint:
    hwnd: int
    pid: int
    exe_path_hash: str
    class_name: str
    title_hash: str
    client_rect: Rect
    dpi_scale: float

class WindowGateway(Protocol):
    def discover(self) -> list[WindowFingerprint]: ...
    def bind(self, fp: WindowFingerprint) -> BoundWindow: ...
    def assert_target(self, window: BoundWindow) -> None: ...
    def is_foreground(self, window: BoundWindow) -> bool: ...
```

安全要求：
- 目标选择必须由用户确认，不能仅靠标题关键字自动绑定。
- 输入前校验 hwnd 仍有效、pid 未变化、exe 路径匹配、窗口尺寸未异常变化。
- 如果窗口失焦超过配置阈值（默认 3 秒），前台输入 backend 必须停机；后台 backend 进入降速或暂停。

### 2.3 输入模拟安全层：PostMessage / SendInput / DirectInput 取舍

| 输入方式 | 工程特点 | 安全风险 | 推荐用途 |
|---|---|---|---|
| PostMessage | 发送窗口消息，不移动真实鼠标；WWA 生产路径使用 | 某些游戏不接受；后台高频消息有行为特征 | 低频 UI 操作、剧情确认、菜单导航；必须限流 |
| SendInput | 系统级输入，接近真实键鼠事件 | 会影响前台；若无授权会造成输入劫持 | 仅前台、仅用户每次会话授权、仅必要场景 |
| DirectInput 类库（如 pydirectinput） | 对部分游戏兼容较好 | 仍是全局输入；高频固定脉冲风险高 | 钓鱼/战斗等需要游戏接收时的可选后端，默认关闭 |
| 驱动/虚拟 HID | 低层模拟 | 红线，高风险 | 禁止 |

#### `InputGateway` 设计

```python
class InputGateway(Protocol):
    def click(self, x: int, y: int, *, button: MouseButton = MouseButton.LEFT,
              reason: str, target: BoundWindow) -> InputDecision: ...
    def tap_key(self, key: Key, *, hold_ms: int | None = None,
                reason: str, target: BoundWindow) -> InputDecision: ...
    def key_hold(self, key: Key, hold_ms: int, *, reason: str,
                 target: BoundWindow) -> InputDecision: ...
    def release_all(self, target: BoundWindow) -> None: ...
```

每次输入必须经过：

```text
ConsentGate → WindowGateway.assert_target → ForegroundGuard
→ RateLimiter → SessionBudget → InputBackend → AuditLogger
```

建议默认值（需实测调整）：
- 单任务输入上限：≤ 8 events/s；全局 ≤ 12 events/s。
- 单分钟输入上限：≤ 240 events/min。
- 单次按键保持：普通 UI 30–80ms；长按必须显式声明 reason。
- 任意 `key_down` 必须使用上下文管理器，异常时 `finally release_all()`。

### 2.4 图像识别安全层：BitBlt / PrintWindow / DDA / WGC

| 截屏方式 | 特点 | 优点 | 局限/风险 | NTE 建议 |
|---|---|---|---|---|
| BitBlt | 传统 GDI 拷贝窗口/屏幕 DC | 简单、依赖少 | 遮挡/最小化/硬件加速窗口可能黑屏 | 仅作为诊断回退 |
| PrintWindow | WWA 默认后台截图，`PW_RENDERFULLCONTENT` | 后台窗口可用，适合 Win32/部分 DX | 对 DX12/Unreal 兼容不稳定 | 作为 WWA 可移植模块保留 |
| DDA / Desktop Duplication | DXGI 桌面复制 | 高帧率，全屏前台稳定 | 实现复杂，对窗口级 crop 需额外处理 | 暂不作为 v0.1 主路径 |
| WGC / Windows Graphics Capture | NTE-ai 新版钓鱼已使用，按 hwnd 捕获 | 窗口级捕获、对现代渲染兼容较好 | Win10 1903+；用户授权/系统策略差异 | NTE 主路径首选 |
| mss | 前台/屏幕区域抓取 | 简单稳定 | 需要窗口可见，受遮挡影响 | 前台模式兜底 |

#### `CaptureGateway` 设计

```python
class CaptureMode(StrEnum):
    WGC = "wgc"
    PRINT_WINDOW = "printwindow"
    MSS = "mss"
    BITBLT = "bitblt"

@dataclass(frozen=True)
class Frame:
    image: np.ndarray          # BGR/RGB 明确标注
    ts_monotonic: float
    source: CaptureMode
    window_fp_hash: str
    region: Rect | None

class CaptureGateway(Protocol):
    def grab(self, target: BoundWindow, region: Rect | None = None) -> Frame: ...
    def healthcheck(self, target: BoundWindow) -> CaptureHealth: ...
```

安全要求：
- 默认不落盘原始截图；调试截图必须用户显式开启，并自动打码/裁 ROI。
- ROI 坐标统一基于 1280×720 或 1920×1080 基准，通过 `Scaler` 映射。
- 连续 N 帧黑屏、尺寸变化、置信度过低时触发停机，而不是盲目继续输入。

### 2.5 时序安全层：随机延迟、拟人化节奏、行为模式治理

本方案只允许“工程抖动”和“安全限速”，不允许研究、拟合或对抗反作弊检测特征。

```python
@dataclass(frozen=True)
class TimingPolicy:
    min_action_gap_ms: tuple[int, int] = (80, 180)
    ui_click_hold_ms: tuple[int, int] = (35, 90)
    key_tap_hold_ms: tuple[int, int] = (30, 75)
    max_events_per_second: int = 8
    max_continuous_minutes: int = 90
    max_daily_minutes: int = 360
    recognition_failure_limit: int = 20
```

策略：
- 使用有界随机，而不是固定 10ms/50ms 循环。
- 引入任务级退避：识别失败 → 降频 → 暂停 → 停机。
- 引入疲劳/休息：连续运行到上限必须停止并要求用户重新确认。
- 对自动战斗等高频场景采用状态机驱动，只有状态变化才输入，不做无意义轮询连点。

### 2.6 进程隐藏层：红线与替代设计

用户要求中的“进程隐藏、进程名伪装、内存特征消除、DLL 注入检测规避”属于高风险对抗范畴。本项目**不设计、不实现、不文档化可操作方法**。安全替代方案如下：

| 请求能力 | 风险判定 | 替代安全设计 |
|---|---|---|
| 进程名伪装/隐藏 | 红线：恶意软件特征，可能违反平台规则 | 正常进程名、签名/版本信息透明、用户可审计 |
| 内存特征消除 | 红线：对抗扫描 | 不读写游戏内存，不进入游戏进程地址空间 |
| DLL 注入检测规避 | 红线：注入与规避均禁止 | 不注入 DLL，不 hook DirectX/OpenGL/WinAPI |
| 驱动/内核输入 | 红线：高危 | 用户态、前台授权、限流输入 |
| ETW/日志抑制 | 红线：取证对抗 | 保留本工具审计日志，用户可删除自己的本地日志 |

架构强制措施：
- `platform_adapters/` 不提供内存、注入、hook、驱动相关接口。
- CI 禁止出现 `ReadProcessMemory`、`WriteProcessMemory`、`CreateRemoteThread`、`SetWindowsHookEx`、`NtSetInformationThread`、`WinDivert` 等关键字，除非在红线文档中以禁止项出现。
- Code Review Checklist 要求任何新增 native API 都说明用途、调用层、授权方式和停机策略。

---

## 3. 可移植安全模块设计

### 3.1 可从 WWA 直接移植或改造的模块

| WWA 模块/思想 | 迁移级别 | 迁移说明 |
|---|---|---|
| `core/interface.py` 抽象方式 | 高 | 不直接复制全部接口，提炼 Window/Capture/Input/Vision/Page/Task |
| `dependency-injector` 容器 | 高 | 用于切换 WGC/PrintWindow/mss 与 PostMessage/SendInput |
| `hwnd_util` 的 hwnd、类名、标题、exe 路径匹配 | 高 | 改为 NTE 窗口指纹；窗口类名需实测 |
| DPI awareness + `Scaler` | 高 | 替代 NTE 固定 ROI，统一坐标映射 |
| `screenshot_util` 的 PrintWindow 实现 | 中 | 作为 CaptureChain 回退，不作为唯一主路径 |
| `keymouse_util` 的 PostMessage 封装 | 中 | 放入 `PostMessageInputAdapter`，外层加限流/审计 |
| 任务进程隔离 `ProcessTask` 思路 | 高 | NTE 每个功能独立 worker，主控 watchdog |
| OCR/OD 服务抽象 | 中 | OCR/YOLO 仅在需要时引入，默认离线、本地、可禁用 |
| Page/Event 模型 | 高 | 剧情/日常任务应从模板循环升级到页面状态机 |
| 战斗 DSL/Combo 思路 | 中 | NTE 自动战斗需要重建领域模型，不能照搬 WWA 角色逻辑 |

### 3.2 需要针对 NTE 特性重新设计的部分

1. **窗口识别**：WWA 使用 `UnrealWindow` + 鸣潮标题；NTE 需实测窗口类名、标题、进程路径、启动器/登录器关系。
2. **WGC 客户区裁剪**：NTE-ai 已实现 DWM extended frame bounds + ClientToScreen，应抽成 `WgcCaptureAdapter`，避免在 `controlfishing_v2.py` 与调试工具重复。
3. **钓鱼控制器**：新版“保持在绿色区间内”比追中心更安全，应保留，但需改为状态机 + 限流 + 可配置 ROI/HSV。
4. **剧情模板动作表**：现有 `TEMPLATES_CONFIG` 可迁移为 `Page` 配置，但需多模板投票、失败退避、危险点击二次确认。
5. **自动战斗**：不能照搬 WWA 的角色枚举与连招；需先建立 NTE 的技能状态检测、冷却识别、目标锁定与安全停止条件。
6. **GUI 与日志**：PyQt5 可运行，但建议与 WWA 对齐到 PySide6；日志改为结构化 JSONL + UI 可读摘要。

### 3.3 建议模块化安全架构与接口定义

```text
nte_assistant/
├── app/
│   ├── main.py
│   ├── container.py              # dependency-injector 容器
│   └── config_schema.py          # Pydantic 配置
├── core/
│   ├── geometry.py               # Rect/Point/Scaler
│   ├── window.py                 # WindowGateway Protocol
│   ├── capture.py                # CaptureGateway Protocol
│   ├── input.py                  # InputGateway Protocol
│   ├── vision.py                 # Template/OCR/HSV/OD Protocol
│   ├── page.py                   # Page/Fingerprint/Action
│   └── task.py                   # Task/StateMachine/StepResult
├── safety_runtime/
│   ├── consent.py
│   ├── rate_limiter.py
│   ├── session_budget.py
│   ├── watchdog.py
│   ├── kill_switch.py
│   ├── foreground_guard.py
│   └── audit_logger.py
├── platform_adapters/
│   ├── win32_window.py
│   ├── wgc_capture.py
│   ├── printwindow_capture.py
│   ├── mss_capture.py
│   ├── postmessage_input.py
│   └── foreground_sendinput.py
├── services/
│   ├── story_service.py
│   ├── fishing_service.py
│   ├── combat_service.py
│   └── mini_game_service.py
├── gui/
└── tests/
```

核心数据结构：

```python
@dataclass(frozen=True)
class Action:
    kind: Literal["click", "key", "wait", "confirm"]
    target: Point | None = None
    key: Key | None = None
    reason: str = ""
    max_retries: int = 1

@dataclass(frozen=True)
class StepResult:
    status: Literal["continue", "success", "retry", "pause", "stop", "error"]
    reason: str
    next_delay_ms: int = 100

class SafeTask(Protocol):
    name: str
    def prepare(self, ctx: TaskContext) -> None: ...
    def step(self, ctx: TaskContext) -> StepResult: ...
    def cleanup(self, ctx: TaskContext) -> None: ...
```

---

## 4. 功能扩展安全评估

### 4.1 自动战斗 / 自动任务的安全实现方案

自动战斗是高频输入场景，风险高于剧情点击和钓鱼。建议分阶段：

1. **只读状态识别**：先做技能图标、血条、目标锁定、战斗/非战斗状态识别，不发送输入。
2. **低频辅助动作**：仅允许拾取、确认、退出异常页面等低频动作。
3. **受限 Combo DSL**：每个动作必须声明最大频率、最长持续时间、前置状态和退出条件。
4. **战斗状态机**：

```text
IDLE → DETECT_COMBAT → SELECT_TARGET → EXECUTE_COMBO_STEP
  ↑          │                 │              │
  └── STOP ← ERROR ← LOST_TARGET ← COOLDOWN ←─┘
```

安全条件：
- 目标丢失、窗口失焦、血条/技能识别异常、输入被拒超过阈值时停机。
- 禁止无限循环连点；每个 combo step 必须可中断。
- 战斗任务默认前台模式；后台模式必须单独评审。

### 4.2 自动钓鱼等小游戏的安全实现方案

钓鱼适合保留 NTE-ai 新版思路：WGC 捕获 + HSV 绿色区 + 黄色模板 + 区间保持控制。但需改造：

```text
FishingService
├── DetectPromptState      # 识别 F/开始/空白/鱼图提示
├── StartFishingState      # 低频按键/点击，必须限流
├── TrackBarState          # WGC 只读帧 + 控制器输出 A/D pulse 请求
├── ConfirmResultState     # 成功/失败/超时识别
└── CleanupState           # release_all + capture.stop
```

安全控制：
- A/D 脉冲由 `InputGateway.key_hold()` 执行，不能直接 `pydirectinput.keyDown()`。
- 脉冲上限、间隔、单次钓鱼最大时长全部配置化。
- 连续失败、首帧超时、绿色区/黄标丢失、窗口尺寸变化时停机。
- 默认不保存钓鱼帧；ROI 调试图必须用户主动开启并自动脱敏。

### 4.3 OCR / 图像识别的安全使用方式

推荐技术：
- 模板/HSV：`opencv-python>=4.11`、`numpy==1.26.4` 或与 OpenCV 兼容的锁定版本。
- OCR：优先 `rapidocr==3.5.0`（WWA 已用），可选 `paddleocr==3.3.2` 但作为 extra。
- OD：如需目标检测，优先 ONNX Runtime：`onnxruntime==1.20.0` / `onnxruntime-directml==1.20.0`，避免在线模型和云端截图。

安全策略：
- OCR 默认只读指定 ROI，不读取聊天框、好友列表、账号区域。
- OCR 结果不记录原文，只记录匹配到的页面 key 和置信度。
- 模型文件固定 hash；模型更新走版本签名和 changelog。
- 禁止将截图上传云端识别，除非用户逐次明确授权且文档另行评审。

### 4.4 配置管理和日志安全

配置 Schema 示例：

```python
class SafetyConfig(BaseModel):
    require_consent_each_session: bool = True
    foreground_required_for_sendinput: bool = True
    max_events_per_second: int = Field(default=8, ge=1, le=20)
    max_session_minutes: int = Field(default=90, ge=5, le=120)
    max_daily_minutes: int = Field(default=360, ge=10, le=480)
    stop_on_focus_lost_seconds: float = Field(default=3.0, ge=0.5, le=30)
    stop_on_recognition_failures: int = Field(default=20, ge=3, le=100)
    allow_debug_screenshots: bool = False
```

审计日志 JSONL 示例：

```json
{"ts":"2026-04-25T12:00:00Z","session_id":"...","task":"fishing","action":"tap_key","target":"hwnd_hash:ab12","decision":"allow","reason":"green_zone_left","rate_window":"3/8"}
```

禁止日志字段：账号、昵称、聊天文本、完整窗口标题、完整 exe 路径、原始截图、OCR 原文、输入设备序列号。

---

## 5. 实施路线图

### Phase 1：安全底座与红线门禁（1–2 周）

目标：先让项目“不会失控、不会旁路、不会泄露”。

交付：
- Poetry + `pyproject.toml` + lockfile。
- Pydantic 配置模型。
- `WindowGateway`、`InputGateway`、`CaptureGateway` 空实现/测试替身。
- `ConsentGate`、`RateLimiter`、`KillSwitch`、`AuditLogger`。
- CI 静态检查：禁止业务层直接调用 OS 输入/截图库。
- `SECURITY.md` 红线清单。

验收标准：
- grep/ruff 规则证明 `pyautogui`、`pydirectinput`、`PostMessage`、`SendInput` 等只在 adapter 层出现。
- 注入 1000 events/s，实际下发不超过配置上限。
- KillSwitch 触发后 P99 ≤ 200ms 停止下发输入。
- 日志样例不含敏感字段。

### Phase 2：窗口、截图、输入抽象与 NTE 钓鱼重构（2–4 周）

目标：把 NTE-ai 中最成熟但分散的 WGC 钓鱼流程迁入安全框架。

交付：
- `Win32WindowAdapter`：窗口指纹、DPI、客户区坐标。
- `WgcCaptureAdapter`：复用 NTE 的 DWM crop 思路。
- `PrintWindowCaptureAdapter` / `MssCaptureAdapter`：兼容回退。
- `PostMessageInputAdapter` / `ForegroundSendInputAdapter`：统一走 `InputGateway`。
- `FishingService` 状态机：替代 `fishing.py` + `controlfishing_v2.py` 的全局变量/直接输入。
- ROI/HSV/阈值配置化。

验收标准：
- 同名窗口测试：exe/hash 不匹配时拒绝操作。
- 100%/125%/150% DPI 下 ROI 坐标误差 ≤ 2px。
- WGC 黑屏/首帧超时/窗口失焦均触发暂停或停机。
- 钓鱼控制器异常退出时 `release_all()` 必定执行。

### Phase 3：页面状态机、自动任务/战斗扩展与持续审计（4–8 周）

目标：把剧情跳过、日常任务、自动战斗等扩展到同一安全运行时。

交付：
- `PageService`：多模板/多 ROI/可选 OCR 的页面识别。
- `StoryService`：替代固定模板扫描循环。
- `DailyTaskService`：页面驱动任务流。
- `CombatAssistService` MVP：先只读识别，再低频辅助，再受限 combo。
- Feature Safety Checklist 接入 PR 模板。
- 依赖审计：`pip-audit`、许可证检查、模型 hash 检查。

验收标准：
- 连续识别失败、页面未知、危险页面、失焦、输入拒绝均可停机。
- 单次运行超过配置时长自动停止并要求重新授权。
- 新功能 PR 必须填写安全清单且通过红线扫描。
- 长跑 4 小时无 GDI/句柄/内存明显泄漏。

### 技术选型建议

| 类别 | 推荐 | 版本建议 | 说明 |
|---|---|---|---|
| Python | CPython | `>=3.11,<3.13` | 与 WWA 兼容，生态稳定 |
| 包管理 | Poetry | `>=2.1` | WWA 已用，lockfile 可审计 |
| GUI | PySide6 | `>=6.8,<7` | 替代 PyQt5，许可证更友好 |
| DI | dependency-injector | `>=4.45,<5` | 与 WWA 对齐 |
| 配置 | pydantic | v2 | 强 Schema 校验 |
| 图像 | opencv-python | `>=4.11` | 模板/HSV |
| 数值 | numpy | `==1.26.4` 起步 | 与 WWA 一致，降低兼容风险 |
| 截图 | windows-capture | `>=1.4` | NTE 已用 WGC |
| 截图回退 | pywin32 / mss | `pywin32>=308`, `mss>=10` | PrintWindow/mss |
| OCR | rapidocr | `==3.5.0` | WWA 默认 |
| 推理 | onnxruntime | `==1.20.0` | 与 WWA 一致 |
| 进程 | psutil | `>=7,<8` | exe 路径、进程存活 |
| 日志 | structlog + orjson | 最新稳定锁定 | JSONL 审计 |
| 测试 | pytest/pytest-cov/hypothesis | 锁定小版本 | 状态机与限流测试 |
| 静态 | ruff/mypy/bandit/pip-audit | 锁定小版本 | 质量与依赖门禁 |

---

## 6. 风险评估矩阵

等级：L=低，M=中，H=高，C=红线禁止。

| 模块/功能 | 检测/安全风险 | 等级 | 缓解措施 | 应急方案 |
|---|---|---|---|---|
| 窗口枚举与绑定 | 误绑定同名窗口、误操作非游戏 | H | hwnd+pid+exe+class+用户确认 | 拒绝输入并提示重新绑定 |
| WGC 捕获 | 持续捕获窗口、兼容性黑屏 | M | 用户授权、只捕 ROI、健康检查 | 回退 PrintWindow/mss；失败停机 |
| PrintWindow/BitBlt | DX/Unreal 黑屏、坐标错位 | M | 仅回退，首帧校验 | 自动切换或停机 |
| mss 前台截图 | 隐私区域入镜 | M | 仅 ROI、默认不落盘 | 清除调试图、提示用户 |
| PostMessage 输入 | 后台消息模式异常、游戏不接受 | M/H | 限流、低频、窗口校验 | 切前台 SendInput 或停机 |
| SendInput/pydirectinput | 全局输入劫持、影响用户 | H | 仅前台、每会话授权、热键停机 | 立即 release_all + 停机 |
| 剧情跳过 | 固定模板/固定节奏 | M | 页面状态机、有界随机、退避 | 连续失败停机 |
| 自动钓鱼 | 高频 A/D 脉冲、长时间运行 | H | 区间控制、限流、会话上限 | 脉冲异常立即 release_all |
| 自动战斗 | 高频连招、收益高、规则风险 | H | 分阶段、前台默认、combo 可中断 | 默认关闭，异常停机 |
| OCR | 读取聊天/账号隐私 | M | ROI 白名单、不存原文 | 清理日志，关闭 OCR |
| YOLO/OD 模型 | 模型供应链、体积与性能 | M | hash 校验、离线模型 | 禁用模型功能 |
| 配置文件 | 用户调高频率绕过限流 | M | Pydantic 上限、硬编码安全上限 | 拒绝启动并提示 |
| 日志 | 泄露路径、标题、截图、OCR | H | 脱敏 JSONL、禁原图 | 一键清理日志 |
| 自动更新 | 供应链劫持 | H | 签名/hash、手动确认 | 禁用自动执行更新 |
| 进程隐藏/伪装 | 对抗性高危 | C | 禁止 | 拒绝需求 |
| 内存读写/DLL 注入/Hook | 反作弊与法律高危 | C | 禁止 | 拒绝需求 |
| 网络抓改包 | 协议作弊高危 | C | 禁止 | 拒绝需求 |
| 驱动/ETW 抑制 | 恶意软件特征 | C | 禁止 | 拒绝需求 |

### 红线清单

以下事项永久禁止，且不得在文档中提供可操作步骤：

1. 读取或写入游戏进程内存。
2. DLL 注入、API Hook、DirectX/OpenGL Hook。
3. 内核驱动、虚拟 HID 驱动、驱动级输入。
4. 进程隐藏、进程名伪装、签名伪造、反调试对抗。
5. ETW/系统审计抑制或篡改。
6. 网络抓包、改包、重放、中间人。
7. 修改游戏客户端文件、资源、shader、存档。
8. 收集账号密码、聊天、好友、支付信息。
9. 托管、代练、群控、规模化账号运营。

---

## 7. 结论

NTE 新项目最合理的安全路线不是增加“隐藏”和“规避”，而是把自动化限制在可解释、可授权、可审计的外部辅助边界内。WWA 可提供成熟工程骨架：分层、接口、DI、任务隔离、窗口/截图/输入封装；NTE 自身已有 WGC 钓鱼控制的良好基础。最终建议以 WGC + 安全输入网关 + 状态机 + KillSwitch + 审计日志为 v0.1 主线，先改造钓鱼和剧情，再谨慎扩展到自动任务和自动战斗。任何涉及内存、注入、隐藏、驱动、网络协议的能力均不进入架构。
