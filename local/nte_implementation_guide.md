# NTE-ai 基于 WWA 架构的重构实施指南

> 目标：用 WWA（WutheringWavesAssistant）的成熟工程架构、安全输入/截图层与 OCR/ONNX 识别能力，重构 NTE-ai（异环薄荷 AI）的全部现有功能，并为后续扩展（自动战斗、自动任务）打底。
>
> 参考文档：
> - `local/wwa_analysis.md` — WWA 全量分析
> - `local/nte_analysis.md` — NTE-ai 全量分析
> - `local/wwa_vs_nte_comparison.md` — 二者技术对比
> - `local/nte_security_framework.md` — NTE 新项目安全框架（**红线请遵守**）
>
> 风格约定：本指南示例代码以伪 Python 给出**接口与关键逻辑**，不复制 WWA 源码，但保持 API 形态与 WWA 对齐，方便后续直接借用 WWA 的 `util/` 实现细节。
>
> **红线（来自 `nte_security_framework.md` §2.6 / §6）**：禁止内存读写、DLL 注入、API/DX Hook、驱动级输入、进程隐藏、ETW 抑制、抓改包、修改客户端文件。本指南所有方案均在用户态外部辅助边界内。

---

## 0. 整体路线图

按"先底座后业务，先识别后输入"的顺序：

```
Phase 0  仓库脚手架（Poetry / Pydantic / 目录骨架）
Phase 1  Safety Runtime + 平台适配层（Window / Capture / Input Gateway）
Phase 2  视觉网关（Template / HSV / OCR / OD）
Phase 3  钓鱼服务重构（去掉全局变量、HSV→ColorChecker、env var → DI）
Phase 4  剧情自动化升级（模板表 → Page 状态机 + OCR 兜底）
Phase 5  PySide6 + Fluent UI 迁移
Phase 6  扩展能力（自动战斗 MVP、ONNX 物体检测、麻将）
```

每个阶段都会在下文 §7 给出具体步骤、验收标准与代码骨架。

---

## 1. NTE 功能清单 → WWA 对应映射

### 1.1 NTE 现有功能完整清单（来自 §读源码）

| 模块 | 文件 | 功能 | 入口 |
|---|---|---|---|
| 主入口 | `main.py` | QApplication + 高 DPI + 图标 + `NeonMainWindow` | — |
| 主窗口 | `ui.py` | QTabWidget 6 个 Tab：剧情 / 战斗（占位）/ 兑奖码 / 钓鱼 / 麻将（占位）/ 加入我们 | `NeonMainWindow` |
| 自动剧情 | `automation_thread.py` | QThread 循环：截图 → 灰度 → 0.5x 缩放 → `cv2.matchTemplate(TM_CCOEFF_NORMED)` → 阈值 0.9 → 点击/按键 | `AutomationThread.run()` |
| 模板配置 | `config.py` | `TEMPLATES_CONFIG` 13 条 `(png, action, param)` | — |
| 钓鱼-总流程 | `fishing.py` | 4 阶段串行：监测 → 双鱼图 → 启动跟随（env `FISHING_TARGET_HWND`）→ 等待结果 | `fish_logic()` |
| 钓鱼-控制 v1 | `controlfishing.py` | `ImageGrab.grab(bbox=ROI)` + 双模板（hs/dds）+ 追中心式 A/D 控制 | `start_follow()` |
| 钓鱼-控制 v2 | `controlfishing_v2.py` | WGC 捕获 + DWM 客户区裁剪 + HSV 绿色区 + 模板黄标 + 区间保持脉冲控制 | `start_follow()` |
| 窗口工具 | `window_utils.py` | `EnumWindows` + `GetClientRect` + `ClientToScreen` | — |
| 截图工具 | `utils.py` | `pygetwindow` + `ImageGrab.grab(bbox=...)` 全屏兜底 | `screenshot_window_by_title()` |
| ROI 静态调试 | `roi_check.py` | 全屏截图 → `ImageDraw.rectangle` 红框 → 落盘 PNG | — |
| ROI 实时调试 | `roi_debugger.py` | WGC 实时镜像 + ROI/HSV/FPS/状态叠加（PyQt5 浮窗） | — |
| 浮动日志 | `floating_log.py` | 半透明置顶 `QTextEdit`，`setMaximumBlockCount(50)`，可拖动 | — |
| 自动更新 | `auto_updater.py` | 拉 `raw.githubusercontent.com/.../version.txt`，比版本，弹窗跳浏览器 | — |
| 任务（占位）| `renwu.py` | 1 个空函数 | — |

### 1.2 一一映射到 WWA 的等价模块

| NTE 模块/能力 | WWA 等价模块 | 复用方式 |
|---|---|---|
| `pyautogui.click/press` | `src/util/keymouse_util.py` 的 `click/tap_key`（PostMessage） | **直接抄**，仅改窗口类名常量 |
| `pydirectinput.keyDown/keyUp` | `src/util/keymouse_util.py` 的 `key_down/key_up` | **直接抄** |
| `PIL.ImageGrab.grab()` | `src/util/screenshot_util.py` 的 `screenshot()`（PrintWindow PW_RENDERFULLCONTENT） | **直接抄** |
| `pygetwindow.getWindowsWithTitle` | `src/util/hwnd_util.py` 的 `_find_all_windows + get_hwnd_by_class_and_title` | 改 `WUWA_HWND_CLASS_NAME → "UnrealWindow"`（异环若同为 UE，复用），改标题白名单 |
| `windows-capture` WGC（v2 钓鱼） | WWA 暂未用，但可作为 `ImgService.set_capture_mode(WGC)` 第 4 后端引入 | **保留 NTE 已有 v2 的 WGC 实现** + 适配 WWA 接口 |
| `cv2.matchTemplate`（灰度+0.5 缩放） | `src/util/img_util.py` + `ImgService.match_template()` | **直接抄**，并升级为多尺度（见 §2.3） |
| HSV 绿色检测（v2 钓鱼） | WWA 无 HSV，但 `ColorChecker`（BGR 容差，§4.1）思想类似 | 可两者并存：HSV 仍用于"动态条带"，`ColorChecker` 用于"静态像素点" |
| 无 OCR | `src/service/ocr_service.py` `RapidOcrServiceImpl` | **直接抄**（首选 RapidOCR 3.5，CPU/DML/CUDA 由 onnxruntime extras 切换） |
| 无 ONNX/OD | `src/service/od_service.py`（YOLO） | 暂不引入；钓鱼/剧情不需要；自动战斗 v2 再考虑 |
| `TEMPLATES_CONFIG` 三元组循环 | WWA `pages.py` 的 `Page` + `TextMatch` + `ConditionalAction` | NTE 适配为"轻量 Page 表"（见 §5.2） |
| 全局变量 `global_stop / fish_count / FISHING_TARGET_HWND` | WWA `Context` + `BossTaskContext`（Pydantic） | 改为 `TaskContext` 注入 |
| `automation_thread.AutomationThread(QThread)` | WWA `multiprocessing.Process` + `TaskMonitor` | 钓鱼/剧情先用线程也可；远期建议进程隔离 |
| `floating_log.FloatingLogWindow` | WWA `src/gui/widgets/...` Fluent log card（无强对应） | 直接迁 PySide6 即可，逻辑不变 |
| `auto_updater` | WWA `WWA一键更新.bat` + `WWA.exe` 启动器 | 保留 NTE 现方案即可，无需改造 |
| `roi_debugger` 实时调试 | WWA 无对应（用 `tests/` 半集成 + print） | **保留并升级**：作为开发态独立工具，不进入运行时 |
| `NeonMainWindow` (PyQt5) | `src/gui/gui.py wwa()` (PySide6 + qfluentwidgets) | 全量迁移到 PySide6（见 §5.3） |
| `KeyboardMappingConfig` 自定义键位 | 同名 WWA 模块 | 钓鱼/剧情按键也建议入配置 |
| `TaskMonitor` 崩溃自重启 | WWA `src/controller/main_controller.py` | Phase 6 引入 |

