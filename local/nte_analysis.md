# NTE-ai 技术分析报告

分析对象：`/Volumes/TP4000PRO/GitHub/NTE-ai`  
分析时间：基于当前工作区源码快照  
分析范围：已阅读全部 Python 源文件（`main.py`, `config.py`, `ui.py`, `automation_thread.py`, `fishing.py`, `controlfishing.py`, `controlfishing_v2.py`, `window_utils.py`, `utils.py`, `floating_log.py`, `roi_check.py`, `roi_debugger.py`, `auto_updater.py`, `renwu.py`）、`README.md`、`requirements.txt`、`version.txt`、GitHub Actions 构建文件及资源目录结构。

---

## 1. Tech Stack & Dependencies

### Python 版本

- `README.md` 标注 Python **3.9+**。
- `.github/workflows/build.yml` 使用 `actions/setup-python@v5`，版本为 **Python 3.10**。
- 项目没有 `pyproject.toml`、`setup.py`、`setup.cfg`、`Pipfile` 或 lock 文件；依赖完全由 `requirements.txt` 声明。

### 核心依赖

`requirements.txt`：

| 依赖 | 作用 |
|---|---|
| `PyQt5>=5.15.0` | 桌面 GUI。 |
| `opencv-python>=4.5.0` | 图像识别、模板匹配、HSV 颜色检测。 |
| `numpy>=1.21.0` | OpenCV 图像数组处理。 |
| `pyautogui>=0.9.53` | 剧情跳过功能中的截图、鼠标点击、键盘按键。 |
| `pillow>=9.0.0` | `ImageGrab` 截屏与 ROI 调试截图。 |
| `pynput>=1.7.6` | 全局 F12 热键监听。 |
| `pygetwindow>=0.0.9` | 通过窗口标题查找窗口。 |
| `pywin32>=305` | Win32 窗口枚举、句柄校验、坐标转换。 |
| `pydirectinput>=1.0.4` | 钓鱼流程中模拟 DirectInput 风格键鼠输入。 |
| `windows-capture>=1.4.0` | Windows Graphics Capture（WGC）窗口捕获，用于新版钓鱼控制器和 ROI 调试器。 |

### 图像识别方式

项目以 **OpenCV 模板匹配 + 固定 ROI + 部分 HSV 颜色阈值** 为核心，没有 OCR、深度学习模型或内存读取。

1. **剧情跳过 / 通用任务自动化**：
   - `automation_thread.py` 加载 `config.TEMPLATES_CONFIG` 中列出的 `images/*.png`。
   - 用 `cv2.imdecode` 读取中文文件名模板，转灰度后按 `SCALE_FACTOR = 0.5` 缩放。
   - 截取游戏窗口后使用 `cv2.matchTemplate(..., cv2.TM_CCOEFF_NORMED)`。
   - 阈值来自 `config.MATCH_THRESHOLD = 0.9`。

2. **钓鱼主流程状态检测**：
   - `fishing.py` 对全屏或指定区域 `ImageGrab.grab()` 截图。
   - 对 `fishingimages/diaoyu.png`, `kaishidiaoyu.png`, `dianjikongbai.png`, `panduandiaoyu.png`, `yu1.png`, `yu.png` 做灰度模板匹配。
   - 阈值 `MATCH_THRESH = 0.7`。

3. **旧版钓鱼条控制**：
   - `controlfishing.py` 在固定 ROI `(597, 61, 1328, 85)` 内通过 `ImageGrab.grab(bbox=...)` 截图。
   - 识别 `hs.png` 与 `dds.png` 两个模板，阈值 `0.6`。

4. **新版钓鱼条控制**：
   - `controlfishing_v2.py` 使用 `windows_capture.WindowsCapture` 对窗口句柄进行 WGC 捕获。
   - 通过 DWM extended frame bounds 计算纯客户区 crop。
   - 用 HSV 范围 `[60,100,150]` 到 `[90,255,255]` 检测绿色得分区。
   - 用 `hs.png` 模板匹配黄色标记，阈值 `YELLOW_MATCH_THRESH = 0.6`。

5. **ROI 调试系统**：
   - `roi_check.py` 生成带红框的静态截图 `debug_screenshots/roi_check.png`。
   - `roi_debugger.py` 使用 WGC 实时镜像窗口，叠加 ROI、绿色区域、黄色标记、FPS 与状态文本。

### GUI 框架

GUI 使用 **PyQt5**，入口为 `main.py`：

- 启用 `Qt.AA_EnableHighDpiScaling` 和 `Qt.AA_UseHighDpiPixmaps`。
- 创建 `QApplication`。
- 设置图标后实例化 `ui.NeonMainWindow`。

`ui.py` 是主窗口实现，使用 `QMainWindow + QTabWidget`，包含：

- 快速剧情
- 战斗宏（开发中）
- 兑奖码
- AI 钓鱼
- AI 麻将（开发中）
- 加入我们

### 构建 / 发布方式

