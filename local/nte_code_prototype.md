# NTE-ai v2 架构原型：按 WWA 四层模式重建

> 目标：把 NTE-ai 从“多个脚本 + 大 UI 调度”重构为类似 WWA 的 `Core / Service / Util / UI` 四层架构。本文基于 `wwa_analysis.md`、`nte_analysis.md` 以及 WWA 的 `interface.py / control_service.py / window_service.py / ocr_service.py / hwnd_util.py`，给出可落地的 Python 代码原型。

---

## 1. 设计结论

WWA 的成熟点不是“某个算法更复杂”，而是把能力拆成稳定接口：

- `core/interface.py` 定义抽象能力，业务逻辑只依赖接口。
- `service/*_service.py` 实现窗口、截图、输入、OCR/识别等可替换服务。
- `util/*` 只放 Win32、OpenCV、路径、日志等无状态工具。
- GUI 只负责启动/停止任务、展示日志、收集配置，不直接写自动化循环。

NTE-ai 当前的核心能力是：

1. 快速剧情/任务跳过：模板匹配后点击、按键或中心点击。
2. AI 钓鱼主流程：模板推进状态机 + 启动钓鱼条控制器。
3. 钓鱼条控制：WGC 截图、HSV 绿区检测、模板识别黄标、A/D 短脉冲控制。
4. ROI 调试：实时 WGC 镜像、绘制 ROI/绿区/黄标。
5. UI/热键/日志/自动更新/兑奖码等外围功能。

重构重点：**保留 NTE 已验证的识别逻辑，但把输入、截图、窗口、识别、流程状态机全部服务化**。

---

## 2. 推荐项目结构

```text
nte-ai-v2/
├── src/
│   ├── core/
│   │   ├── interface.py          # ABC 接口定义
│   │   ├── context.py            # 运行上下文 / 配置聚合
│   │   ├── geometry.py           # ROI、点、匹配结果、分辨率缩放
│   │   ├── fishing/
│   │   │   ├── fishing_core.py   # 钓鱼状态机，不直接依赖 pyautogui/pydirectinput
│   │   │   ├── detector.py       # 钓鱼条绿区/黄标识别
│   │   │   └── models.py         # FishingConfig/FishingState/FishingDetection
│   │   └── quest/
│   │       ├── quest_core.py     # 剧情/任务跳过核心
│   │       └── models.py         # TemplateAction/QuestConfig
│   ├── service/
│   │   ├── control_service.py    # PostMessage 输入控制服务
│   │   ├── window_service.py     # 窗口管理服务
│   │   ├── capture_service.py    # PrintWindow 截图服务，可另加 WGC 实现
│   │   ├── ocr_service.py        # OCR/文字识别服务，预留 RapidOCR/PaddleOCR
│   │   ├── recognition_service.py# OpenCV 模板/HSV 识别服务
│   │   └── fishing_service.py    # 钓鱼流程服务，封装线程与生命周期
│   ├── util/
│   │   ├── hwnd_util.py          # 枚举窗口、DPI、客户区、DWM crop
│   │   ├── cv_util.py            # imread 中文路径、模板缓存、颜色工具
│   │   ├── resource_util.py      # PyInstaller/源码路径兼容
│   │   └── log_util.py           # logging 配置
│   └── ui/
│       ├── main_window.py        # 主 UI
│       ├── tabs/
│       │   ├── quest_tab.py
│       │   └── fishing_tab.py
│       └── widgets/floating_log.py
├── assets/
│   ├── images/
│   └── fishingimages/
├── config.yaml
├── main.py
└── tests/
    ├── core/
    ├── service/
    └── fixtures/
```

建议依赖方向固定为：

```text
UI -> service -> core(interface/models) -> util
core 不反向 import UI/service；service 允许调用 util；util 不依赖业务。
```

---

## 3. 核心接口定义代码：`src/core/interface.py`

下面代码可直接保存为 `src/core/interface.py`。它把 NTE 现有的输入、截图、识别能力抽象出来，业务层只依赖这些 ABC。

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class Rect:
    """客户区相对坐标：left, top, right, bottom。"""
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_slice(self) -> tuple[slice, slice]:
        return slice(self.top, self.bottom), slice(self.left, self.right)

    def scale_from(self, base_size: tuple[int, int], target_size: tuple[int, int]) -> "Rect":
        base_w, base_h = base_size
        target_w, target_h = target_size
        sx = target_w / base_w
        sy = target_h / base_h
        return Rect(
            left=int(self.left * sx),
            top=int(self.top * sy),
            right=int(self.right * sx),
            bottom=int(self.bottom * sy),
        )


@dataclass(frozen=True)
class MatchResult:
    ok: bool
    score: float
    center: Point | None = None
    rect: Rect | None = None