### 1.3 哪些 WWA 模块**不应**搬到 NTE

避免无谓引入：

- `combat_system.py` 16 个角色枚举、协奏能量颜色 → 鸣潮专属，不搬。
- `boss_info_service.py` BOSS 列表、传送路径 → 鸣潮专属，不搬。
- `EchoMergeService`、`AutoBossService`、`DailyActivityService` → 业务强耦合，重写 NTE 自己的服务即可。
- `dxcam_util.py` → 工具脚本，NTE 暂不需要。
- `pyside6-fluent-widgets[full]==1.7.6` 的全部组件 → 按需引入即可（QTabWidget 等基础已够）。
- `paddleocr` extras → 直接默认 RapidOCR，简化分发。

---

## 2. 图像识别能力升级方案

NTE 当前只有"灰度 0.5 缩放 + `TM_CCOEFF_NORMED` + 固定阈值 0.9 / 0.7 / 0.6"三件套，识别能力弱、对分辨率/语言/UI 改版鲁棒性差。WWA 的 RapidOCR + ColorChecker + ONNX YOLO 是已经验证过的工业级组合，可以分层引入到 NTE。

### 2.1 升级目标层级

| 层级 | 用途 | 引入时机 |
|---|---|---|
| L1 模板匹配（升级版） | 兜底；NTE 50+ 模板继续可用，但要做多尺度 + 灰度/HSV 双模式 | Phase 2 必做 |
| L2 ColorChecker 像素颜色 | 钓鱼条状态、技能冷却、协奏能量等"固定坐标 + 颜色变化"场景 | Phase 3 钓鱼用 |
| L3 RapidOCR | 任务文字、对话名字、提示语、按钮上的"领取/确认/跳过"等多语言场景 | Phase 4 剧情用 |
| L4 ONNX OD | 自动战斗 BOSS 锁定、宝箱定位、麻将牌识别 | Phase 6 才上 |

### 2.2 NTE → 升级版模板匹配

**问题**：NTE `automation_thread.find_and_act` 截屏+缩放+`cv2.matchTemplate` 全部硬编码，对窗口尺寸变化无能为力。

**升级方案**：照搬 WWA `src/service/img_service.py` 的 `ImgServiceImpl.match_template`，并补"多尺度"。

```python
# nte_assistant/services/img_service.py
import cv2
import numpy as np
from src.core.regions import Position  # 复用 WWA Position 即可

class TemplateMatcher:
    def __init__(self, scaler):
        self._scaler = scaler  # 来自 WindowGateway，保存当前 client_wh

    def match(self,
              img: np.ndarray,
              template: np.ndarray,
              region: tuple[int, int, int, int] | None = None,
              threshold: float = 0.85,
              scales: tuple[float, ...] = (1.0, 0.95, 1.05),  # 多尺度
              colorspace: str = "gray",                       # gray / bgr / hsv
              ) -> Position | None:
        if region is not None:
            x1, y1, x2, y2 = region
            img = img[y1:y2, x1:x2]
        img = self._cvt(img, colorspace)
        template = self._cvt(template, colorspace)
        # 按窗口比例缩放模板（来自 WindowGateway，对应 WWA scaler.get_ratio()）
        ratio = self._scaler.get_ratio()
        best = None
        for s in scales:
            tw = int(template.shape[1] * ratio * s)
            th = int(template.shape[0] * ratio * s)
            if tw < 8 or th < 8:
                continue
            tpl = cv2.resize(template, (tw, th), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
            _, maxv, _, maxloc = cv2.minMaxLoc(res)
            if maxv >= threshold and (best is None or maxv > best[0]):
                best = (maxv, maxloc, tpl.shape)
        if best is None:
            return None
        score, (x, y), (h, w) = best
        return Position(x1=x, y1=y, x2=x + w, y2=y + h, score=score)

    @staticmethod
    def _cvt(arr: np.ndarray, colorspace: str) -> np.ndarray:
        if colorspace == "gray":
            return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if arr.ndim == 3 else arr
        if colorspace == "hsv":
            return cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
        return arr
```

**与 NTE 现状对比**：

| 项 | NTE 现状 | 升级后 |
|---|---|---|
| 缩放 | 固定 `SCALE_FACTOR = 0.5` | 按窗口比例 + 多尺度 (0.95/1.0/1.05) |
| 颜色空间 | 仅灰度 | gray / bgr / hsv 三种 |
| 阈值 | 全局 `0.9 / 0.7 / 0.6` 散落 | 每模板可独立配置（见 §5.2） |
| 多分辨率适配 | 无 | 通过 `WindowGateway.scaler` 自动适配 |
| 截图来源 | `ImageGrab` 全屏 | `CaptureGateway` 后台 PrintWindow |

### 2.3 引入 OCR：RapidOCR 3.5

**为何引入**：NTE 用模板识别"领取""确认""跳过"等按钮——文字稍变（汉化更新、按钮换字）就失效。OCR 一次识别全屏文字后用正则匹配，**鲁棒性指数级提升**且不需要再维护 50 个 PNG。

**引入步骤**：

1. **依赖**：`poetry add rapidocr==3.5.0 onnxruntime==1.20.0`（可加 `[dml]` extra 启用 DirectML，国内显卡通用）。
2. **模块**：复制 WWA `src/util/rapidocr_util.py`（`create_ocr` + 参数 `_COMMON_PARAMS / _DML_PARAMS / _GPU_PADDLEPADDLE_PARAMS`）。
3. **服务**：复制 WWA `src/service/ocr_service.py` 的 `AbstractOcrService` + `RapidOcrServiceImpl`（共 282 行，**几乎可直接拿来用**，仅需改 import 路径）。
4. **接口**：在 NTE 的 `core/vision.py` 暴露：

```python
# nte_assistant/core/vision.py
from typing import Protocol
import numpy as np

class OcrService(Protocol):
    def find_text(self, targets: str | list[str],
                  img: np.ndarray | None = None,
                  region: tuple[int, int, int, int] | None = None) -> "TextPosition | None": ...
    def wait_text(self, targets: str | list[str], timeout: float = 3.0,
                  region: tuple[int, int, int, int] | None = None,
                  wait_time: float = 0.1) -> "TextPosition | None": ...
    def ocr(self, img: np.ndarray,
            region: tuple[int, int, int, int] | None = None) -> list["TextPosition"]: ...
```

**NTE 钓鱼的 OCR 用例**：替换"对话框跳过"模板。

```python
# 升级前（NTE）：
("跳过.png", "key", "esc"),

# 升级后（NTE-Refactor）：
PageRule(
    name="dialog_skip",
    detectors=[OcrDetector(text=r"^(跳过|Skip)$",
                           region_rate=(0.85, 0.05, 1.0, 0.15))],
    action=Action.tap_key("ESC"),
)
```

**OCR 性能注意**：
- RapidOCR 默认 CPU 单图 ~150ms（与 WWA 一致），可接受。
- 用 `_resize_img` 把 H>720 的图先压到 720（WWA 已实现，不要漏抄）。
- 加 `OcrInterval` 限频，避免 50ms 循环里堆调用（WWA 默认 0，钓鱼场景建议 0.2）。

### 2.4 ColorChecker：钓鱼条/HUD 状态的最佳工具

**为何引入**：钓鱼条左右进度、协奏能量、技能冷却、玩家是否阵亡——这类**固定坐标 + 离散颜色**场景，OCR 杀鸡用牛刀，模板匹配又对动画帧不稳。WWA `ColorChecker` 用 BGR 像素 + 容差，毫秒级判定。

**关键源码**（`src/core/combat/combat_core.py:216-300`，**直接复制**到 `nte_assistant/core/vision/color_checker.py`）：