项目没有标准 Python 包结构，也没有 PyInstaller spec。但源码中多处兼容 PyInstaller：

- `main.py`, `fishing.py`, `controlfishing.py`, `controlfishing_v2.py` 使用 `sys._MEIPASS` 或 `sys.frozen` 处理打包资源路径。
- `ui.py` 在 frozen 环境下直接用线程调用 `fishing.main()`，开发环境下用子进程启动 `fishing.py`。
- `.gitignore` 忽略 `dist/`, `build/`, `*.spec`，暗示本地可能使用 PyInstaller，但仓库没有保存 spec。

GitHub Actions 的发布方式不是打 exe，而是：

- tag `v*` 触发；
- Ubuntu 上安装依赖；
- 将 `*.py`, `*.txt`, `*.ico`, `images`, `fishingimages` 打成 `异环薄荷AI.zip`；
- 通过 `gh release create` 上传 release asset。

这意味着官方 CI 产物更像源码/资源 zip，而非真正 Windows 可执行文件。若用户下载后运行，仍需 Python 环境或另有外部分发的 exe。

---

## 2. Architecture & Code Organization

### 文件结构

核心源码非常扁平，全部 Python 文件位于仓库根目录：

```text
NTE-ai/
├── main.py                 # PyQt 入口
├── ui.py                   # 主 GUI，功能入口和线程/进程管理
├── config.py               # 应用名、版本、仓库、模板配置、动作参数
├── automation_thread.py    # 快速剧情/任务跳过自动化线程
├── fishing.py              # 钓鱼状态机主流程
├── controlfishing.py       # 旧版钓鱼条控制器（ImageGrab + 双模板）
├── controlfishing_v2.py    # 新版钓鱼条控制器（WGC + HSV + 模板）
├── window_utils.py         # ctypes 枚举窗口和客户区坐标
├── utils.py                # 窗口截图、日志时间戳工具
├── floating_log.py         # 置顶浮动日志窗口
├── auto_updater.py         # GitHub version.txt 检查
├── roi_check.py            # 静态 ROI 截图检查工具
├── roi_debugger.py         # 实时 ROI/WGC 调试 GUI
└── renwu.py                # 占位任务模块
```

资源目录：

```text
images/           # 剧情跳过模板，如 跳过、确认、领取、调查F 等
fishingimages/    # 钓鱼相关模板，如 hs、dds、diaoyu、yu 等
debug_screenshots/# ROI 调试输出
.github/workflows/build.yml
```

### 模块职责

| 模块 | 职责 | 备注 |
|---|---|---|
| `main.py` | GUI 启动 | 极薄入口。 |
| `ui.py` | 主窗口、菜单、Tab、日志、钓鱼进程管理、全局热键 | 最大文件，UI 与业务调度耦合较高。 |
| `automation_thread.py` | 模板加载、窗口截图、匹配、执行点击/按键 | 继承 `QThread`，通过信号回传日志。 |
| `fishing.py` | 钓鱼流程状态机 | 使用全局事件、全局鱼数、环境变量传 hwnd。 |
| `controlfishing_v2.py` | 低层钓鱼条控制 | 更接近独立控制器，API 与旧版兼容。 |
| `controlfishing.py` | 旧版低层控制 | 仍保留，但 `fishing.py` 当前导入 v2。 |
| `utils.py` | 截图和日志辅助 | 基于窗口标题，不基于 hwnd。 |
| `window_utils.py` | Win32 ctypes 窗口工具 | 当前主流程实际用得较少，UI 中多处直接用 `win32gui` / `pygetwindow`。 |
| `roi_*` | 调试工具 | 与主功能共享 ROI 常量但没有统一配置源。 |
| `auto_updater.py` | 检查远程版本并打开 releases 页面 | 不做自动替换或热更新。 |

### 设计模式

项目整体是 **脚本式 + GUI 调度式**，没有深层框架。可识别的模式包括：

1. **Qt 事件/信号槽模式**
   - `AutomationThread` 通过 `log_signal`, `game_log_signal`, `finished_signal` 与 UI 通信。
   - `HotKeySignals` 将 pynput 回调转为 Qt signal，避免非 GUI 线程直接改 UI。

2. **Producer/Consumer 单槽队列**
   - `controlfishing.py` 的 `pos_queue = queue.Queue(maxsize=1)`。
   - `controlfishing_v2.py` 的 `detection_queue = queue.Queue(maxsize=1)`。
   - 队列满时丢旧数据保留最新帧，适合实时控制。

3. **资源路径适配函数**
   - `fishing.py`, `controlfishing.py`, `controlfishing_v2.py` 都定义 `resource_path()` 以兼容源码运行和 PyInstaller `_MEIPASS`。

4. **策略表驱动的模板动作**
   - `config.TEMPLATES_CONFIG` 将模板文件名、动作类型、动作参数组合为配置表。
   - `automation_thread.py` 统一执行 `click`, `key`, `center_click`。