@dataclass(frozen=True)
class FishingDetection:
    yellow_x: int
    green_left: int
    green_right: int

    @property
    def green_width(self) -> int:
        return self.green_right - self.green_left


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class WindowService(ABC):
    """窗口发现、客户区与焦点状态。"""

    @property
    @abstractmethod
    def hwnd(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def refresh(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_client_size(self) -> tuple[int, int]:
        raise NotImplementedError

    @abstractmethod
    def get_client_rect_on_screen(self) -> tuple[int, int, int, int]:
        raise NotImplementedError

    @abstractmethod
    def is_foreground(self) -> bool:
        raise NotImplementedError


class ControlService(ABC):
    """输入控制。Core 只调用语义动作，不关心后端是 PostMessage/SendInput/pydirectinput。"""

    @abstractmethod
    def key_down(self, key: str | int) -> None:
        raise NotImplementedError

    @abstractmethod
    def key_up(self, key: str | int) -> None:
        raise NotImplementedError

    @abstractmethod
    def tap_key(self, key: str | int, seconds: float = 0.05) -> None:
        raise NotImplementedError

    @abstractmethod
    def click(self, x: int | None = None, y: int | None = None, button: MouseButton = MouseButton.LEFT,
              seconds: float = 0.03) -> None:
        raise NotImplementedError

    @abstractmethod
    def activate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def release_all(self) -> None:
        raise NotImplementedError


class CaptureService(ABC):
    """截图服务，返回 RGB numpy 数组。"""

    @abstractmethod
    def screenshot(self, region: Rect | None = None) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def screenshot_window(self, hwnd: int) -> np.ndarray:
        raise NotImplementedError


class RecognitionService(ABC):
    """视觉识别服务：模板、HSV、OCR 的统一入口。"""

    @abstractmethod
    def match_template(self, image: np.ndarray, template_path: str | Path, threshold: float) -> MatchResult:
        raise NotImplementedError

    @abstractmethod
    def find_first_template(self, image: np.ndarray, template_paths: Sequence[str | Path],
                            threshold: float) -> tuple[Path, MatchResult] | None:
        raise NotImplementedError

    @abstractmethod
    def detect_green_zone(self, image: np.ndarray, roi: Rect, hsv_lower: np.ndarray,
                          hsv_upper: np.ndarray) -> tuple[int, int] | None:
        raise NotImplementedError

    @abstractmethod
    def detect_yellow_marker(self, image: np.ndarray, roi: Rect, template_path: str | Path,
                             threshold: float) -> int | None:
        raise NotImplementedError


class TaskService(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_running(self) -> bool:
        raise NotImplementedError
```

---

## 4. 输入服务代码：`src/service/control_service.py`

WWA 的输入路径核心是 `win32gui.PostMessage(hwnd, WM_KEYDOWN/UP/WM_LBUTTONDOWN/UP, ...)`。NTE v2 可先用 PostMessage 统一替代散落的 `pyautogui` 与 `pydirectinput`，以后再按配置替换后端。

```python
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

import win32api
import win32con
import win32gui

from src.core.interface import ControlService, MouseButton, WindowService

logger = logging.getLogger(__name__)

VK_MAP: dict[str, int] = {
    "A": ord("A"), "B": ord("B"), "C": ord("C"), "D": ord("D"),
    "E": ord("E"), "F": ord("F"), "Q": ord("Q"), "R": ord("R"),
    "S": ord("S"), "W": ord("W"), "X": ord("X"), "Z": ord("Z"),
    "0": ord("0"), "1": ord("1"), "2": ord("2"), "3": ord("3"),
    "ESC": win32con.VK_ESCAPE,
    "ENTER": win32con.VK_RETURN,
    "SPACE": win32con.VK_SPACE,
    "SHIFT": win32con.VK_SHIFT,
    "LEFT_SHIFT": win32con.VK_LSHIFT,
    "F12": win32con.VK_F12,
}


def _vk(key: str | int) -> int:
    if isinstance(key, int):
        return key
    key = key.upper()
    if len(key) == 1:
        return ord(key)
    if key not in VK_MAP:
        raise KeyError(f"unsupported key: {key}")
    return VK_MAP[key]


def _key_lparam(vk: int, is_up: bool = False) -> int:
    scan = win32api.MapVirtualKey(vk, 0)
    lparam = 1 | (scan << 16)
    if is_up:
        lparam |= (1 << 30) | (1 << 31)
    return lparam


def _mouse_lparam(x: int, y: int) -> int:
    return win32api.MAKELONG(int(x), int(y))


@dataclass
class PostMessageControlService(ControlService):
    window_service: WindowService
    humanize_ms: tuple[float, float] = (0.0, 0.010)
    _pressed: set[int] = field(default_factory=set)

    @property
    def hwnd(self) -> int:
        return self.window_service.hwnd

    def _sleep(self, seconds: float) -> None:
        jitter = random.uniform(*self.humanize_ms)
        time.sleep(max(0.0, seconds + jitter))

    def activate(self) -> None:
        win32gui.PostMessage(self.hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
        self._sleep(0.03)

    def key_down(self, key: str | int) -> None:
        vk = _vk(key)
        win32gui.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk, _key_lparam(vk, is_up=False))
        self._pressed.add(vk)

    def key_up(self, key: str | int) -> None:
        vk = _vk(key)
        win32gui.PostMessage(self.hwnd, win32con.WM_KEYUP, vk, _key_lparam(vk, is_up=True))
        self._pressed.discard(vk)

    def tap_key(self, key: str | int, seconds: float = 0.05) -> None:
        self.key_down(key)
        self._sleep(seconds)
        self.key_up(key)

    def click(self, x: int | None = None, y: int | None = None,
              button: MouseButton = MouseButton.LEFT, seconds: float = 0.03) -> None:
        if x is None or y is None:
            w, h = self.window_service.get_client_size()
            x, y = w // 2, h // 2

        if button == MouseButton.LEFT:
            down_msg, up_msg, flag = win32con.WM_LBUTTONDOWN, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON
        elif button == MouseButton.RIGHT:
            down_msg, up_msg, flag = win32con.WM_RBUTTONDOWN, win32con.WM_RBUTTONUP, win32con.MK_RBUTTON
        else:
            down_msg, up_msg, flag = win32con.WM_MBUTTONDOWN, win32con.WM_MBUTTONUP, win32con.MK_MBUTTON

        lparam = _mouse_lparam(x, y)
        win32gui.PostMessage(self.hwnd, down_msg, flag, lparam)
        self._sleep(seconds)
        win32gui.PostMessage(self.hwnd, up_msg, 0, lparam)

    def release_all(self) -> None:
        for vk in list(self._pressed):
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_KEYUP, vk, _key_lparam(vk, is_up=True))
            except Exception:
                logger.exception("failed to release key: %s", vk)
            finally:
                self._pressed.discard(vk)
```

关键点：

- Core 层只调用 `control.tap_key("F")`、`control.click(x, y)`、`control.key_down("A")`。
- 按键释放集中在 `release_all()`，避免钓鱼异常后 A/D 卡住。
- 人类化抖动集中在服务层，剧情、钓鱼、任务模块统一受益。

---

## 5. 截图服务代码：`src/service/capture_service.py`

WWA 默认后台截图是 `GetWindowDC + CreateCompatibleBitmap + PrintWindow(hwnd, dc, 3)`。NTE v2 可把它作为通用截图后端；WGC 可作为高帧率钓鱼条专用后端继续保留。

```python
from __future__ import annotations

import ctypes
import logging

import cv2
import numpy as np
import win32con
import win32gui
import win32ui

from src.core.interface import CaptureService, Rect, WindowService

logger = logging.getLogger(__name__)
PW_RENDERFULLCONTENT = 0x00000002


class PrintWindowCaptureService(CaptureService):
    def __init__(self, window_service: WindowService):
        self.window_service = window_service

    def screenshot(self, region: Rect | None = None) -> np.ndarray:
        img = self.screenshot_window(self.window_service.hwnd)
        if region is not None:
            img = img[region.as_slice()]
        return img

    def screenshot_window(self, hwnd: int) -> np.ndarray:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise RuntimeError(f"invalid client size: {width}x{height}")

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        try:
            # 3 = PW_CLIENTONLY | PW_RENDERFULLCONTENT，在很多 UE 窗口下比 BitBlt 稳定。
            ok = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)
            if ok != 1:
                logger.warning("PrintWindow returned %s, hwnd=%s", ok, hwnd)

            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            return np.ascontiguousarray(img)
        finally:
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
```

如果 NTE 的钓鱼条必须继续使用 `windows-capture`，建议新增 `WGCCaptureService`，但仍实现同一个 `CaptureService` 或暴露 `subscribe_frames(callback)`，不要让 `fishing_core.py` 直接 import `WindowsCapture`。

---

## 6. 识别服务原型：`src/service/recognition_service.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from src.core.interface import MatchResult, Point, RecognitionService, Rect


class OpenCVRecognitionService(RecognitionService):
    def __init__(self):
        self._template_cache: dict[Path, np.ndarray] = {}

    def _read_template(self, path: str | Path, grayscale: bool = True) -> np.ndarray:
        p = Path(path)
        if p not in self._template_cache:
            flags = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
            data = np.fromfile(str(p), dtype=np.uint8)
            img = cv2.imdecode(data, flags)
            if img is None:
                raise FileNotFoundError(f"template not found or invalid: {p}")
            self._template_cache[p] = img
        return self._template_cache[p]

    def match_template(self, image: np.ndarray, template_path: str | Path, threshold: float) -> MatchResult:
        template = self._read_template(template_path, grayscale=True)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image
        if gray.shape[0] < template.shape[0] or gray.shape[1] < template.shape[1]:
            return MatchResult(ok=False, score=0.0)
        res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        h, w = template.shape[:2]
        rect = Rect(max_loc[0], max_loc[1], max_loc[0] + w, max_loc[1] + h)
        center = Point(max_loc[0] + w // 2, max_loc[1] + h // 2)
        return MatchResult(ok=max_val >= threshold, score=float(max_val), center=center, rect=rect)

    def find_first_template(self, image: np.ndarray, template_paths: Sequence[str | Path],
                            threshold: float) -> tuple[Path, MatchResult] | None:
        for path in template_paths:
            result = self.match_template(image, path, threshold)
            if result.ok:
                return Path(path), result
        return None

    def detect_green_zone(self, image: np.ndarray, roi: Rect, hsv_lower: np.ndarray,
                          hsv_upper: np.ndarray) -> tuple[int, int] | None:
        roi_img = image[roi.as_slice()]
        if roi_img.size == 0:
            return None
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
        cols = np.any(mask > 0, axis=0)
        indices = np.where(cols)[0]
        if len(indices) == 0:
            return None
        return int(indices[0] + roi.left), int(indices[-1] + roi.left)

    def detect_yellow_marker(self, image: np.ndarray, roi: Rect, template_path: str | Path,
                             threshold: float) -> int | None:
        roi_img = image[roi.as_slice()]
        match = self.match_template(roi_img, template_path, threshold)
        if not match.ok or match.center is None:
            return None
        return roi.left + match.center.x
```

---

## 7. 钓鱼核心代码：`src/core/fishing/fishing_core.py`

下面是把 `fishing.py + controlfishing_v2.py` 重写成 Core 状态机的示例。它不依赖 PyQt、环境变量、pydirectinput，也不自己截图；这些全部从 service 注入。

```python
from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import numpy as np

from src.core.interface import CaptureService, ControlService, FishingDetection, RecognitionService, Rect

logger = logging.getLogger(__name__)


class FishingState(Enum):
    SEARCH_ENTRY = auto()
    CONFIRM_FISH = auto()
    FOLLOW_BAR = auto()
    WAIT_RESULT = auto()
    SUCCESS = auto()
    FAILED = auto()
    STOPPED = auto()


@dataclass(frozen=True)
class FishingConfig:
    asset_dir: Path
    match_threshold: float = 0.70
    yellow_threshold: float = 0.60
    base_size: tuple[int, int] = (1920, 1080)
    bar_roi: Rect = Rect(597, 61, 1328, 85)
    green_hsv_lower: tuple[int, int, int] = (60, 100, 150)
    green_hsv_upper: tuple[int, int, int] = (90, 255, 255)
    green_buffer_pct: float = 0.25
    pulse_scale: float = 0.002
    pulse_min: float = 0.005
    pulse_max: float = 0.040
    loop_interval: float = 0.05
    result_timeout: float = 15.0

    def template(self, name: str) -> Path:
        return self.asset_dir / name


class FishingCore:
    def __init__(self, capture: CaptureService, recognition: RecognitionService,
                 control: ControlService, config: FishingConfig):
        self.capture = capture
        self.recognition = recognition
        self.control = control
        self.config = config
        self.state = FishingState.SEARCH_ENTRY
        self.fish_count = 0

    def run_once(self, stop_event: threading.Event) -> bool:
        try:
            self.state = FishingState.SEARCH_ENTRY
            if not self._search_entry(stop_event):
                return False
            self.state = FishingState.CONFIRM_FISH
            if not self._confirm_fish(stop_event):
                return False
            self.state = FishingState.FOLLOW_BAR
            return self._follow_and_wait_result(stop_event)
        finally:
            self.control.release_all()

    def _search_entry(self, stop_event: threading.Event) -> bool:
        actions = [
            ("diaoyu.png", "key", "F"),
            ("kaishidiaoyu.png", "click", None),
            ("dianjikongbai.png", "click", None),
            ("panduandiaoyu.png", "key_break", "F"),
        ]
        last_log = time.monotonic()
        while not stop_event.is_set():
            frame = self.capture.screenshot()
            for filename, action, key in actions:
                result = self.recognition.match_template(frame, self.config.template(filename), self.config.match_threshold)
                if not result.ok:
                    continue
                logger.info("fishing entry matched %s score=%.3f", filename, result.score)
                if action.startswith("key"):
                    self.control.tap_key(key or "F", seconds=0.04)
                else:
                    self._click_match(result.center)
                if action == "key_break":
                    return True
                time.sleep(0.02)
                break
            else:
                if time.monotonic() - last_log > 3:
                    logger.info("waiting fishing entry templates")
                    last_log = time.monotonic()
                time.sleep(self.config.loop_interval)
        self.state = FishingState.STOPPED
        return False

    def _confirm_fish(self, stop_event: threading.Event) -> bool:
        needed = {"yu1.png", "yu.png"}
        found: set[str] = set()
        deadline = time.monotonic() + 8.0
        while needed - found and not stop_event.is_set() and time.monotonic() < deadline:
            frame = self.capture.screenshot()
            for filename in list(needed - found):
                match = self.recognition.match_template(frame, self.config.template(filename), self.config.match_threshold)
                if match.ok:
                    logger.info("fish confirm matched %s", filename)
                    self.control.tap_key("F", seconds=0.04)
                    found.add(filename)
            time.sleep(self.config.loop_interval)
        return needed == found

    def _follow_and_wait_result(self, stop_event: threading.Event) -> bool:
        started = time.monotonic()
        while not stop_event.is_set():
            frame = self.capture.screenshot()
            self._follow_bar_frame(frame)

            success = self.recognition.match_template(frame, self.config.template("dianjikongbai.png"), self.config.match_threshold)
            if success.ok:
                self.control.release_all()
                self._click_match(success.center)
                self.fish_count += 1
                self.state = FishingState.SUCCESS
                logger.info("fishing success, count=%s", self.fish_count)
                return True

            escape = self.recognition.match_template(frame, self.config.template("panduandiaoyu.png"), self.config.match_threshold)
            if escape.ok or time.monotonic() - started > self.config.result_timeout:
                self.control.release_all()
                self.state = FishingState.FAILED
                logger.info("fish escaped or timeout")
                return False

            time.sleep(self.config.loop_interval)
        self.state = FishingState.STOPPED
        return False

    def _follow_bar_frame(self, frame: np.ndarray) -> None:
        client_w, client_h = frame.shape[1], frame.shape[0]
        roi = self.config.bar_roi.scale_from(self.config.base_size, (client_w, client_h))
        green = self.recognition.detect_green_zone(
            frame,
            roi,
            np.array(self.config.green_hsv_lower, dtype=np.uint8),
            np.array(self.config.green_hsv_upper, dtype=np.uint8),
        )
        yellow_x = self.recognition.detect_yellow_marker(frame, roi, self.config.template("hs.png"),
                                                         self.config.yellow_threshold)
        if green is None or yellow_x is None:
            self.control.release_all()
            return
        self._apply_bar_control(FishingDetection(yellow_x=yellow_x, green_left=green[0], green_right=green[1]))

    def _apply_bar_control(self, detection: FishingDetection) -> None:
        buffer_px = int(detection.green_width * self.config.green_buffer_pct)
        target_left = detection.green_left + buffer_px
        target_right = detection.green_right - buffer_px
        if target_left >= target_right:
            target_left, target_right = detection.green_left, detection.green_right

        if target_left <= detection.yellow_x <= target_right:
            self.control.release_all()
            return

        if detection.yellow_x < target_left:
            key = "D"
            overshoot = target_left - detection.yellow_x
        else:
            key = "A"
            overshoot = detection.yellow_x - target_right

        pulse = max(self.config.pulse_min, min(self.config.pulse_max, overshoot * self.config.pulse_scale))
        self.control.release_all()
        self.control.tap_key(key, seconds=pulse)

    def _click_match(self, center) -> None:
        if center is None:
            return
        x = center.x + random.randint(-10, 10)
        y = center.y + random.randint(-10, 10)
        self.control.click(x, y, seconds=0.03)
```

迁移后的变化：

- `global_stop`、`fish_count` 变为实例字段，方便测试和多实例。
- 不再通过 `os.environ["FISHING_TARGET_HWND"]` 传句柄，由 `WindowService` 注入。
- `find_image()` 从函数变成 `RecognitionService.match_template()`。
- A/D 控制逻辑从线程函数变成 `_apply_bar_control()`，可直接单元测试。
- ROI 自动按当前客户区从 1920×1080 缩放，避免多处分散硬编码。

---

## 8. 功能迁移代码示例

### 8.1 快速剧情 / 任务跳过

**Before（当前 NTE：`automation_thread.py`）**

```python
screen_bgr = screenshot_window_by_title(self.window_title)
result = cv2.matchTemplate(screen_scaled, template_scaled, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
if max_val >= MATCH_THRESHOLD:
    if action == "click":
        pyautogui.click(click_x, click_y)
    elif action == "key":
        pyautogui.press(param.lower())
```

问题：截图按标题、动作按 `pyautogui`、模板加载、日志、Qt 线程混在一个类里。

**After（`src/core/quest/quest_core.py`）**

```python
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.core.interface import CaptureService, ControlService, RecognitionService

logger = logging.getLogger(__name__)
ActionType = Literal["click", "key", "center_click"]


@dataclass(frozen=True)
class TemplateAction:
    filename: str
    action: ActionType
    param: str | None = None
    threshold: float = 0.90


class QuestSkipCore:
    def __init__(self, capture: CaptureService, recognition: RecognitionService,
                 control: ControlService, template_dir: Path, actions: list[TemplateAction]):
        self.capture = capture
        self.recognition = recognition
        self.control = control
        self.template_dir = template_dir
        self.actions = actions

    def tick(self) -> bool:
        frame = self.capture.screenshot()
        for item in self.actions:
            match = self.recognition.match_template(frame, self.template_dir / item.filename, item.threshold)
            if not match.ok:
                continue
            if item.action == "click" and match.center is not None:
                self.control.click(match.center.x, match.center.y)
            elif item.action == "key" and item.param:
                self.control.tap_key(item.param)
            elif item.action == "center_click":
                self.control.click()
            logger.info("quest action: %s score=%.3f", item.filename, match.score)
            return True
        return False

    def run_forever(self, stop_event, loop_interval: float = 0.05, action_delay: float = 0.01) -> None:
        while not stop_event.is_set():
            acted = self.tick()
            time.sleep(action_delay if acted else loop_interval)
```

关键差异：

- Qt `QThread` 只包一层 `QuestSkipCore.run_forever()`，不再持有识别细节。
- 模板动作仍保留 NTE 的表驱动优势，但 `action` 执行转到 `ControlService`。
- 后续新增 OCR/YOLO 状态，只需扩展 `RecognitionService` 或新增 `Detector`。

---

### 8.2 AI 钓鱼主流程

**Before（当前 NTE：`fishing.py`）**

```python
pos = find_image(PATH_DIAOYU)
if pos:
    pydirectinput.press('f')
...
target_hwnd_str = os.environ.get("FISHING_TARGET_HWND")
target_hwnd = int(target_hwnd_str)
controlfishing.start_follow(stop_event, target_hwnd=target_hwnd)
```

问题：流程、截图、模板、输入、句柄传递全部耦合，`global_stop` 和 `fish_count` 不利于测试。

**After（`src/service/fishing_service.py`）**

```python
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from src.core.fishing.fishing_core import FishingCore
from src.core.interface import TaskService

logger = logging.getLogger(__name__)


@dataclass
class FishingService(TaskService):
    core: FishingCore
    retry_sleep: float = 3.0
    success_sleep: float = 1.0

    def __post_init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="nte-fishing", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.core.control.release_all()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        logger.info("fishing service started")
        while not self._stop_event.is_set():
            ok = self.core.run_once(self._stop_event)
            self._interruptible_sleep(self.success_sleep if ok else self.retry_sleep)
        logger.info("fishing service stopped, count=%s", self.core.fish_count)

    def _interruptible_sleep(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while not self._stop_event.is_set() and time.monotonic() < end:
            time.sleep(0.05)
```

关键差异：

- UI 调用 `fishing_service.start()` / `stop()`，不再直接 `subprocess.Popen([python, fishing.py])`。
- 线程生命周期、停止信号、释放按键统一在服务层。
- 可以在 tests 中用 fake capture/control 直接测试 `FishingCore`。

---

### 8.3 钓鱼条控制器

**Before（当前 NTE：`controlfishing_v2.py`）**

```python
if target_left <= yellow_x <= target_right:
    release_all()
elif yellow_x < target_left:
    release_all()
    pulse = scale_pulse(target_left - yellow_x)
    pydirectinput.keyDown('d')
    time.sleep(pulse)
    pydirectinput.keyUp('d')
else:
    release_all()
    pulse = scale_pulse(yellow_x - target_right)
    pydirectinput.keyDown('a')
    time.sleep(pulse)
    pydirectinput.keyUp('a')
```

**After（可测试的纯逻辑）**

```python
from dataclasses import dataclass

from src.core.interface import FishingDetection


@dataclass(frozen=True)
class PulseDecision:
    key: str | None
    seconds: float = 0.0


def decide_fishing_pulse(detection: FishingDetection, buffer_pct: float = 0.25,
                         pulse_scale: float = 0.002, pulse_min: float = 0.005,
                         pulse_max: float = 0.040) -> PulseDecision:
    buffer_px = int(detection.green_width * buffer_pct)
    left = detection.green_left + buffer_px
    right = detection.green_right - buffer_px
    if left >= right:
        left, right = detection.green_left, detection.green_right
    if left <= detection.yellow_x <= right:
        return PulseDecision(None)
    if detection.yellow_x < left:
        overshoot = left - detection.yellow_x
        return PulseDecision("D", max(pulse_min, min(pulse_max, overshoot * pulse_scale)))
    overshoot = detection.yellow_x - right
    return PulseDecision("A", max(pulse_min, min(pulse_max, overshoot * pulse_scale)))
```

关键差异：

- 计算决策与执行输入分离，`decide_fishing_pulse()` 不 import `time`、`pydirectinput`、`win32gui`。
- 可用几十组 `FishingDetection` 做离线单测，避免每次都开游戏调参。

---

### 8.4 窗口管理

**Before（当前 NTE：多处重复）**

```python
def enum_cb(hwnd, _):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if "异环" in title and "异环薄荷AI" not in title:
            self.fishing_window_combo.addItem(title, hwnd)
```

**After（`src/service/window_service.py`）**

```python
from __future__ import annotations

import logging

import win32gui

from src.core.interface import WindowService

logger = logging.getLogger(__name__)


class Win32WindowService(WindowService):
    def __init__(self, title_keyword: str = "异环", exclude_keywords: tuple[str, ...] = ("异环薄荷AI",)):
        self.title_keyword = title_keyword
        self.exclude_keywords = exclude_keywords
        self._hwnd: int | None = None
        self.refresh()

    @property
    def hwnd(self) -> int:
        if self._hwnd is None or not win32gui.IsWindow(self._hwnd):
            if not self.refresh():
                raise RuntimeError(f"game window not found: {self.title_keyword}")
        return int(self._hwnd)

    def list_windows(self) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []
        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if self.title_keyword in title and not any(k in title for k in self.exclude_keywords):
                found.append((hwnd, title))
        win32gui.EnumWindows(callback, None)
        return found

    def refresh(self) -> bool:
        windows = self.list_windows()
        self._hwnd = windows[0][0] if windows else None
        return self._hwnd is not None

    def get_client_size(self) -> tuple[int, int]:
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        return right - left, bottom - top

    def get_client_rect_on_screen(self) -> tuple[int, int, int, int]:
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        sx, sy = win32gui.ClientToScreen(self.hwnd, (0, 0))
        return sx, sy, sx + right - left, sy + bottom - top

    def is_foreground(self) -> bool:
        return win32gui.GetForegroundWindow() == self.hwnd
```

关键差异：

- UI 下拉、截图、输入全部使用同一个 `WindowService`。
- 后续支持多开时，可以仿照 WWA 用进程路径过滤 hwnd。

---

### 8.5 ROI 调试

**Before（当前 NTE：`ROI = (597, 61, 1328, 85)` 分散在 5 个文件）**

```python
ROI = (597, 61, 1328, 85)
```

**After（配置 + 几何对象）**

```yaml
# config.yaml
window:
  title_keyword: "异环"
  exclude_keywords: ["异环薄荷AI", "镜像"]
fishing:
  base_size: [1920, 1080]
  bar_roi: [597, 61, 1328, 85]
  match_threshold: 0.70
  yellow_threshold: 0.60
  green_hsv_lower: [60, 100, 150]
  green_hsv_upper: [90, 255, 255]
quest:
  match_threshold: 0.90
  loop_interval: 0.05
  action_delay: 0.01
```

```python
from src.core.interface import Rect

base_size = tuple(config["fishing"]["base_size"])
roi = Rect(*config["fishing"]["bar_roi"])
scaled_roi = roi.scale_from(base_size, capture_service.screenshot().shape[1::-1])
```

关键差异：

- ROI 只在 `config.yaml` 出现一次。
- ROI debugger 修改 ROI 后可回写 YAML，主程序自动读取同一份配置。

---

### 8.6 自动更新

**Before（当前 NTE：字符串比较版本）**

```python
if remote_ver > self.current_version:
    QDesktopServices.openUrl(QUrl(releases_url))
```

**After（服务化，语义化版本比较）**

```python
from __future__ import annotations

from dataclasses import dataclass
from urllib.request import urlopen
from packaging.version import Version


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    remote: str
    update_available: bool
    release_url: str


class UpdateService:
    def __init__(self, owner: str, repo: str, current_version: str):
        self.owner = owner
        self.repo = repo
        self.current_version = current_version

    def check(self) -> UpdateInfo | None:
        url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/main/version.txt"
        try:
            with urlopen(url, timeout=5) as resp:
                remote = resp.read().decode("utf-8").strip()
        except Exception:
            return None
        return UpdateInfo(
            current=self.current_version,
            remote=remote,
            update_available=Version(remote) > Version(self.current_version),
            release_url=f"https://github.com/{self.owner}/{self.repo}/releases",
        )
```

关键差异：

- UI 只负责弹窗；网络和版本比较在 service。
- `1.0.10 > 1.0.9` 按语义化版本正确判断。

---

## 9. 依赖配置建议

建议使用 `pyproject.toml`，保留 NTE 当前 PyQt/OpenCV/WGC 能力，并引入 WWA 同款工程化依赖。

```toml
[project]
name = "nte-ai-v2"
version = "2.0.0"
description = "NTE automation assistant rebuilt with layered architecture"
readme = "README.md"
requires-python = ">=3.10,<3.13"
dependencies = [
    "numpy>=1.26,<2.0",
    "opencv-python>=4.11.0",
    "pillow>=10.0",
    "pywin32>=308; platform_system == 'Windows'",
    "windows-capture>=1.0; platform_system == 'Windows'",
    "pyside6>=6.8,<7.0",
    "pyside6-fluent-widgets[full]>=1.7,<2.0",
    "pydantic>=2.0",
    "omegaconf>=2.3",
    "dependency-injector>=4.45,<5.0",
    "psutil>=7.0,<8.0",
    "packaging>=24.0",
    "colorlog>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-mock>=3.14",
]
ocr = [
    "rapidocr>=3.0",
    "onnxruntime>=1.20",
]
legacy-input = [
    "pyautogui>=0.9",
    "pydirectinput>=1.0",
    "pynput>=1.7",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-q"

[tool.mypy]
ignore_missing_imports = true
python_version = "3.10"
```

说明：

- `legacy-input` 暂留，用于 PostMessage 不兼容时回退，不再让业务代码直接 import。
- `rapidocr` 可选；NTE 当前未用 OCR，但 WWA 证明 OCR 服务化后可扩展剧情任务。
- `dependency-injector` 可用于像 WWA 一样装配 service singleton。

---

## 10. 依赖注入容器示例

```python
from dependency_injector import containers, providers

from src.core.fishing.fishing_core import FishingConfig, FishingCore
from src.service.capture_service import PrintWindowCaptureService
from src.service.control_service import PostMessageControlService
from src.service.fishing_service import FishingService
from src.service.recognition_service import OpenCVRecognitionService
from src.service.window_service import Win32WindowService


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    window_service = providers.Singleton(
        Win32WindowService,
        title_keyword=config.window.title_keyword,
        exclude_keywords=config.window.exclude_keywords,
    )
    control_service = providers.Singleton(PostMessageControlService, window_service=window_service)
    capture_service = providers.Singleton(PrintWindowCaptureService, window_service=window_service)
    recognition_service = providers.Singleton(OpenCVRecognitionService)

    fishing_config = providers.Factory(
        FishingConfig,
        asset_dir=config.fishing.asset_dir,
        match_threshold=config.fishing.match_threshold,
        yellow_threshold=config.fishing.yellow_threshold,
    )
    fishing_core = providers.Factory(
        FishingCore,
        capture=capture_service,
        recognition=recognition_service,
        control=control_service,
        config=fishing_config,
    )
    fishing_service = providers.Singleton(FishingService, core=fishing_core)
```

---

## 11. UI 迁移方式

UI 不再直接 `subprocess.Popen` 或 import `fishing.global_stop`，而是持有服务。

```python
class FishingTab(QWidget):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.fishing_service = container.fishing_service()
        self.start_btn.clicked.connect(self.start_fishing)
        self.stop_btn.clicked.connect(self.stop_fishing)

    def start_fishing(self):
        if self.fishing_service.is_running():
            self.append_log("[警告] 钓鱼已在运行")
            return
        self.fishing_service.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.append_log("[系统] 钓鱼已启动")

    def stop_fishing(self):
        self.fishing_service.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_log("[系统] 钓鱼已停止")
```

这样 UI 文件可以拆成多个 tab，避免当前 `ui.py` 继续膨胀。

---

## 12. 测试框架搭建

### 12.1 推荐测试目录

```text
tests/
├── core/
│   ├── test_fishing_decision.py
│   ├── test_fishing_core.py
│   └── test_quest_core.py
├── service/
│   ├── test_recognition_service.py
│   └── test_window_service_contract.py
├── fixtures/
│   ├── fishing_bar_inside.png
│   ├── fishing_bar_left.png
│   └── fishing_bar_right.png
└── conftest.py
```

### 12.2 钓鱼控制决策单测

```python
from src.core.interface import FishingDetection
from src.core.fishing.detector import decide_fishing_pulse


def test_decide_no_action_when_yellow_inside_safe_zone():
    decision = decide_fishing_pulse(FishingDetection(yellow_x=150, green_left=100, green_right=200))
    assert decision.key is None
    assert decision.seconds == 0.0


def test_decide_press_d_when_yellow_left_of_zone():
    decision = decide_fishing_pulse(FishingDetection(yellow_x=90, green_left=100, green_right=200))
    assert decision.key == "D"
    assert 0.005 <= decision.seconds <= 0.040


def test_decide_press_a_when_yellow_right_of_zone():
    decision = decide_fishing_pulse(FishingDetection(yellow_x=230, green_left=100, green_right=200))
    assert decision.key == "A"
    assert 0.005 <= decision.seconds <= 0.040
```

### 12.3 Core 层 fake service 测试

```python
import numpy as np

from src.core.interface import CaptureService, ControlService, MatchResult, MouseButton, Point, RecognitionService, Rect
from src.core.fishing.fishing_core import FishingConfig, FishingCore


class FakeCapture(CaptureService):
    def screenshot(self, region: Rect | None = None) -> np.ndarray:
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def screenshot_window(self, hwnd: int) -> np.ndarray:
        return self.screenshot()


class FakeControl(ControlService):
    def __init__(self):
        self.actions = []

    def key_down(self, key): self.actions.append(("down", key))
    def key_up(self, key): self.actions.append(("up", key))
    def tap_key(self, key, seconds=0.05): self.actions.append(("tap", key, seconds))
    def click(self, x=None, y=None, button=MouseButton.LEFT, seconds=0.03): self.actions.append(("click", x, y))
    def activate(self): self.actions.append(("activate",))
    def release_all(self): self.actions.append(("release_all",))


class FakeRecognition(RecognitionService):
    def __init__(self):
        self.calls = 0

    def match_template(self, image, template_path, threshold):
        name = str(template_path)
        if "diaoyu" in name:
            return MatchResult(True, 0.95, Point(100, 100))
        if "panduandiaoyu" in name:
            return MatchResult(True, 0.95, Point(200, 200))
        if "yu" in name:
            return MatchResult(True, 0.95, Point(300, 300))
        if "dianjikongbai" in name:
            self.calls += 1
            return MatchResult(self.calls > 2, 0.96, Point(500, 500))
        return MatchResult(False, 0.0)

    def find_first_template(self, image, template_paths, threshold): return None
    def detect_green_zone(self, image, roi, hsv_lower, hsv_upper): return (100, 200)
    def detect_yellow_marker(self, image, roi, template_path, threshold): return 150


def test_fishing_core_can_run_success_once(tmp_path):
    control = FakeControl()
    core = FishingCore(FakeCapture(), FakeRecognition(), control, FishingConfig(asset_dir=tmp_path))
    import threading
    ok = core.run_once(threading.Event())
    assert ok is True
    assert core.fish_count == 1
    assert any(action[0] == "tap" and action[1] == "F" for action in control.actions)
```

### 12.4 RecognitionService 离线图像测试

```python
import cv2
import numpy as np

from src.core.interface import Rect
from src.service.recognition_service import OpenCVRecognitionService


def test_detect_green_zone_from_synthetic_image():
    service = OpenCVRecognitionService()
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    # RGB 绿色，转换 HSV 后应落在 [60,100,150] ~ [90,255,255]
    img[40:60, 100:180] = (0, 255, 0)
    result = service.detect_green_zone(
        img,
        Rect(0, 0, 300, 100),
        np.array([50, 100, 100], dtype=np.uint8),
        np.array([90, 255, 255], dtype=np.uint8),
    )
    assert result == (100, 179)
```

---

## 13. 分阶段落地计划

1. **第一阶段：抽接口但不改 UI**
   - 新建 `src/core/interface.py`、`src/service/recognition_service.py`。
   - 把 `find_image()`、HSV 检测、模板匹配迁入 `RecognitionService`。
   - 加入 `tests/core/test_fishing_decision.py`。

2. **第二阶段：输入与窗口服务化**
   - 新建 `WindowService` 与 `ControlService`。
   - 钓鱼与剧情先走同一个输入服务；必要时保留 `PyDirectInputControlService` 作为 fallback。

3. **第三阶段：钓鱼状态机重写**
   - 引入 `FishingCore` 与 `FishingService`。
   - UI 调 `FishingService.start/stop`，删除环境变量传 hwnd。

4. **第四阶段：剧情任务核心重写**
   - 引入 `QuestSkipCore`。
   - `AutomationThread` 只做 Qt 线程包装与信号转发。

5. **第五阶段：配置和调试工具统一**
   - ROI、阈值、模板动作、窗口关键词进入 `config.yaml`。
   - ROI debugger 读取/写回同一份配置。

---

## 14. 总结

NTE-ai v2 不需要推翻现有算法。最值得复用的是：

- `TEMPLATES_CONFIG` 的表驱动剧情动作。
- `controlfishing_v2.py` 的 WGC + HSV + 黄标模板 + 区间保持控制。
- `roi_debugger.py` 的实时可视化调参能力。

最需要替换的是工程组织方式：把脚本式全局函数改为 WWA 风格的 ABC 接口、服务实现、核心状态机与测试夹具。这样 NTE 后续新增战斗宏、AI 麻将、OCR 任务或 YOLO 检测时，不会继续堆到 `ui.py` 和根目录脚本里，而是沿着稳定接口扩展。