```python
class ColorChecker:
    def __init__(self, points, colors, tolerance=30,
                 logic=LogicEnum.OR, align=None):
        self.points = points          # [(x, y), ...] 1280×720 基准坐标
        self.colors = np.array(colors)  # [(B, G, R), ...]
        self.tolerance = tolerance
        self.logic = logic
        self.align = align            # AlignEnum.TOP_CENTER / BOTTOM_RIGHT 等

    def check(self, img: np.ndarray) -> bool:
        dpt = DynamicPointTransformer(img)  # 自动按当前分辨率换算
        if self.logic == LogicEnum.OR:
            for p in self.points:
                tp = dpt.transform(p, self.align)
                target = img[tp[1], tp[0]]
                for c in self.colors:
                    if np.all(np.abs(c - target) <= self.tolerance):
                        return True
            return False
        # AND 逻辑...
```

**NTE 钓鱼应用**：替换"判断鱼是否上钩"的 `panduandiaoyu.png` 模板匹配。先用 ROI 调试器（NTE 已有 `roi_debugger.py`）取 3~5 个像素点位 + 上钩/未上钩两组 BGR，写成：

```python
on_hook_checker = ColorChecker(
    points=[(640, 540), (640, 545), (645, 540)],     # 1280×720 基准
    colors=[(0, 215, 255), (10, 200, 245)],          # 黄色提示框 BGR 两组容差
    tolerance=25,
    logic=LogicEnum.OR,
    align=AlignEnum.TOP_CENTER,
)
# 替换原 fishing.py: pos = find_image(PATH_PANDUANDIAOYU)
if on_hook_checker.check(frame_bgr):
    input_gateway.tap_key("F", reason="fish_hook")
```

**HSV vs ColorChecker 的取舍**：

| 场景 | 推荐 |
|---|---|
| 钓鱼绿色得分区（**位置不固定**，整条带） | HSV `cv2.inRange`（NTE v2 已用，保留） |
| 钓鱼黄色光标位置（**点状**） | 模板匹配（NTE v2 已用，保留），OR 颜色阈值二选一 |
| HUD 上"技能就绪/角色死亡"（**固定点位**） | ColorChecker（多点 OR/AND） |
| 复杂动画/UI 元素 | 模板匹配 + 多尺度 |

### 2.5 总览：识别后端选择决策树

```
需要识别 X
├── X 是文字？ → OcrService.find_text(...)
├── X 是固定点位的颜色变化？ → ColorChecker
├── X 是固定形状的 UI 元素？ → TemplateMatcher (gray + multi-scale)
├── X 是颜色范围（条带、区域）？ → HSV cv2.inRange
└── X 是动态位置的物体？ → ONNX OD（Phase 6）
```

---

## 3. 安全交互层移植方案（NTE 当前的最大短板）

### 3.1 总体目标

把 NTE 现有的 `pyautogui` / `pydirectinput` / `ImageGrab` 三件套，**全量替换**为基于 `win32gui.PostMessage` / `PrintWindow PW_RENDERFULLCONTENT` 的"后台不抢焦点"路径。技术风险：低；工作量：中；收益：极大（用户可一边挂机一边干别的）。

### 3.2 文件级移植映射

| NTE 现有文件 | 调用 | 替换为 | 来源（WWA 文件） |
|---|---|---|---|
| `fishing.py:75` `pydirectinput.press('f')` | 按 F | `keymouse_util.tap_key(hwnd, 'F', 0.05)` | `src/util/keymouse_util.py` |
| `fishing.py:60` `pydirectinput.click()` | 鼠标点击 | `keymouse_util.click(hwnd, x, y, 0.05)` | 同上 |
| `controlfishing_v2.py:264` `pydirectinput.keyDown('d')` | 按住 D | `keymouse_util.key_down(hwnd, 'D')` | 同上 |
| `automation_thread.py:100` `pyautogui.click(x, y)` | 屏幕坐标点击 | `keymouse_util.click(hwnd, win_x, win_y)`（需把屏幕坐标转客户区） | 同上 |
| `automation_thread.py:105` `pyautogui.press(param)` | 按键 | `keymouse_util.tap_key(hwnd, param.upper(), 0.05)` | 同上 |
| `fishing.py:43` `ImageGrab.grab(bbox=...)` | 截屏 | `screenshot_util.screenshot(hwnd, region)` | `src/util/screenshot_util.py` |
| `utils.py:22` `ImageGrab.grab(bbox=rect)` | 全屏截图回退 | `screenshot_util.screenshot(hwnd)` 后裁剪 | 同上 |
| `controlfishing_v2.py` `WindowsCapture` (WGC) | WGC 捕获 | **保留**（钓鱼对实时性要求高，WGC 60FPS 优于 PrintWindow） | NTE 自有 |

### 3.3 按键移植：`pydirectinput → win32gui.PostMessage`

**WWA 关键代码**（`src/util/keymouse_util.py:63-90`）：

```python
KEYBOARD_VK_MAPPING: dict[str, int] = {
    "0": 48, ..., "A": 65, "B": 66, ..., "Z": 90,
    "LSHIFT": win32con.VK_LSHIFT,
    "ESC": win32con.VK_ESCAPE,
    "SPACE": win32con.VK_SPACE,
    "F1": win32con.VK_F1,
    "F2": win32con.VK_F2,
    "ENTER": win32con.VK_RETURN,
}

def tap_key(hwnd, key: str | int, seconds: float = 0.0):
    vk_key = KEYBOARD_VK_MAPPING.get(key.upper()) if isinstance(key, str) else key
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_key, 0)
    __sleep(seconds)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_key, 0)

def key_down(hwnd, key, seconds=0.0):
    vk_key = ...
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_key, 0)
    __sleep(seconds)

def key_up(hwnd, key, seconds=0.0):
    vk_key = ...
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_key, 0)

def __sleep(seconds: float):
    if seconds < 0:
        seconds = random.uniform(0.040, 0.060)  # 40~60ms 抖动
    if seconds > 0:
        time.sleep(seconds)
```

**直接按 NTE 文件改造**：

```python
# 改造前：fishing.py
pydirectinput.press('f')
time.sleep(0.02)

# 改造后：
input_gateway.tap_key("F", reason="fish_F_prompt")  # 经过 RateLimiter / Audit
# 或最底层：
keymouse_util.tap_key(self.hwnd, "F", seconds=0.05)
```

```python
# 改造前：controlfishing_v2.py: control_worker
pydirectinput.keyDown('d')
time.sleep(pulse)
pydirectinput.keyUp('d')

# 改造后（保持脉冲语义）：
with input_gateway.held_key(self.hwnd, "D", reason="fish_track_right") as h:
    h.sleep(pulse)   # 脉冲长度 5~40ms
# 退出 with 自动 key_up，异常时 finally release_all
```

**为什么这个改动是"质变"**：
- `pydirectinput` 走 SendInput，**全局生效**——用户切到浏览器写字，A/D 也会按到浏览器；
- `PostMessage` 走窗口消息，**只发到目标 hwnd**——用户切走完全无感；
- 取消"必须前台"约束，删除 `pygetwindow.activate` 之类的抢焦点逻辑。

**已知风险**（来自 §nte_security_framework §2.3）：
- 部分游戏/反作弊会过滤 `WM_KEYDOWN` 的 `lParam=0`（不带扫描码/重复计数）。WWA 在鸣潮上跑得通；异环若拒收，需要在 `lParam` 里填 `MAKELPARAM(repeatCount=1, scanCode=MapVirtualKey(vk, 0))`。先按 WWA 同款实现，遇到不收再补。

### 3.4 鼠标移植

**WWA 关键代码**（`src/util/keymouse_util.py:95-165`）：

```python
def click(hwnd, x=0, y=0, seconds=0.0):
    l_param = win32api.MAKELONG(int(x), int(y))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
    __sleep(seconds)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l_param)

def right_click(hwnd, x=0, y=0, seconds=0.0): ...
def middle_click(hwnd, x=0, y=0, seconds=0.0): ...
def scroll_mouse(hwnd, count, x=0, y=0, seconds=0.0): ...
```