5. **有限状态机雏形**
   - `fishing.py` 的 `fish_logic()` 可分为“进入钓鱼 → 识别鱼 → 启动跟随 → 等待成功/失败 → 收尾”的顺序状态机，但用 while/if 实现，没有显式状态枚举。

### 配置管理

配置集中度有限：

- `config.py` 管理应用名、GitHub 仓库、模板目录、剧情跳过阈值、循环间隔、动作延迟和剧情模板动作表。
- 钓鱼 ROI、阈值、HSV、控制参数分散在 `fishing.py`, `controlfishing.py`, `controlfishing_v2.py`, `roi_check.py`, `roi_debugger.py`。
- 兑奖码硬编码在 `ui.py`。
- QQ 群号、QQ群链接硬编码在 `ui.py`。
- 目标窗口关键字“异环”在 `ui.py`, `roi_check.py`, `roi_debugger.py` 多处硬编码。
- 版本号来自 `version.txt`，由 `config.get_version()` 读取。

因此项目是“部分配置驱动”。剧情跳过相对容易扩展；钓鱼、UI 文案、ROI、阈值仍偏硬编码。

### 游戏动作抽象

游戏动作主要分三层：

1. **视觉触发层**
   - 模板匹配或 HSV 检测得出游戏状态/目标位置。

2. **动作语义层**
   - 剧情跳过用 `TEMPLATES_CONFIG` 中的 `click`, `key`, `center_click` 表示动作。
   - 钓鱼主流程直接写死“按 F”、“随机点击”、“启动跟随”。
   - 钓鱼控制器把“黄标偏左/偏右”转成 A/D 脉冲。

3. **输入执行层**
   - 剧情跳过：`pyautogui.click()` / `pyautogui.press()`。
   - 钓鱼：`pydirectinput.moveTo()`, `click()`, `press()`, `keyDown()`, `keyUp()`。

没有统一 `Action` interface，也没有可插拔 input backend。自动化能力目前按功能分散实现。

---

## 3. Anti-Cheat & Risk Control

> 结论：NTE-ai 主要采取“只看屏幕 + 模拟常规输入”的低侵入方式，没有直接内存访问、进程注入、网络协议篡改或游戏文件修改。但代码中也没有成熟的反检测/风控体系；高频固定循环、固定模板、固定 ROI、确定性按键节奏仍可能形成自动化特征。

### 与游戏交互方式

项目交互方式包括：

1. **窗口枚举 / 句柄管理**
   - `window_utils.py` 用 `ctypes.windll.user32.EnumWindows` 枚举可见窗口，并通过 `GetClientRect` + `ClientToScreen` 返回客户区屏幕坐标。
   - `ui.py` 用 `pygetwindow.getWindowsWithTitle("异环")` 自动检测剧情窗口。
   - `ui.py` 钓鱼窗口下拉列表用 `win32gui.EnumWindows`，只纳入标题包含“异环”且不包含“异环薄荷AI”的窗口。
   - `fishing.py` 通过环境变量 `FISHING_TARGET_HWND` 接收 UI 选中的窗口句柄。
   - `controlfishing_v2.py` 对 hwnd 调用 `win32gui.IsWindow()` 校验。

2. **屏幕/窗口捕获**
   - 剧情跳过：`utils.screenshot_window_by_title()` 用 `ImageGrab.grab(bbox=rect)` 截窗口区域，找不到时退回 `pyautogui.screenshot()` 全屏截图。
   - 钓鱼主流程：`fishing.find_image()` 默认全屏 `ImageGrab.grab()`。
   - 旧版钓鱼控制：`ImageGrab.grab(bbox=...)` 截客户区固定 ROI。
   - 新版钓鱼控制：`windows-capture` WGC 捕获指定 hwnd，避免全屏抓取并提升帧率和窗口定位可靠性。

3. **输入模拟**
   - 剧情跳过：`pyautogui.click()` 和 `pyautogui.press()`。
   - 钓鱼：`pydirectinput`，包括 `press('f')`, `moveTo()`, `click()`, `keyDown('a'/'d')`, `keyUp()`。
   - 未发现 `win32api.SendMessage/PostMessage`、`SendInput` 直接调用、驱动级输入、内存写入或 DirectX hook。

### 直接内存 / 注入 / Hook

未发现：

- `ReadProcessMemory` / `WriteProcessMemory`
- 进程句柄打开或模块枚举
- DLL 注入
- DirectX/OpenGL hook
- 网络封包操作
- 游戏文件 patch

`README.md` 也明确写明“通过 OpenCV 对游戏画面进行图像识别与模拟操作，不涉及内存读取”。源码与此一致。

### 窗口句柄与客户区处理

`window_utils.py` 的实现是简洁的 ctypes 封装：

- `get_all_windows()` 枚举所有可见且有标题的窗口。
- `get_window_rect(hwnd)` 返回客户区左上/右下转换到屏幕坐标后的矩形。

但主流程并没有统一使用该模块：

- 剧情功能主要通过 `pygetwindow` 标题匹配。
- 钓鱼 UI 直接用 `win32gui.EnumWindows`。
- WGC crop 逻辑在 `controlfishing_v2.py` 和 `roi_debugger.py` 中重复实现。

新版钓鱼的客户区 crop 较细致：先用 `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` 获取 WGC 捕获包含的 DWM 边界，再用 `ClientToScreen` 得到客户区相对 DWM frame 的偏移，最后裁出纯客户区。这比单纯 `GetWindowRect` 更适合 WGC。

### 检测规避措施

存在的低风险设计：

- **不读取内存**：只依赖屏幕图像。
- **不注入游戏进程**：没有 hook 或 DLL。
- **使用窗口句柄和客户区坐标**：减少误操作其他窗口。
- **WGC 捕获时设置 `cursor_capture=False`, `draw_border=False`**：避免捕获光标和 WGC 边框影响识别；这主要是识别稳定性措施，不是反检测。
- **钓鱼点击有随机偏移**：`fishing.random_click(pos, offset=10)` 给点击坐标加入 ±10 像素随机。
- **短脉冲控制**：A/D 不是长期按住，而是 5-40ms 脉冲，减少明显持续输入。

缺失或薄弱点：

- **剧情跳过完全确定性**：点击模板中心、固定阈值、固定 `ACTION_DELAY=0.01`、固定 `LOOP_INTERVAL=0.05`。
- **钓鱼按 F 没有随机化**：多数 `pydirectinput.press('f')` 后固定 sleep 20ms 或 50ms。
- **控制器脉冲公式固定**：`PULSE_SCALE=0.002`, `PULSE_MIN=0.005`, `PULSE_MAX=0.040`，没有噪声或个体差异。
- **没有速率限制/会话限制**：钓鱼主循环成功后 1 秒继续，失败后 3 秒重试，缺少疲劳/休息/异常退避策略。
- **没有检测前台焦点**：代码校验窗口句柄存在，但没有系统性确认游戏窗口在前台或输入目标正确。
- **没有安全停机条件**：除 UI 停止、F12、进程结束外，缺少“识别异常过多自动停机”“窗口尺寸不匹配停机”等风控。
- **没有日志脱敏或安全审计**：日志是 UI/print 级别。

### 风险画像

从反作弊视角，这类工具的风险主要来自：

- 用户态模拟输入库的可检测性（尤其是 `pyautogui`/`pydirectinput` 行为模式）。
- 固定时间间隔和固定反应速度远快于真人。
- WGC/屏幕捕获本身通常比内存读取低风险，但持续捕获指定游戏窗口也可能被安全产品观察到。
- 自动化长时间运行、重复动作过于规律。

NTE-ai 的优势是低侵入；短板是没有系统性 humanization/risk-control layer。

---

## 4. Automation System

### 快速剧情 / 任务跳过主流程（`automation_thread.py`）

`AutomationThread` 是 `QThread` 子类，启动后执行：

1. 初始化时调用 `load_templates()`：
   - 遍历 `config.TEMPLATES_CONFIG`；
   - 从 `images/` 读取模板；
   - 转灰度；
   - 按 0.5 缩放；
   - 保存 `(template_scaled, action, param, h, w)`。

2. `run()` 校验：
   - 必须有模板；
   - 必须有目标窗口标题关键字。

3. 主循环：
   - 逐个模板调用 `find_and_act()`；
   - 任意模板匹配并执行动作后 break，避免同一帧多动作；
   - 若 acted，则 sleep `ACTION_DELAY=0.01`；否则 sleep `LOOP_INTERVAL=0.05`。

4. `find_and_act()`：
   - 通过 `utils.screenshot_window_by_title(window_title)` 截图；
   - 转灰度并按 0.5 缩放；
   - `cv2.matchTemplate` 找最高分；
   - 超过 `MATCH_THRESHOLD=0.9` 后还原坐标；
   - 用 `get_window_rect_by_title` 转成屏幕绝对坐标；
   - 根据 action 执行：
     - `click`: 点击模板中心；
     - `key`: 按参数键；
     - `center_click`: 点击窗口中心或屏幕中心。

`TEMPLATES_CONFIG` 当前包含：跳过箭头、确认、下页、点击空白区域关闭、领取、跳过（ESC）、不可跳过（中心点击）、调查 F、查看放大镜 F、三个点、手 F 等。这个配置表是任务抽象的核心。

### `renwu.py`

`renwu.py` 目前仅为占位：

```python
def run_task():
    print("任务模块运行")
```

实际“任务自动跳过”并不在该模块中，而是在 `AutomationThread` + `config.TEMPLATES_CONFIG` 中实现。

### 钓鱼系统整体流程（`fishing.py`）

`fishing.py` 当前导入：

```python
import controlfishing_v2 as controlfishing
```

主流程为 `main()` 无限循环调用 `fish_logic()`，直到 `global_stop` 被设置。

`fish_logic()` 分四阶段：