**坐标语义**：x、y 是**客户区坐标**（左上角为 0,0），不是屏幕坐标。NTE `automation_thread.find_and_act` 把模板中心转屏幕绝对坐标后给 `pyautogui.click`——改造时去掉这一步，直接用 `(center_x_original, center_y_original)`。

```python
# 改造前：automation_thread.py
rect = get_window_rect_by_title(self.window_title)
left, top, _, _ = rect
click_x = left + center_x_original
click_y = top + center_y_original
pyautogui.click(click_x, click_y)

# 改造后：
input_gateway.click(self.hwnd, center_x_original, center_y_original,
                    reason=f"template:{template_name}")
```

### 3.5 截图移植：`ImageGrab → PrintWindow`

**WWA 关键代码**（`src/util/screenshot_util.py:12-76`）：

```python
def screenshot(hwnd, region=None) -> np.ndarray:
    """ 返回 BGR 图（去 alpha） """
    if region is None:
        region = win32gui.GetClientRect(hwnd)
    left, top, right, bottom = region
    width, height = right - left, bottom - top

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(save_bitmap)

    # 关键：flag=3 == PW_RENDERFULLCONTENT，对 DX/UE 兼容
    ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

    bmp_str = save_bitmap.GetBitmapBits(True)
    img = np.frombuffer(bmp_str, dtype=np.uint8)
    img = img.reshape((height, width, 4))[..., :3]  # BGRA → BGR

    # 释放 GDI 资源（不释放会泄漏）
    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)
    return img
```

**改造 NTE `utils.py`**：

```python
# 改造前
def screenshot_window_by_title(title_keyword=None):
    rect = get_window_rect_by_title(title_keyword)
    if rect:
        screenshot = ImageGrab.grab(bbox=rect)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

# 改造后
def screenshot_window(hwnd, region=None) -> np.ndarray:
    return screenshot_util.screenshot(hwnd, region)  # 直接抄 WWA
```

**关键收益**：
- **窗口被遮挡**也能拿到正常画面（`ImageGrab` 必然黑屏）；
- 不进入截屏特征面（不影响 DWM/桌面 hook）；
- 配合 `Alt+Tab` 用户切走依然识别正常。

**已知坑**：
- 部分 UE 渲染模式下 PrintWindow 仍可能黑帧——必须做"首帧黑屏检测"，黑就回退 `mss` 或 WGC（WWA 用 `MaxFightTime` + 重启策略兜底）。NTE 钓鱼场景建议保留 v2 的 WGC 路径作为 capture mode 选项。

### 3.6 InputGateway / CaptureGateway 完整接口

参考 `nte_security_framework.md §2.3 / §2.4`，给出可直接落地的接口：

```python
# nte_assistant/core/input.py
from enum import StrEnum
from typing import Protocol
from contextlib import contextmanager

class MouseButton(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"

class InputGateway(Protocol):
    def click(self, hwnd: int, x: int, y: int, *,
              button: MouseButton = MouseButton.LEFT,
              hold_ms: int = 50, reason: str = "") -> None: ...
    def tap_key(self, hwnd: int, key: str, *,
                hold_ms: int = 50, reason: str = "") -> None: ...
    @contextmanager
    def held_key(self, hwnd: int, key: str, *, reason: str = ""): ...
    def release_all(self, hwnd: int) -> None: ...
```

```python
# nte_assistant/platform_adapters/postmessage_input.py
class PostMessageInputAdapter:
    def __init__(self, rate_limiter, audit_logger, foreground_guard):
        self._held_keys: set[tuple[int, str]] = set()
        self._rl = rate_limiter
        self._audit = audit_logger
        self._fg = foreground_guard

    def tap_key(self, hwnd, key, *, hold_ms=50, reason=""):
        self._rl.acquire()           # 限频
        self._fg.assert_target(hwnd) # 校验目标窗口
        self._audit.log("tap_key", hwnd=hwnd, key=key, reason=reason)
        keymouse_util.tap_key(hwnd, key, seconds=hold_ms / 1000.0)

    @contextmanager
    def held_key(self, hwnd, key, *, reason=""):
        self._rl.acquire()
        self._fg.assert_target(hwnd)
        self._audit.log("key_down", hwnd=hwnd, key=key, reason=reason)
        keymouse_util.key_down(hwnd, key)
        self._held_keys.add((hwnd, key))
        try:
            yield self
        finally:
            try:
                keymouse_util.key_up(hwnd, key)
            finally:
                self._held_keys.discard((hwnd, key))
                self._audit.log("key_up", hwnd=hwnd, key=key)

    def release_all(self, hwnd):
        for h, k in list(self._held_keys):
            if h == hwnd:
                try:
                    keymouse_util.key_up(h, k)
                except Exception:
                    pass
                self._held_keys.discard((h, k))
```

**`held_key` 是 NTE 当前最大的 bug 来源**：`controlfishing_v2.control_worker` 在异常退出时全靠 `release_all()`，但若 control_worker 线程被 KillSwitch 强杀，`finally` 也跑不到。`held_key` 上下文管理器 + `release_all(hwnd)` 是双保险。

---

## 4. 状态机与事件驱动移植

### 4.1 NTE 现状 vs WWA 模式

**NTE 钓鱼**（`fishing.py`）是典型的"4 阶段串行 if-elif"：

```python
# 简化伪码
while True:
    while not panduandiaoyu_found:
        if find(diaoyu): press F; continue
        if find(kaishi): click; continue
        if find(kongbai): click; continue
        if find(panduan): press F; break
    while not (yu1_found and yu2_found):
        if find(yu1): press F; yu1_found = True
        if find(yu2): press F; yu2_found = True
    start_follow(stop_event)
    while True:
        if find(success): result='success'; break
        if find(escape): result='escape'; break
        if timeout: result='escape'; break
```

问题：状态散落、卡死时无法恢复、新增"失败重试""超时停机"必须改主循环。

**WWA 模式**（`page_event_service.py`）是"页面驱动 + 条件动作"：

```python
# 简化伪码
def execute(...):
    src_img = capture()
    img = resize(src_img)
    ocr_results = ocr(img)
    for page in self.get_pages():           # 大约 30+ Page 定义
        if page.is_match(src_img, img, ocr_results):
            page.action(page.matchPositions)
    for cond in self.get_conditional_actions():
        if cond():                          # 条件谓词
            cond.action()                   # 动作
```

每个 `Page` 是 Pydantic 模型，含 `name + screenshot + targetTexts(正则) + action`，循环里"看到什么就做什么"，与执行顺序无关。

### 4.2 NTE 状态机化方案

为 NTE 设计一个**轻量状态机框架**（不必照搬 WWA 1332 行的 pages.py 那么重），分两层：

#### 层 1：`PageRule`（无状态，对应 WWA `Page`）

```python
# nte_assistant/core/page.py
from dataclasses import dataclass, field
from typing import Callable

@dataclass(frozen=True)
class Detector:
    """识别器抽象，子类实现 detect(frame)->matchInfo|None"""
    def detect(self, frame, ctx) -> "MatchInfo | None":
        raise NotImplementedError

@dataclass(frozen=True)
class TemplateDetector(Detector):
    template_path: str
    threshold: float = 0.85
    region_rate: tuple[float, float, float, float] | None = None
    colorspace: str = "gray"

@dataclass(frozen=True)
class OcrDetector(Detector):
    text: str  # 正则
    region_rate: tuple[float, float, float, float] | None = None

@dataclass(frozen=True)
class ColorDetector(Detector):
    points: tuple[tuple[int, int], ...]
    colors: tuple[tuple[int, int, int], ...]
    tolerance: int = 30

@dataclass(frozen=True)
class PageRule:
    name: str
    detectors: tuple[Detector, ...]              # 多个 detector，要求全部命中（AND）
    action: Callable[["PageContext"], "StepResult"]
    cooldown_ms: int = 0                         # 同 page 触发后冷却
    requires_state: str | None = None            # 仅在某状态下生效（可选）
```

#### 层 2：`StateMachine`（有状态，对应 WWA `BossTaskContext`）