1. **进入钓鱼/交互阶段**
   - 循环识别：
     - `diaoyu.png`：发现后按 F；
     - `kaishidiaoyu.png`：随机点击；
     - `dianjikongbai.png`：随机点击；
     - `panduandiaoyu.png`：按 F 并 break。
   - 每 3 秒打印一次“监测中”。

2. **鱼图确认阶段**
   - 等待 `yu1.png` 和 `yu.png`。
   - 分别找到后按 F。
   - 两者都找到才继续，否则失败。

3. **钓鱼条跟随阶段**
   - 从环境变量 `FISHING_TARGET_HWND` 读取 UI 选择的 hwnd。
   - 创建局部 `stop_event`。
   - 调用 `controlfishing.start_follow(stop_event, target_hwnd=target_hwnd)`。

4. **结果等待阶段**
   - 最多等待 15 秒。
   - 出现 `dianjikongbai.png` 视为成功，停止跟随并随机点击，`fish_count += 1`。
   - 出现 `panduandiaoyu.png` 或超时视为逃走/失败。

异常处理：`fish_logic()` 捕获所有异常，打印 traceback，返回 False；`main()` 捕获 KeyboardInterrupt 和异常，finally 中释放 A/D。

### 旧版钓鱼控制器（`controlfishing.py`）

旧版控制器特点：

- 固定 ROI `(597, 61, 1328, 85)`。
- 将 ROI 从客户区坐标转换为屏幕坐标后用 `ImageGrab.grab(bbox=...)`。
- 同时模板匹配 `hs.png` 和 `dds.png`。
- 用两者 x 坐标差 `diff = hs_x - dds_x` 控制 A/D。
- 有 `DEAD_ZONE=2`、多档 pulse（5ms/10ms/20ms/35ms）和 `BRAKE_PULSE=15ms`。
- 检测漂/标静止时会 release_all 并做两次制动。
- 使用队列 `pos_queue(maxsize=1)` 保留最新检测结果。

它体现出“追踪两个模板中心，让一者跟随另一者”的控制思路。

### 新版钓鱼控制器（`controlfishing_v2.py`）

新版控制器设计更清晰：

1. **捕获层 `CaptureWorker`**
   - 使用 WGC 指定 hwnd 捕获。
   - 通过 DWM + ClientToScreen 计算客户区 crop。
   - 在 WGC frame callback 中裁剪、转 RGB、检测绿色区域和黄色标记。
   - 检测结果 `(yellow_x, green_left, green_right)` 写入单槽队列。

2. **检测层**
   - `detect_green_zone(frame_rgb)`：HSV mask 后取有绿色像素的列范围。
   - `detect_yellow_marker(frame_rgb, template)`：在 ROI 内对 `hs.png` 模板匹配。

3. **控制层 `control_worker()`**
   - 计算绿色区宽度和安全缓冲区：`GREEN_BUFFER_PCT = 0.25`。
   - 若黄标在安全区内：释放 A/D，不动作。
   - 黄标在左侧：按 D 一个短脉冲。
   - 黄标在右侧：按 A 一个短脉冲。
   - 脉冲时长：`max(0.005, min(0.040, overshoot_px * 0.002))`。
   - 每次 pulse 后 `INTER_PULSE_SLEEP = 0.010`。

相比旧版，新版不是强行追中心，而是“保持在绿色范围内”，更稳定，也更少输入。

### 状态管理与任务调度

状态管理较轻量：

- UI 侧：
  - `self.automation_thread` 管理剧情线程。
  - `self.fishing_process` 管理开发环境钓鱼子进程。
  - `self.fishing_thread` 管理打包环境钓鱼线程。
  - `QTimer` 每 50ms 拉取钓鱼 stdout 队列更新 UI。

- 自动化线程：
  - `self.running` boolean 控制循环。

- 钓鱼：
  - `global_stop = threading.Event()` 控制主循环。
  - 每次跟随另建 `stop_event` 控制 WGC 和 control worker。
  - `fish_count` 全局计数。

- 控制器：
  - 用 `threading.Event` 停止捕获和控制。
  - 用单槽 queue 传递最新视觉状态。

没有统一 scheduler、任务队列、状态机类、失败重试策略表或插件生命周期管理。

### 游戏状态检测

状态检测完全视觉驱动：

- 是否有按钮/提示：看模板是否出现。
- 是否进入钓鱼条：先通过 `yu1.png` / `yu.png` 等模板推进，再启动控制器。
- 钓鱼条状态：检测绿色区域和黄色 marker 的相对位置。
- 成功/逃走：检测 `dianjikongbai.png` 或 `panduandiaoyu.png`。

优势：无需游戏 API 或内存，适配简单。缺点：强依赖分辨率、UI 缩放、画质、语言、遮挡、模板更新。

---

## 5. UI & User Experience

### 主 UI（`ui.py`）

`NeonMainWindow` 使用深色霓虹风样式：

- 窗口 900x700；
- 背景 `#0a0f1e`；
- 青色边框/按钮；
- `QGraphicsDropShadowEffect` 给主窗口添加 glow；
- 6 个 tab：快速剧情、战斗宏、兑奖码、AI钓鱼、AI麻将、加入我们。

功能体验：

1. **快速剧情**
   - 开始/停止按钮。
   - 显示游戏内浮动日志按钮。
   - 目标窗口标题输入框。
   - 自动检测“异环”窗口按钮。
   - F12 全局热键启动/停止。

2. **钓鱼**
   - 开始/停止按钮。
   - 下拉选择钓鱼目标窗口。
   - 刷新窗口列表。
   - 输出钓鱼日志。
   - 开发环境以子进程运行，打包环境以线程直接调用。

3. **兑奖码**
   - 最新和历史兑换码硬编码。
   - 点击 label 复制到剪贴板，并短暂改变样式。

4. **未完成功能**
   - 战斗宏、AI 麻将只有“开发中”说明。

### 自动更新（`auto_updater.py`）

`AutoUpdater` 机制较简单：

- 从 `https://raw.githubusercontent.com/{owner}/{repo}/main/version.txt` 读取远程版本。
- 本地版本来自 `config.VERSION`，即 `version.txt`。
- 如果 `remote_ver > current_version`，弹出 `QMessageBox`。
- 用户同意后用 `QDesktopServices.openUrl()` 打开 GitHub Releases 页面。

限制：

- 版本比较是字符串比较，不是语义化版本比较；如 `1.0.10` 与 `1.0.9` 可能比较错误。
- 失败时静默，不显示 UI 错误。
- 不下载、不校验、不替换文件。
- `README.md` 的仓库是 `daoqi/NTE-ai`，本地 git remote origin 是 `BlueSkyXN/NTE-ai`，而 `config.py` 使用 `daoqi/NTE-ai`，需要注意 fork 与 upstream 的版本源。

### 日志与调试

1. **普通 UI 日志**
   - `utils.log_message()` 添加 `[HH:MM:SS]` 前缀。
   - `ui.log_signal_ui()` 写入主 QTextEdit，超过 500 block 时删除开头。

2. **钓鱼日志**
   - 开发环境子进程 stdout/stderr 被两个 daemon thread 读取到 queue。
   - `QTimer` 每 50ms 刷新到 UI。
   - frozen 环境直接线程调用时，`print` 不会自动进入 UI（除非 stdout 被外部重定向），这是体验不一致点。

3. **浮动日志窗口**
   - `floating_log.py` 使用无边框、置顶、半透明 QWidget。
   - QTextEdit 最大 50 行。
   - 支持拖动，默认显示到屏幕右下角。
   - 剧情自动化会通过 `game_log_signal` 同步动作日志。

4. **控制台 print**
   - `fishing.py`, `controlfishing*.py`, `roi_*` 大量使用 `print`。
   - 没有 Python `logging` 模块、日志级别、日志文件或结构化日志。

### ROI 系统

ROI 固定为 `(597, 61, 1328, 85)`，假定游戏客户区布局接近 1920x1080。

工具链：

1. **`roi_check.py`**
   - 枚举标题包含“异环”但不包含“异环薄荷AI”的窗口。
   - 打印客户区大小、ROI 窗口坐标、ROI 屏幕坐标。
   - 截全屏，在 ROI 处画红框，保存 `debug_screenshots/roi_check.png`。

2. **`roi_debugger.py`**
   - 实时窗口镜像。
   - 使用 WGC 捕获和客户区 crop。
   - 显示 FPS。
   - 绘制 ROI 红框、绿色得分区、黄色标记、是否在区间内。
   - 可用于调试新版 `controlfishing_v2.py` 的算法。

问题：

- ROI 常量在 `fishing.py`, `controlfishing.py`, `controlfishing_v2.py`, `roi_check.py`, `roi_debugger.py` 多处重复。
- 没有 UI 配置 ROI，也没有按窗口大小自动缩放 ROI。
- ROI 工具与主程序之间没有配置回写机制。

---

## 6. Testing & Quality

### 测试覆盖

未发现测试目录或测试文件：

- 无 `tests/`。
- 无 `test_*.py` / `*_test.py`。
- 无 `pytest.ini` / `tox.ini`。
- CI 也不运行测试，只安装依赖并打 zip。

这意味着项目质量主要依赖人工运行和 ROI 调试工具。

### 错误处理模式

优点：

- 多数长循环中有 try/except，避免单帧识别异常直接崩溃。
- `AutomationThread.load_templates()` 对模板不存在、解码失败有日志。
- `AutomationThread.run()` 对没有模板、没有窗口标题会退出并发 signal。
- `fishing.py` 主流程有 `try/finally` 释放 A/D。
- `controlfishing_v2.py` 对 WGC 启动失败、模板缺失、窗口句柄无效有返回 False。
- UI 对找不到脚本、未选窗口、重复启动有提示。

问题：