```python
# nte_assistant/core/state_machine.py
from dataclasses import dataclass

@dataclass
class TaskContext:
    state: str = "idle"
    fish_count: int = 0
    last_fired: dict[str, float] = None       # page_name → ts
    consecutive_failures: int = 0

class StateMachine:
    def __init__(self, rules: list[PageRule], context: TaskContext,
                 capture, vision, input_gw, audit):
        self._rules = rules
        self._ctx = context
        self._capture = capture
        self._vision = vision
        self._input = input_gw
        self._audit = audit

    def step(self) -> StepResult:
        frame = self._capture.grab()
        for rule in self._rules:
            if rule.requires_state and rule.requires_state != self._ctx.state:
                continue
            if not self._cooldown_ok(rule):
                continue
            matches = [d.detect(frame, self._vision) for d in rule.detectors]
            if not all(matches):
                continue
            self._mark_fired(rule)
            return rule.action(PageContext(frame=frame, matches=matches,
                                            input=self._input, ctx=self._ctx))
        return StepResult.continue_()

    def run(self, stop_event):
        while not stop_event.is_set():
            res = self.step()
            if res.status == "stop":
                return
            time.sleep(res.next_delay_ms / 1000.0)
```

#### NTE 钓鱼用 `PageRule` 重写

```python
# nte_assistant/services/fishing/rules.py
FISHING_RULES = [
    # 状态：idle → 看到「钓鱼」F 提示，按 F 进入
    PageRule(
        name="enter_fishing_F",
        detectors=(TemplateDetector("diaoyu.png", threshold=0.7),),
        action=lambda c: (
            c.input.tap_key(c.ctx.hwnd, "F", reason="enter_fishing"),
            c.ctx.transition("idle", "casting"),
            StepResult.continue_(next_delay_ms=200),
        )[-1],
        requires_state="idle",
        cooldown_ms=500,
    ),
    # 状态：casting → 看到「开始钓鱼」按钮，点击
    PageRule(
        name="start_cast",
        detectors=(TemplateDetector("kaishidiaoyu.png"),),
        action=lambda c: (
            c.input.click(c.ctx.hwnd, *c.center(), reason="start_cast"),
            c.ctx.transition("casting", "waiting_bite"),
            StepResult.continue_(next_delay_ms=500),
        )[-1],
        requires_state="casting",
    ),
    # 状态：waiting_bite → 上钩颜色出现，按 F
    PageRule(
        name="hook_F",
        detectors=(ColorDetector(  # 用 ColorChecker 替代 panduandiaoyu.png
            points=((640, 540), (640, 545)),
            colors=((0, 215, 255),),
            tolerance=25,
        ),),
        action=lambda c: (
            c.input.tap_key(c.ctx.hwnd, "F"),
            c.ctx.transition("waiting_bite", "tracking"),
            StepResult.continue_(),
        )[-1],
        requires_state="waiting_bite",
    ),
    # 状态：tracking → 启动 control_worker（单独线程）
    # ...
    # 状态：tracking → 看到「成功」（OCR 识别 "钓鱼成功"），结算
    PageRule(
        name="result_success",
        detectors=(OcrDetector(text=r"钓鱼成功|捕获", region_rate=(0.3, 0.4, 0.7, 0.6)),),
        action=lambda c: (
            c.input.click(c.ctx.hwnd, *c.center(), reason="claim_fish"),
            setattr(c.ctx, "fish_count", c.ctx.fish_count + 1),
            c.ctx.transition("tracking", "idle"),
            StepResult.continue_(next_delay_ms=1000),
        )[-1],
        requires_state="tracking",
    ),
    # 兜底超时
    PageRule(
        name="result_timeout",
        detectors=(TimeoutDetector(seconds=15, since="state_change"),),
        action=lambda c: (
            c.input.release_all(c.ctx.hwnd),
            c.ctx.transition("tracking", "idle"),
            StepResult.continue_(next_delay_ms=3000),
        )[-1],
        requires_state="tracking",
    ),
]
```

**收益**：
- 任意阶段卡死，状态机会持续重新匹配 → 自然恢复；
- 加新阶段只需 append `PageRule`，不改主循环；
- 每条规则可独立写单元测试（feed PNG，断言触发的 action）；
- `requires_state` 让规则之间互不干扰。

### 4.3 全局事件 / KillSwitch

NTE 现有 `pynput` F12 全局热键 → 统一接入 `SafetyController`：

```python
# nte_assistant/safety_runtime/kill_switch.py
class KillSwitch:
    def __init__(self):
        self._event = threading.Event()
        self._listeners: list[Callable] = []

    def trigger(self, reason: str):
        logger.warning("KillSwitch triggered: %s", reason)
        self._event.set()
        for cb in self._listeners:
            try: cb()
            except Exception: pass

    def is_set(self): return self._event.is_set()
    def add_listener(self, cb): self._listeners.append(cb)

# 初始化
kill = KillSwitch()
kill.add_listener(lambda: input_gateway.release_all_for_all_hwnds())
pynput.keyboard.GlobalHotKeys({'<f12>': lambda: kill.trigger("user_F12")}).start()
```

每个状态机的 step 循环都检查 `kill.is_set()`；`InputGateway` 内部也检查，被设置后所有调用直接 no-op。

---

## 5. 具体功能实现方案

### 5.1 钓鱼自动化（端到端重构示例）

把 §3 / §4 的所有改造汇总到一个完整文件结构：

```
nte_assistant/services/fishing/
├── __init__.py
├── service.py        # FishingService（顶层任务）
├── rules.py          # FISHING_RULES = [PageRule, ...]
├── tracker.py        # 钓鱼条追踪器（基于 v2 的 WGC + HSV，封装为 Service）
└── config.py         # FishingConfig（Pydantic）
```

#### `config.py`：替换全局常量

```python
from pydantic import BaseModel, Field

class FishingConfig(BaseModel):
    # 原 controlfishing_v2.py 全局常量全部入这里
    roi: tuple[int, int, int, int] = (597, 61, 1328, 85)  # 1920×1080 基准
    green_hsv_lower: tuple[int, int, int] = (60, 100, 150)
    green_hsv_upper: tuple[int, int, int] = (90, 255, 255)
    yellow_match_thresh: float = Field(0.6, ge=0.0, le=1.0)
    green_buffer_pct: float = Field(0.25, ge=0.0, le=0.5)
    pulse_scale: float = 0.002
    pulse_min_ms: int = Field(5, ge=1, le=200)
    pulse_max_ms: int = Field(40, ge=5, le=500)
    inter_pulse_sleep_ms: int = 10
    first_frame_timeout_s: float = 1.0
    # 安全上限
    max_session_minutes: int = Field(60, ge=1, le=120)
    max_consecutive_failures: int = 5
```

#### `tracker.py`：保留 WGC，加入安全限流

```python
class FishingTracker:
    """对应 controlfishing_v2.CaptureWorker + control_worker"""
    def __init__(self, capture_gw, input_gw, cfg: FishingConfig, kill_switch):
        self._capture = capture_gw
        self._input = input_gw
        self._cfg = cfg
        self._kill = kill_switch
        self._queue = queue.Queue(maxsize=1)

    def start(self, hwnd, stop_event):
        # 1. 启动 WGC（直接复用 controlfishing_v2 的 CaptureWorker）
        capture = WgcCaptureSession(hwnd, on_frame=self._on_frame, stop_event=stop_event)
        capture.start()
        # 2. 启动控制线程
        threading.Thread(target=self._control_loop,
                         args=(hwnd, stop_event), daemon=True,
                         name="fishing-tracker").start()

    def _on_frame(self, frame_bgr):
        green = detect_green_zone(frame_bgr, self._cfg)  # NTE 已实现
        yellow_x = detect_yellow_marker(frame_bgr, self._template_hs, self._cfg)
        if green and yellow_x is not None:
            try: self._queue.put_nowait((yellow_x, *green))
            except queue.Full:
                self._queue.get_nowait()
                self._queue.put_nowait((yellow_x, *green))

    def _control_loop(self, hwnd, stop_event):
        while not stop_event.is_set() and not self._kill.is_set():
            try:
                yellow_x, gl, gr = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            buf = int((gr - gl) * self._cfg.green_buffer_pct)
            tl, tr = gl + buf, gr - buf
            if tl <= yellow_x <= tr:
                self._input.release_all(hwnd)
            elif yellow_x < tl:
                pulse_ms = self._scale_pulse(tl - yellow_x)
                with self._input.held_key(hwnd, "D", reason="fish_right"):
                    time.sleep(pulse_ms / 1000.0)
                time.sleep(self._cfg.inter_pulse_sleep_ms / 1000.0)
            else:
                pulse_ms = self._scale_pulse(yellow_x - tr)
                with self._input.held_key(hwnd, "A", reason="fish_left"):
                    time.sleep(pulse_ms / 1000.0)
                time.sleep(self._cfg.inter_pulse_sleep_ms / 1000.0)
        self._input.release_all(hwnd)  # 双保险
```