- 一些 bare `except:` 会吞掉异常，例如 `ui.start_hotkey_listener()`、`controlfishing.py` 捕获和队列操作，降低可诊断性。
- `controlfishing_v2.py` 中 frame callback 只 print，不回传 UI。
- 线程/子进程退出状态没有统一错误码或错误对象。
- `stop_event._capture_worker = capture` 是动态挂属性，清理依赖约定；`fishing.py` 只 `stop_event.set()`，没有显式调用 `capture.stop()`，虽然 callback 会看到 stop 并停止，但异常路径下资源清理不够明确。
- UI frozen 模式下钓鱼线程日志不进入 `fishing_log`，错误可见性较弱。

### 日志方法

项目混合使用：

- Qt 信号 + QTextEdit：剧情自动化日志。
- QTextEdit + stdout queue：开发环境钓鱼日志。
- `print`：钓鱼、WGC、ROI 调试。
- 无 `logging` 标准库。
- 无日志文件、trace id、模块级 logger、debug/info/warn/error 分级。

对个人工具足够；若要长期维护或对比更成熟项目，则可观测性偏弱。

### 代码质量观察

优点：

- 文件少，入口清晰，容易读懂。
- 核心算法直观，依赖少。
- `controlfishing_v2.py` 注释较充分，分层比其他模块清楚。
- `AutomationThread` 使用 Qt signal 避免 UI 线程问题。
- 队列保留最新帧的实时控制思路合理。

短板：

- 业务、UI、进程管理在 `ui.py` 高度耦合。
- 配置分散，ROI/窗口关键字/兑换码硬编码。
- 无类型标注和单元测试。
- 无统一异常和日志体系。
- 中英文注释混用，部分文件像快速迭代实验代码。
- `renwu.py` 与 README 中“任务模块”预期不一致，只是占位。
- `window_utils.py` 与实际窗口管理逻辑重复/割裂。

---

## 7. Portability & Extensibility

### 平台可移植性

NTE-ai 是强 Windows 项目：

- `ctypes.windll.user32`、`ctypes.windll.dwmapi`。
- `win32gui`、`pywin32`。
- `windows-capture` WGC。
- `ImageGrab` 截屏行为也主要针对桌面环境。
- `pydirectinput` 面向 Windows DirectInput 场景。

在 macOS/Linux 上基本无法运行核心功能。当前分析环境为 Darwin，因此不适合直接执行程序验证。

### 分辨率 / UI 缩放适配

可移植性较弱：

- 钓鱼 ROI 写死为 1920x1080 下的客户区坐标。
- 模板匹配依赖图像资源、语言、画质和 UI 状态。
- 剧情跳过只做截图和模板同时缩放 0.5，不做多尺度模板匹配。
- `MATCH_THRESHOLD` 高达 0.9，鲁棒性取决于模板是否精准。
- 没有 DPI/分辨率自动标定流程；虽然 Qt UI 开启高 DPI，但游戏识别层没有高 DPI 适配。

### 新功能扩展难度

#### 容易扩展的部分

1. **剧情跳过模板动作**
   - 新增 `images/*.png` 模板。
   - 在 `config.TEMPLATES_CONFIG` 添加 `(filename, action, param)`。
   - 若动作只是点击、按键、点击中心，几乎不用改代码。

2. **兑换码**
   - 修改 `ui.py` 中列表即可，但不是配置化。

3. **钓鱼控制算法实验**
   - `fishing.py` 以 `import controlfishing_v2 as controlfishing` 的方式引用，旧/新控制器保持 `start_follow(stop_event, target_hwnd=None)` 兼容签名，便于替换控制器。

4. **ROI 调试**
   - 已有独立实时调试器，对算法调整友好。

#### 较难扩展的部分

1. **新增复杂任务**
   - 缺少任务基类、状态机框架、动作库、统一视觉 detector。
   - 新功能大概率会新增脚本并在 UI 中硬接按钮。

2. **多游戏/多语言/多分辨率**
   - 窗口标题、ROI、模板目录、阈值都分散硬编码。
   - 没有 profile/config 文件机制。

3. **更高级识别**
   - README 提到 YOLOv8 规划中，但 requirements 未包含 `ultralytics`，源码也没有模型加载/推理接口。
   - 当前 OpenCV pipeline 没有抽象成 detector 接口。

4. **输入后端替换**
   - `pyautogui` 与 `pydirectinput` 直接散落在业务代码中。
   - 没有统一 `InputController`，难以集中加入随机化、焦点校验、限速、停机保护。

### 模块化 vs 单体化

项目不是完全单体，但更接近“多个脚本 + 一个大 UI”：

- `automation_thread.py` 和 `controlfishing_v2.py` 有一定模块边界。
- `ui.py` 负责太多：界面、窗口枚举、进程管理、日志、状态控制、菜单、硬编码数据。
- `fishing.py` 是过程式状态机，和资源路径、视觉识别、动作执行强耦合。
- 工具模块重复逻辑较多，没有统一核心包。

对小型个人项目可接受；若与更成熟的游戏自动化项目比较，NTE-ai 的工程化程度偏早期。

---

## 8. 与另一个游戏自动化项目比较时的关键维度

可作为对比基准的观察点：

| 维度 | NTE-ai 当前状态 | 对比时应关注 |
|---|---|---|
| 侵入性 | 屏幕识别 + 输入模拟，无内存读取 | 另一项目是否使用内存、OCR、CV、模型、Hook。 |
| 识别技术 | OpenCV 模板匹配 + HSV，未接 YOLO/OCR | 是否有多尺度、特征匹配、目标检测、语义状态机。 |
| 输入技术 | `pyautogui` + `pydirectinput` | 是否有 DirectInput、SendInput、虚拟 HID、消息注入。 |
| 风控 | 低侵入但缺少系统 anti-detection | 是否有人类化、限速、随机、焦点检查、异常停机。 |
| UI | PyQt5 tabs，视觉完成度较高 | 是否有配置 UI、调试 UI、任务编排 UI。 |
| 架构 | 扁平脚本，UI 耦合较高 | 是否有插件化任务、Detector/Action 抽象、统一配置。 |
| 配置 | 部分配置在 `config.py`，大量硬编码 | 是否支持 profile、外部 YAML/JSON、热加载。 |
| 调试 | ROI 检查和实时 WGC debugger 较实用 | 是否有录制回放、截图归档、标注工具、测试素材集。 |
| 测试 | 无自动化测试 | 是否有单元测试、离线图像测试、CI。 |
| 打包 | CI 打 zip，源码兼容 PyInstaller | 是否有稳定 exe 构建、签名、自动更新。 |

---

## 9. Strengths / Weaknesses / Improvement Suggestions

### Strengths

- 低侵入：不读内存、不注入、不修改游戏进程。
- GUI 可用性不错：PyQt tab、日志、浮动窗口、热键、窗口选择都有。
- 剧情跳过模板表设计简单有效，适合快速加模板。
- 新版钓鱼控制器从 ImageGrab 升级到 WGC，捕获和客户区裁剪更专业。
- ROI 调试器提供实时叠加可视化，对调参很有帮助。
- 代码量小，入门和二次修改成本低。

### Weaknesses

- Windows-only，跨平台能力几乎没有。
- 无测试、无类型、无标准 logging，质量保障弱。
- 配置分散且硬编码较多，尤其是 ROI、窗口标题、兑换码、阈值。
- UI 与业务调度耦合，后续功能增加会让 `ui.py` 继续膨胀。
- 缺少统一 Detector、Action、Task、Input backend 抽象。
- 反检测/风控仅停留在低侵入和少量点击随机，缺少系统的人类化与安全停机。
- 自动更新只是打开 release 页面，不是真正自动更新。
- 发布流程只打 zip，不生成可执行程序。

### Improvement Suggestions

1. **统一配置系统**
   - 将 ROI、模板阈值、窗口关键字、兑换码、循环间隔移到 YAML/JSON。
   - 支持不同分辨率 profile。

2. **抽象核心接口**
   - `Detector`：模板匹配、HSV、未来 YOLO/OCR。
   - `ActionExecutor`：pyautogui/pydirectinput 后端。
   - `Task`：start/stop/tick/state/error。
   - `WindowProvider`：统一 pygetwindow/win32gui/ctypes 逻辑。

3. **增强风控**
   - 加入焦点检查、窗口尺寸校验、最大连续运行时长、异常识别停机。
   - 对点击位置、反应时间、按键持续时间加入合理随机扰动。
   - 降低固定高速循环特征，加入状态驱动而非纯轮询。

4. **提升识别鲁棒性**
   - 支持多尺度模板匹配或按窗口尺寸缩放 ROI。
   - 保存失败截图，形成离线测试集。
   - 对关键模板增加置信度日志和调试面板。

5. **工程化**
   - 拆分 `ui.py`，将每个 tab 和服务层分开。
   - 引入 `logging`。
   - 增加离线图像测试（给截图，验证 detector 输出）。
   - 在 CI 中至少运行 import/静态检查/离线 detector 单测。

6. **打包与更新**
   - 增加 PyInstaller spec 或 Nuitka 构建脚本。
   - Windows runner 构建 exe。
   - 自动更新可加入下载、校验 hash、替换/重启流程。

---

## 10. 总体结论

NTE-ai 是一个以 **PyQt5 GUI + OpenCV 视觉识别 + 用户态输入模拟** 为核心的小型 Windows 游戏自动化工具。它的技术路线偏低侵入，避免了内存读取和注入，风险相对低于内存/Hook 类方案；但它并没有完整的 anti-detection 或风控体系，自动化节奏和输入模式仍较机械。

从架构上看，它适合快速验证和个人使用：源码少、流程直观、模板配置简单、ROI 调试工具实用。与更成熟的游戏自动化项目相比，它的主要差距在工程化、配置化、可测试性、插件化和风险控制层。若目标是长期维护或扩展到更多玩法，优先应做配置统一、任务/识别/输入抽象、日志测试体系和安全停机机制。