#### `service.py`：组合 PageRule 与 Tracker

```python
class FishingService:
    def __init__(self, hwnd, capture_gw, vision, input_gw, cfg, kill_switch, audit):
        self._hwnd = hwnd
        self._ctx = TaskContext(state="idle", hwnd=hwnd)
        self._sm = StateMachine(FISHING_RULES, self._ctx,
                                capture_gw, vision, input_gw, audit)
        self._tracker = FishingTracker(capture_gw, input_gw, cfg, kill_switch)
        self._kill = kill_switch
        self._cfg = cfg

    def run(self, stop_event):
        session_deadline = time.monotonic() + self._cfg.max_session_minutes * 60
        # 钓鱼条追踪 (tracking 状态时启动)
        tracker_stop = threading.Event()
        # 把 PageRule 中"transition('waiting_bite','tracking')"动作里启动 tracker：
        self._ctx.on_state_change("tracking",
            lambda: self._tracker.start(self._hwnd, tracker_stop))
        self._ctx.on_state_change("idle",
            lambda: tracker_stop.set())
        try:
            while not stop_event.is_set() and not self._kill.is_set():
                if time.monotonic() > session_deadline:
                    self._kill.trigger("max_session_exceeded")
                    break
                if self._ctx.consecutive_failures >= self._cfg.max_consecutive_failures:
                    self._kill.trigger("too_many_failures")
                    break
                self._sm.step()
        finally:
            tracker_stop.set()
            self._input_gw.release_all(self._hwnd)
```

### 5.2 任务/剧情自动化（轻量 Page 表）

NTE 当前 `TEMPLATES_CONFIG` 13 行三元组 → 升级为 `PAGE_RULES` 列表（每条带 region/threshold/cooldown）：

```python
# nte_assistant/services/story/rules.py
STORY_RULES = [
    PageRule(
        name="skip_arrow",
        detectors=(TemplateDetector("跳过箭头.png", threshold=0.85),),
        action=lambda c: (c.input.click(c.ctx.hwnd, *c.center()), StepResult.continue_(50))[-1],
        cooldown_ms=300,
    ),
    PageRule(
        name="confirm_btn",
        # OCR 优先：如果 OCR 起来了，文字识别比模板更稳
        detectors=(OcrDetector(text=r"^确认$", region_rate=(0.6, 0.7, 1.0, 1.0)),),
        action=lambda c: (c.input.click(c.ctx.hwnd, *c.center()), StepResult.continue_(50))[-1],
        cooldown_ms=300,
    ),
    PageRule(
        name="esc_cant_skip",
        detectors=(TemplateDetector("不可跳过.png", threshold=0.9),),
        action=lambda c: (c.input.click(c.ctx.hwnd, c.ctx.client_w//2, c.ctx.client_h//2),
                          StepResult.continue_(100))[-1],
    ),
    PageRule(
        name="press_F_investigate",
        detectors=(TemplateDetector("调查F.png"),
                   # 双 detector：模板 + OCR，AND 逻辑提升精度
                   OcrDetector(text=r"^F$", region_rate=(0.4, 0.4, 0.6, 0.6))),
        action=lambda c: (c.input.tap_key(c.ctx.hwnd, "F"), StepResult.continue_(100))[-1],
    ),
    # ... 13 条 NTE 现有 TEMPLATES_CONFIG 全部迁移
]
```

**与 WWA `page_event_service.py` 的差距**：WWA 用 `Page + TextMatch + DynamicPosition` 完整定义，并支持多语言 i18n；NTE 暂不需要多语言，简化版 PageRule 已经够用。后续如需多语言，按 WWA 同款扩展即可。

### 5.3 UI 升级：PyQt5 → PySide6 + Fluent

#### 选型
- **PySide6**（LGPL，与 WWA 对齐，许可证更自由）
- **`pyside6-fluent-widgets[full]==1.7.6`**（与 WWA 对齐，FluentUI 风格）

#### 迁移要点

| 项 | PyQt5 | PySide6 |
|---|---|---|
| 信号 | `pyqtSignal` | `Signal`（`from PySide6.QtCore import Signal`） |
| 槽 | `pyqtSlot` | `Slot` |
| `QApplication.exec_()` | 旧 | `app.exec()` |
| 高 DPI | `Qt.AA_EnableHighDpiScaling`（必须在 QApp 前） | PySide6 默认开启 |
| `QtWidgets.QDesktopWidget` | 旧 | `QGuiApplication.primaryScreen().availableGeometry()` |
| `event.globalPos()` | 旧 | `event.globalPosition().toPoint()` |
| `enum` | `Qt.WindowStaysOnTopHint` | `Qt.WindowType.WindowStaysOnTopHint`（Python 3.11+ 严格枚举） |

#### 文件级迁移清单

| NTE 文件 | 迁移操作 |
|---|---|
| `main.py` | `from PySide6.QtWidgets import QApplication`；`app.exec()` |
| `ui.py` | `QMainWindow / QTabWidget / QPushButton / QTextEdit` 全部改为 PySide6 import；`pyqtSignal → Signal` |
| `floating_log.py` | 同上；`event.globalPos() → event.globalPosition().toPoint()` |
| `automation_thread.py` | `QThread + pyqtSignal` → `QThread + Signal`，**或**改用 `multiprocessing.Process`（推荐，与 WWA 对齐） |

#### 引入 Fluent Widgets

```python
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon, PushButton, MessageBox

class NteMainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.story_iface = StoryInterface(self)
        self.fishing_iface = FishingInterface(self)
        self.combat_iface = CombatInterface(self)
        # ...
        self.addSubInterface(self.story_iface, FluentIcon.ROBOT, "快速剧情")
        self.addSubInterface(self.fishing_iface, FluentIcon.GAME, "AI 钓鱼")
        # ...
```

NTE 当前的"霓虹深色"自定义 QSS 可丢掉，Fluent 默认更专业。

### 5.4 自动战斗（Phase 6 占位 MVP）

完全不照搬 WWA 16 角色枚举。NTE 第一版只做"识别即停"：

```python
# nte_assistant/services/combat/mvp_service.py
class CombatMvpService:
    """阶段 1：只识别，不输入"""
    def __init__(self, capture, vision, audit):
        self._rules = [
            # 检测到 "战斗开始"
            PageRule(name="combat_started",
                     detectors=(OcrDetector(text=r"战斗开始|Combat Begin"),),
                     action=lambda c: (audit.log("combat_detected"),
                                       StepResult.continue_())[-1]),
            # 检测到血条空了
            PageRule(name="hp_critical",
                     detectors=(ColorDetector(
                         points=((100, 660),),  # 自己血条右端
                         colors=((20, 20, 200),),  # 红色
                         tolerance=30),),
                     action=lambda c: StepResult.stop("hp_critical")),
        ]
```

第二版再加"低频辅助"（自动拾取、自动喝药）；第三版才做"受限连招"（参考 WWA `BaseCombo.combo_action` 的 `[(key, press, wait), ...]` DSL）。

---

## 6. 项目结构建议

参考 `nte_security_framework.md §3.3` 并结合本指南实施细节：

```
nte_assistant/
├── pyproject.toml                  # Poetry，含 [tool.poetry.extras] cpu/dml/cu118
├── poetry.lock
├── README.md
├── CHANGELOG.md
├── SECURITY.md                     # 红线清单
├── config.yaml                     # 用户配置
├── version.txt
├── main.py                         # = WWA main.py（仅 application.run()）
│
├── nte_assistant/
│   ├── __init__.py                 # __version__
│   ├── application.py              # 装配 Container + 启动 GUI
│   │
│   ├── core/                       # 业务模型与协议（Protocol/ABC）
│   │   ├── __init__.py
│   │   ├── geometry.py             # Rect / Point / Scaler / DynamicPointTransformer
│   │   ├── window.py               # WindowGateway Protocol
│   │   ├── capture.py              # CaptureGateway Protocol + Frame dataclass
│   │   ├── input.py                # InputGateway Protocol + MouseButton enum
│   │   ├── vision.py               # OcrService / TemplateMatcher / ColorChecker / OdService 协议
│   │   ├── page.py                 # PageRule / Detector / MatchInfo
│   │   ├── state_machine.py       # StateMachine / TaskContext / StepResult
│   │   └── exceptions.py           # KillSwitchActivated / WindowLostError
│   │
│   ├── safety_runtime/             # 跨切面安全（不可被业务 import 绕过）
│   │   ├── __init__.py
│   │   ├── consent.py              # ConsentGate（首次会话用户授权）
│   │   ├── rate_limiter.py         # RateLimiter（events/s, events/min）
│   │   ├── session_budget.py       # SessionBudget（max_session_minutes）
│   │   ├── watchdog.py             # 失焦/无新帧/识别失败计数
│   │   ├── kill_switch.py          # KillSwitch（F12 + 自动触发）
│   │   ├── foreground_guard.py     # 窗口指纹校验
│   │   └── audit_logger.py         # JSONL 脱敏审计
│   │
│   ├── platform_adapters/          # 唯一允许 import OS API 的层
│   │   ├── __init__.py
│   │   ├── win32_window.py         # 抄 WWA src/util/hwnd_util.py
│   │   ├── postmessage_input.py    # 抄 WWA src/util/keymouse_util.py + 限流包装
│   │   ├── printwindow_capture.py  # 抄 WWA src/util/screenshot_util.py
│   │   ├── wgc_capture.py          # 保留 NTE controlfishing_v2 的 WGC + DWM crop
│   │   └── mss_capture.py          # 兜底
│   │
│   ├── vision_impls/               # 视觉服务实现
│   │   ├── __init__.py
│   │   ├── template_matcher.py
│   │   ├── color_checker.py        # 抄 WWA combat_core.ColorChecker
│   │   ├── hsv_detector.py
│   │   └── rapidocr_service.py     # 抄 WWA src/service/ocr_service.py
│   │
│   ├── services/                   # 业务任务（仅依赖 core/safety_runtime）
│   │   ├── __init__.py
│   │   ├── fishing/
│   │   │   ├── service.py
│   │   │   ├── tracker.py
│   │   │   ├── rules.py
│   │   │   └── config.py
│   │   ├── story/
│   │   │   ├── service.py
│   │   │   ├── rules.py
│   │   │   └── config.py
│   │   ├── combat/                 # MVP 占位
│   │   │   └── mvp_service.py
│   │   └── exchange_codes/         # 兑换码（NTE 现有功能）
│   │       └── service.py
│   │
│   ├── controller/
│   │   ├── main_controller.py      # 任务调度（multiprocessing.Process）
│   │   └── task_monitor.py         # 抄 WWA TaskMonitor 思路
│   │
│   ├── gui/
│   │   ├── main_window.py          # FluentWindow + 各 SubInterface
│   │   ├── interfaces/
│   │   │   ├── story_interface.py
│   │   │   ├── fishing_interface.py
│   │   │   ├── combat_interface.py
│   │   │   ├── exchange_interface.py
│   │   │   └── settings_interface.py
│   │   └── widgets/
│   │       └── floating_log.py     # PyQt5 → PySide6 迁移版
│   │
│   ├── config/
│   │   ├── schema.py               # Pydantic v2：AppConfig, FishingConfig, StoryConfig, SafetyConfig
│   │   ├── loader.py               # config.yaml + 环境变量
│   │   └── logging_config.py       # 抄 WWA
│   │
│   └── di/
│       └── container.py            # dependency_injector.Container
│
├── assets/
│   ├── images/                     # 剧情模板（原 NTE images/）
│   ├── fishingimages/              # 钓鱼模板（原 NTE fishingimages/）
│   ├── icons/                      # ico/png
│   └── models/                     # ONNX（Phase 6）
│
├── tools/                          # 开发态独立工具，不进运行时
│   ├── roi_debugger.py             # 保留 NTE 的实时 ROI 调试器（升级 PySide6）
│   └── roi_check.py                # 静态 ROI 截图
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_color_checker.py
    │   ├── test_template_matcher.py
    │   ├── test_state_machine.py
    │   └── test_rate_limiter.py
    ├── integration/
    │   └── test_fishing_rules.py   # feed PNG 序列，断言状态迁移
    └── fixtures/
        └── screenshots/            # 录制好的游戏画面
```

**模块边界规则（CI 强制）**：

```
services/ 不允许 import:
  - pyautogui, pydirectinput, pynput
  - pygetwindow, win32gui, win32api, win32con, win32process
  - PIL.ImageGrab
  - ctypes.windll
  - windows_capture
只允许通过 InputGateway/CaptureGateway/WindowGateway 调用上述能力。
```

可在 `pyproject.toml` 加 ruff 规则：

```toml
[tool.ruff.lint.per-file-ignores]
# platform_adapters 是唯一允许使用底层 API 的地方
"nte_assistant/platform_adapters/*" = []
"nte_assistant/services/*" = ["TID251"]  # 自定义禁用 import 列表
```

---

## 7. 分步实施计划

按优先级和依赖关系排序。每个 Phase 都有"必做（M）"和"可选（O）"。

### Phase 0：脚手架（半天）

- M：`poetry init` + 加依赖（`pydantic`, `dependency-injector`, `pywin32`, `numpy==1.26.4`, `opencv-python>=4.11`, `windows-capture>=1.4`, `psutil>=7`, `pyside6>=6.8`, `qfluentwidgets`）
- M：建立目录骨架（§6 全部空目录 + `__init__.py`）
- M：`ruff` + `mypy` + `bandit` 配置（CI 不强制，本地 pre-commit）
- M：`SECURITY.md` 抄 `nte_security_framework.md §6` 红线清单

**验收**：`poetry install && python -c "import nte_assistant"` 成功。

### Phase 1：Safety Runtime + Platform Adapters（3~5 天）

- M：抄 `keymouse_util.py` → `platform_adapters/postmessage_input.py`
- M：抄 `screenshot_util.py` → `platform_adapters/printwindow_capture.py`
- M：抄 `hwnd_util.py` → `platform_adapters/win32_window.py`，**改窗口类名/标题为异环**（实测：可能仍是 `UnrealWindow` + `"异环"`，用 `roi_debugger.py` 验证）
- M：搬 NTE `controlfishing_v2.CaptureWorker` → `platform_adapters/wgc_capture.py`，去掉全局 `detection_queue`
- M：实现 `safety_runtime/{rate_limiter, kill_switch, audit_logger, foreground_guard}.py`
- M：定义 `core/{window, capture, input}.py` Protocol
- M：实现 `vision_impls/color_checker.py`（抄 WWA）、`template_matcher.py`（升级版，§2.2）

**验收**：
- 单元测试：`tap_key` 注入 1000 次/秒，`rate_limiter` 限制下发数 ≤ 8/s
- KillSwitch 触发后 200ms 内 `release_all` 完成
- 异环窗口指纹 4 元组校验（hwnd+pid+exe+class），同名假窗口被拒

### Phase 2：视觉网关（2~3 天）

- M：抄 `rapidocr_util.py` + `ocr_service.py` → `vision_impls/rapidocr_service.py`
- M：跑 `RapidOCR` warmup（首次启动慢 ~3s，warmup 后 150ms/张）
- O：测试 GPU/DML provider 切换

**验收**：feed `assets/screenshots/dialogue_001.png`，OCR 命中 `r"跳过|Skip"` 文本框，置信度 > 0.8。

### Phase 3：钓鱼服务重构（3~5 天）

- M：实现 `services/fishing/{service, tracker, rules, config}.py`
- M：把 `controlfishing_v2.control_worker` 的逻辑搬到 `tracker.py`，改用 `InputGateway.held_key`
- M：把 `fishing.fish_logic` 的 4 阶段 if-elif 改为 §4.2 的 `FISHING_RULES`
- M：删除 `os.environ["FISHING_TARGET_HWND"]`，改为 `FishingService(hwnd=...)` 构造参数
- M：把 `panduandiaoyu.png` 模板替换为 `ColorChecker`（用 `tools/roi_debugger.py` 实测取色）
- O：把"钓鱼成功/失败"识别从模板改为 OCR

**验收**：
- 连续钓 20 杆，无按键卡死（异常退出后 `release_all` 总能执行）
- 用户切到浏览器写字，钓鱼继续正常进行（PostMessage 后台输入验证）
- `max_session_minutes` 60 分钟到时自动停机
- 连续 5 次失败自动停机

### Phase 4：剧情自动化升级（2~3 天）

- M：实现 `services/story/{service, rules, config}.py`
- M：把 `TEMPLATES_CONFIG` 13 条迁到 `STORY_RULES`，每条配 `region_rate / threshold / cooldown_ms`
- M：高频按钮（"确认/跳过/领取"）加 OCR detector 备份（模板失败时 OCR 兜底）
- M：删除 `automation_thread.AutomationThread`，新建 `controller/main_controller.py` 用 `multiprocessing.Process` 跑 `StoryService`

**验收**：
- 替换异环 1 次客户端版本更新，按钮位置微调，**OCR 自动适应**无需改模板
- 全屏菜单循环跑 30 分钟无误点

### Phase 5：PySide6 + Fluent UI 迁移（2~3 天）

- M：`main.py` / `floating_log.py` / `ui.py` 全部 PyQt5 → PySide6
- M：`NeonMainWindow` → `FluentWindow + SubInterface`
- M：钓鱼 Tab、剧情 Tab、设置 Tab 用 Fluent 重做
- M：`config.yaml` 加载到设置 Tab，可在 GUI 修改并保存

**验收**：UI 启动 < 1s，所有原 Tab 功能可用，无 PyQt5 残留 import。

### Phase 6：扩展能力（按需）

- O：自动战斗 MVP（仅识别 + KillSwitch）
- O：ONNX OD（YOLO）做麻将牌识别（参考 WWA `od_service.py + yolo_util.py`）
- O：CI 出 PyInstaller exe（参考 WWA 便携 Python 方案，避免用户装 Python）
- O：`TaskMonitor` 进程监控 + 崩溃自重启

---

## 8. 文件级移植速查表（Cheat Sheet）

| 想要做的事 | 抄哪个文件 | 改什么 |
|---|---|---|
| 后台按键 | `WWA src/util/keymouse_util.py` | 无需改，直接用 |
| 后台截图 | `WWA src/util/screenshot_util.py` | 无需改 |
| 找游戏窗口句柄 | `WWA src/util/hwnd_util.py` | 改 `WUWA_HWND_CLASS_NAME` / `WUWA_HWND_TITLE` 为异环 |
| OCR | `WWA src/util/rapidocr_util.py` + `src/service/ocr_service.py` | 删除 paddleocr 分支即可 |
| 像素颜色判定 | `WWA src/core/combat/combat_core.py:216-300` (`ColorChecker`) | 仅复制此类与 `LogicEnum / DynamicPointTransformer` |
| 缩放/分辨率适配 | `WWA src/core/regions.py` 的 `DynamicPointTransformer` + `Scaler` | 直接抄 |
| 模板匹配 | `WWA src/service/img_service.py` 的 `match_template` | 加多尺度（§2.2） |
| WGC 高帧率截图 | NTE `controlfishing_v2.py:CaptureWorker` | 拆出 `wgc_capture.py`，实现 `CaptureGateway` 接口 |
| Pydantic 配置 | `WWA src/config/config.py` | 删除 `EchoModel/KeyboardMappingConfig` 鸣潮专属，建 `FishingConfig/StoryConfig/SafetyConfig` |
| DI 容器 | `WWA src/core/injector.py` | 把 `combat_service`, `boss_info_service` 拿掉；运行期探测 RapidOCR 是否安装 |
| 异常释放按键 | `WWA src/core/combat/combat_core.py:BaseCombo.combo_action` 的 `key_down_caches` + `finally` 释放 | 改为 `InputGateway.held_key` 上下文管理器 |

---

## 9. 验证与风险控制

### 9.1 必须做的验证

1. **PostMessage 兼容性**：异环对 `WM_KEYDOWN lParam=0` 是否接收。如不接收，按 WWA 同款补 `MAKELPARAM(repeatCount=1, scanCode=...)`。**验证方法**：用 NTE 现有 `roi_debugger.py` 配合一个简单测试脚本，发 `tap_key("F", 0.05)` 看角色是否拾取。
2. **PrintWindow 是否黑屏**：异环的 UE 渲染模式可能导致 PW_RENDERFULLCONTENT 黑帧。**回退策略**：黑帧检测 → 切 WGC。
3. **ColorChecker 颜色取样**：用 `tools/roi_debugger.py` 在不同光照/天气下取 5 帧像素颜色，建立容差范围。
4. **OCR 识别率**：录制 20 张异环 UI 截图，跑 `RapidOCR`，目标识别率 > 95%。
5. **限流验证**：人为调小 `max_events_per_second=2`，观察钓鱼 A/D 脉冲是否被限速但游戏不受影响。

### 9.2 主要风险与应对

| 风险 | 概率 | 应对 |
|---|---|---|
| 异环 PostMessage 不收 | 中 | 加 lParam 完整字段；最坏退回前台 SendInput（仅"剧情确认"等低频场景） |
| 异环 PrintWindow 黑帧 | 中 | 主路径切 WGC（NTE 已有），PrintWindow 仅做兜底 |
| ColorChecker 颜色随光照漂移 | 低 | 多帧取样建立容差；HSV 备份 |
| OCR 在快速滚动文本上漏字 | 低 | 业务层不依赖完整文本，只匹配关键字正则 |
| `held_key` 异常未释放 | 低 | InputGateway 维护全局 `_held_keys` 集合，KillSwitch 触发时 `release_all_for_all_hwnds` |
| Pydantic v2 与 PySide6 信号交互 | 低 | 用 `@dataclass` 替代 BaseModel 用于信号传输 |

### 9.3 不做的事（红线，重申）

- 不读写异环进程内存
- 不注入 DLL / Hook DirectX
- 不抓改包
- 不隐藏进程 / 伪装签名
- 不抑制 ETW
- 不把截图传云端 OCR

---

## 10. 一句话总结

> **架构骨架 100% 借鉴 WWA**（DI + ABC + Pydantic + multiprocessing + PostMessage + PrintWindow + RapidOCR + ColorChecker + 状态机 + KillSwitch + 限流审计），**业务规则用 NTE 自己的轻量 PageRule 驱动**（不照搬鸣潮专属的角色/BOSS 抽象），**WGC 钓鱼 + 实时 ROI 调试器是 NTE 的优势保留并升级**。整体目标是把 NTE 从"个人脚本"升级为"工业级自动化助手"，同时不引入任何反作弊对抗能力。
