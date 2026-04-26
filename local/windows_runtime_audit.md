# NTE-Assistant Windows Runtime 审计报告

审计对象：`/Volumes/TP4000PRO/GitHub/NTE-Assistant`  
审计方式：只读代码审计；无法在 Windows 真机运行，因此以下结论以 Win32 API 规范、pywin32/ctypes 行为、GDI 生命周期、Windows DPI/权限模型推断。  
重点结论：当前版本在 Windows 首测前有多个 release blocker，主要集中在 **PostMessage 对 UnrealWindow 可能无效**、**窗口识别过宽**、**PrintWindow/GDI 坐标与资源生命周期风险**、**DPI awareness 设置时机**、**多线程共享 service 未加锁**。

---

## Findings

### 1. CRITICAL — PostMessage 很可能无法驱动 Unreal Engine 游戏输入
- **File:Line**：`src/service/control_service.py:248,255,293,301,304,312`；`src/service/window_service.py:29`
- **Problem**：控制层只向目标 HWND 投递 `WM_KEYDOWN/WM_KEYUP/WM_MOUSE*`。目标窗口类默认是 `UnrealWindow`，现代 Unreal Engine 游戏通常通过 Raw Input / DirectInput / Enhanced Input 读取硬件输入，往 message queue 里 `PostMessage` 的键鼠消息经常被游戏输入系统忽略。
- **Evidence**：`win32gui.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk, lparam)` 是唯一键盘路径；鼠标同理只发送 `WM_MOUSEMOVE/WM_LBUTTONDOWN/UP`。审计范围内没有 `SendInput`、`pydirectinput`、Windows low-level driver backend。
- **Fix**：新增可配置 backend：优先实现 `SendInputControlService`（foreground required），`input.backend: postmessage|sendinput`；首轮 Windows 测试必须做输入自检。如果 PostMessage 无效，应切换 SendInput 或 pydirectinput。

### 2. CRITICAL — 默认配置禁用了 UnrealWindow class filter，可能操作错误窗口
- **File:Line**：`config.yaml:7`；`main.py:341-345`；`src/service/window_service.py:65-67,111`
- **Problem**：`config.yaml` 配置 `class_name: ""`，`main.py` 原样传入，`Win32WindowService` 将空字符串转成空 tuple，`class_ok = not self.class_names or ...` 变成永远 True。实际只按标题包含 `异环` 选窗口。
- **Evidence**：`config.yaml:7 class_name: ""`；`main.py:343 class_names=window_cfg.get("class_name", "")`；`window_service.py:111 class_ok = not self.class_names or class_name in self.class_names`。
- **Fix**：配置改为 `class_name: "UnrealWindow"`；`main.py` 中空值应 fallback 到 `DEFAULT_CLASS_NAMES`，例如 `class_names=window_cfg.get("class_name") or DEFAULT_CLASS_NAMES`；若用户显式关闭 class filter，应输出 WARNING。

### 3. HIGH — 进程名 allow-list 未从 config 接入，process validation 实际关闭
- **File:Line**：`src/service/window_service.py:60-75,177-186,218-219`；`main.py:341-345`
- **Problem**：`Win32WindowService` 支持 `expected_process_names` 与 `validate_process`，默认进程名也是 `Client-Win64-Shipping.exe`，但 `main.py` 创建 service 时没有传入 `validate_process=True`，因此生产路径永远不校验进程。
- **Evidence**：`main.py:341-345` 只传 `title_keyword/class_names/exclude_keywords`；`window_service.py:75 self.validate_process = bool(validate_process)` 默认 False。
- **Fix**：在 `config.yaml` 增加：`validate_process: true`、`expected_process_names: ["Client-Win64-Shipping.exe"]`，并在 `main.py` 传入；生产默认开启，单元测试可显式关闭。

### 4. HIGH — UAC / Integrity Level 不匹配时 PostMessage 会失败或被 UIPI 拦截
- **File:Line**：`src/service/control_service.py:248,255,293,301,304,312`
- **Problem**：如果游戏以管理员权限运行，而助手普通权限运行，Windows UIPI 会阻止低完整性进程向高完整性窗口发送大量 window messages。当前代码没有捕获 `PostMessage` 失败，也没有诊断。
- **Evidence**：所有 `PostMessage` 调用都未检查返回值/异常；没有 `GetLastError`、权限提示或 elevated self-check。
- **Fix**：封装 `_post_message()`，捕获 `pywintypes.error`，记录 `winerror=5 Access is denied`；启动时检查自身与目标进程 elevation，提示“请以相同权限运行”。

### 5. HIGH — `ctypes.windll` 调用未声明 `argtypes/restype`，64-bit HWND/HDC 有截断风险
- **File:Line**：`src/service/capture_service.py:28-33,136`
- **Problem**：`DwmGetWindowAttribute` 与 `PrintWindow` 直接经 `ctypes.windll` 调用，未设置参数类型。ctypes 默认按 `c_int` 传 Python int，在 64-bit Windows 下 HWND/HDC 是 pointer-sized，存在高 32 位被截断风险。
- **Evidence**：`ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, ...)`；`ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), flags)`。
- **Fix**：模块初始化时设置：`PrintWindow.argtypes=[wintypes.HWND,wintypes.HDC,wintypes.UINT]`, `restype=wintypes.BOOL`；`DwmGetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]`, `restype=ctypes.c_long`。

### 6. HIGH — PrintWindow 位图尺寸使用 DWM extended frame，与实际渲染/裁剪坐标系不一致
- **File:Line**：`src/service/capture_service.py:120-132,160-168`
- **Problem**：`_capture_window` 用 `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` 计算 bitmap 尺寸；但 `PrintWindow` 渲染语义更接近整个 window rect。`_crop_client` 又用 DWM rect 的 left/top 与 `ClientToScreen` 相减，容易产生 7-8px 的系统性偏移或右下裁剪。
- **Evidence**：`left, top, right, bottom = _dwm_window_rect(hwnd)`；`bitmap.CreateCompatibleBitmap(mfc_dc, width, height)`；裁剪时 `x = max(0, client_left - win_left)`。
- **Fix**：bitmap 与裁剪统一使用 `win32gui.GetWindowRect(hwnd)` + `ClientToScreen(hwnd,(0,0))` + `GetClientRect`；如保留 DWM rect，必须补偿 `GetWindowRect` 与 DWM bounds 的差值，并在 offset<0 时报警。

### 7. HIGH — GDI 资源分配阶段不在 try/finally 内，异常会泄漏 DC/HBITMAP
- **File:Line**：`src/service/capture_service.py:128-158`
- **Problem**：`GetWindowDC`、`CreateDCFromHandle`、`CreateCompatibleDC`、`CreateBitmap`、`CreateCompatibleBitmap`、`SelectObject` 都在 `try:` 之前。任一步抛异常会泄漏已创建的 GDI object / DC。
- **Evidence**：`try:` 从 `capture_service.py:135` 才开始；释放逻辑在 `finally:152-158`。
- **Fix**：把所有 GDI 分配纳入 try/finally，变量初始化为 `None`，按后创建先释放顺序清理；`old_obj` 只有成功 select 后才 restore。

### 8. HIGH — 最小化窗口未检查，PrintWindow 可能返回旧帧/黑帧仍被当作实时画面
- **File:Line**：`src/service/capture_service.py:74-100,120-126`
- **Problem**：最小化窗口常见 rect 在 `(-32000,-32000,...)`，尺寸仍可能合法；`PrintWindow` 可能返回黑帧、旧缓存或失败。当前仅用 mean intensity 判断黑帧，无法识别“非黑旧帧”。
- **Evidence**：capture 路径没有 `win32gui.IsIconic(hwnd)`；`validate_capture` 只检查 `image.mean()`。
- **Fix**：`screenshot_window` 入口检查 `IsWindow/IsWindowVisible/IsIconic`；最小化时抛 typed exception 或暂停任务，不继续识别与点击。

### 9. HIGH — 独占全屏 / DXGI flip model 下 PrintWindow/窗口 DC BitBlt 预计失败
- **File:Line**：`src/service/capture_service.py:136,144`
- **Problem**：游戏若使用 fullscreen exclusive 或 DX12/DXGI flip-model swap chain，`PrintWindow` 常返回黑帧；当前 fallback 是从同一 window DC 做 `BitBlt`，该 DC 在这些场景通常也为空，甚至会覆盖 PrintWindow 已写入的部分有效内容。
- **Evidence**：`if ok != 1: save_dc.BitBlt(..., mfc_dc, ...)`。
- **Fix**：不要用 window DC 覆盖 PrintWindow buffer；前台可选 screen DC BitBlt；长期应实现 Windows.Graphics.Capture / DXGI Desktop Duplication backend，并在检测黑帧时自动 fallback。

### 10. HIGH — DPI awareness 设置太晚且重复，可能导致高 DPI 多屏坐标错位
- **File:Line**：`main.py:14-15,158-167,488-490`；`src/service/window_service.py:40-47,63`
- **Problem**：`PySide6.QtWidgets.QApplication` 在模块顶部已 import，Qt 可能提前锁定 DPI awareness；`setup_dpi_awareness()` 到 `main()` 才调用。随后 `Win32WindowService.__init__` 又调用一次 `SetProcessDpiAwareness(2)`，第二次通常返回 `E_ACCESSDENIED` 且被吞掉。
- **Evidence**：`main.py:15 from PySide6.QtWidgets import QApplication`；`main.py:489 setup_dpi_awareness()`；`window_service.py:63 _enable_dpi_awareness()`。
- **Fix**：在任何 Qt import 前调用 `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2=-4)`；删除 service 构造内的进程级 DPI 设置或加 idempotent guard；失败时至少 WARNING。

### 11. HIGH — `FishingService._run` 在 `_state_lock` 内执行阻塞性 `machine.tick()`
- **File:Line**：`src/service/fishing_service.py:105-108`；`src/core/fishing/fishing_core.py:223-240,249-311`
- **Problem**：`machine.tick()` 包含截图、OpenCV、PostMessage、`time.sleep(cfg.action_delay)`。在 `_state_lock` 内执行会阻塞 `stop()`、`fish_count` 与状态查询，UI 可能点击停止后数秒无响应。
- **Evidence**：`with self._state_lock: state = self.machine.tick()`；`fishing_core.py:239 time.sleep(cfg.action_delay)`。
- **Fix**：不要在 `_state_lock` 内调用 tick；锁仅保护 `_thread/_session_started_at/_consecutive_failures` 和 stats 快照；tick 内 sleep 改用 stop_event-aware wait。

### 12. HIGH — `OpenCVRecognitionService` LRU cache 被 quest/fishing 多线程共享但无锁
- **File:Line**：`src/service/recognition_service.py:22,29-44`；`main.py:347-348`
- **Problem**：`create_service_chain` 创建一个 recognition 单例，被 quest thread 和 fishing thread 共享。`OrderedDict.get -> move_to_end`、`set -> popitem` 是复合操作，无锁时可能 KeyError、错误 eviction 或缓存状态损坏。
- **Evidence**：`self._template_cache: OrderedDict...`；`move_to_end`、`popitem` 未加锁。
- **Fix**：给 `_template_cache` 加 `threading.RLock`；或为 quest/fishing 分别创建 recognition 实例；或改用线程安全缓存封装。

### 13. MEDIUM — capture service 可被多线程同时调用，GDI/PrintWindow 对同 HWND 无同步保护
- **File:Line**：`main.py:347-348`；`src/service/capture_service.py:68-100,120-158`
- **Problem**：quest 与 fishing 可同时运行并共享同一个 `PrintWindowCaptureService`。虽然每次创建局部 DC/bitmap，但 GDI 与窗口绘制本身不是为同一 HWND 高频并发 capture 设计，可能出现黑帧、句柄压力、或 PrintWindow reentrancy 问题。
- **Evidence**：`capture = PrintWindowCaptureService(window_service=window)` 单例注入 context；两个 task 均通过 context 使用同一 capture。
- **Fix**：在 `PrintWindowCaptureService.screenshot_window` 外层加 capture lock；或 UI 层禁止 quest/fishing 同时 capture；统计 capture duration 和失败率。

### 14. MEDIUM — `EnumWindows` callback 未显式 `return True`，枚举行为依赖 pywin32 实现
- **File:Line**：`src/service/window_service.py:106-124`
- **Problem**：Win32 `EnumWindowsProc` 约定返回 TRUE 继续、FALSE 停止。当前 callback 返回 `None`。部分 pywin32 示例可工作，但规范上不明确，存在只枚举第一个窗口的风险。
- **Evidence**：`def callback(...) -> None:` 且所有分支只有 bare `return` 或无 return。
- **Fix**：改成 `-> bool`，每个 early return 和结尾都 `return True`；需要停止时才返回 False。

### 15. MEDIUM — `process_name` 校验 fail-open，解析失败时反而通过
- **File:Line**：`src/service/window_service.py:177-186,218-219`
- **Problem**：如果启用 `validate_process`，`_get_process_name` 因权限、psutil、API 失败返回 None，`_process_name_matches` 返回 True。这会让 allow-list 在最需要防御时失效。
- **Evidence**：`if not name: ... return True`。
- **Fix**：生产默认 fail-closed：无法解析进程名应返回 False；可提供 config `process_validation_fail_open` 仅用于调试。

### 16. MEDIUM — `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` 后先调用 `GetModuleFileNameEx`
- **File:Line**：`src/service/window_service.py:155-167`
- **Problem**：`GetModuleFileNameEx` 在不少 Windows 版本/权限组合需要 `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`；当前只有 `0x1000`，通常会失败后再 fallback 到 `QueryFullProcessImageName`。功能有 fallback，但会产生不必要异常与日志噪声。
- **Evidence**：`OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, ...)`；随后先 `win32process.GetModuleFileNameEx(handle, 0)`。
- **Fix**：直接优先 `QueryFullProcessImageName(handle, 0)`；只有兼容老系统时再 fallback。

### 17. MEDIUM — jitter 后负坐标经 `MAKELONG` 打包会变成 65535 类坐标
- **File:Line**：`src/service/control_service.py:142-143,219-223,278-290`
- **Problem**：`click_coord_jitter_px > 0` 时，靠近左上角的坐标可能变负；`win32api.MAKELONG(-1, -1)` 会按 16-bit unsigned 包装成 `0xFFFFFFFF`，目标窗口收到的 client coordinate 异常。
- **Evidence**：`return x + random.randint(-d,d)`；`return win32api.MAKELONG(int(x), int(y))`。
- **Fix**：jitter 后按 client size clamp 到 `[0,w-1]`、`[0,h-1]`；`_mouse_lparam` 也应做 0..0xFFFF 防御。

### 18. MEDIUM — `SetForegroundWindow` 失败被忽略，后续输入可能发给非前台窗口
- **File:Line**：`src/service/control_service.py:227-232`
- **Problem**：Windows 限制后台进程抢前台，`SetForegroundWindow` 可返回 0。当前忽略返回值，也不验证 `GetForegroundWindow()==hwnd`。如果未来切换 SendInput，这会直接把输入送到错误窗口。
- **Evidence**：`win32gui.SetForegroundWindow(hwnd)` 返回值丢弃。
- **Fix**：检查返回值；失败时尝试 `ShowWindow(SW_RESTORE)`、`AttachThreadInput`、Alt key trick 或提示用户手动聚焦；最终用 `GetForegroundWindow` 验证。

### 19. MEDIUM — `_pressed` set 无锁，stop/release_all 与工作线程 key_down/key_up 竞态
- **File:Line**：`src/service/control_service.py:180,236-256,308-316`；`main.py:99-144,542-549`
- **Problem**：quest/fishing worker 可调用 key_down/up，主线程 shutdown 调用 release_all。`_pressed` 的 add/discard/list snapshot 没有锁，可能漏发 keyup，造成游戏内按键卡住。
- **Evidence**：`self._pressed.add(vk)`、`discard`、`for vk in list(self._pressed)` 都无同步。
- **Fix**：为 `_pressed` 添加 `threading.RLock`；`release_all` 在锁内 swap-and-clear 后再逐个 PostMessage。

### 20. MEDIUM — `FishingService.start()` 锁外 `thread.start()`，存在双线程启动竞态
- **File:Line**：`src/service/fishing_service.py:56-66,86-89`
- **Problem**：`self._thread = thread` 后释放锁，再 `thread.start()`。第二次 start 在这个窗口期看到 `_thread.is_alive()==False`，可再创建一个线程，导致两个 fishing loop 并发。
- **Evidence**：`self._thread = thread` 在锁内，`thread.start()` 在锁外。
- **Fix**：把 `thread.start()` 放进同一锁内；或引入 `_starting` flag / 独立 start lock。

### 21. MEDIUM — `ThreadedQuestService` 也缺少 start/stop 锁
- **File:Line**：`main.py:108-123`
- **Problem**：quest service 的 `_thread` 与 `_stop_event` 操作没有 lock；UI 快速双击 start/stop 时可能创建多个 quest thread 或 stop join 到旧线程。
- **Evidence**：`if self.is_running(): return` 后直接创建并 start thread。
- **Fix**：与 FishingService 一样添加 state lock，或让 `LazyTaskService` 串行化 start/stop。

### 22. MEDIUM — `PrintWindow` 返回值按 `ok != 1` 判断，不符合 BOOL 非零即成功
- **File:Line**：`src/service/capture_service.py:136-144`
- **Problem**：Win32 BOOL 语义是 nonzero success。当前只有等于 1 才认为成功；非 1 的成功值会触发 BitBlt fallback，可能覆盖正确画面。
- **Evidence**：`if ok != 1:`。
- **Fix**：改为 `if not ok:` 或 `if ok == 0:`。

### 23. MEDIUM — `PyCBitmap` 可能存在双重释放风险
- **File:Line**：`src/service/capture_service.py:131-155`
- **Problem**：`win32ui.CreateBitmap()` 返回 PyCBitmap 对象，finally 中又对 `bitmap.GetHandle()` 调 `win32gui.DeleteObject`。若 PyCBitmap 析构也释放 handle，则可能 double delete。
- **Evidence**：`bitmap = win32ui.CreateBitmap()`；`win32gui.DeleteObject(bitmap.GetHandle())`。
- **Fix**：确认 pywin32 版本语义。安全方案：改用 `win32gui.CreateCompatibleBitmap` 原生 HBITMAP 并手动 delete；或让 PyCBitmap 自管理，不再额外 DeleteObject。

### 24. MEDIUM — `GetBitmapBits(True)` 假设 32bpp BGRA，无 bpp/stride 校验
- **File:Line**：`src/service/capture_service.py:146-150`
- **Problem**：compatible bitmap 是 device-dependent bitmap，RDP/虚拟显示/非 32bpp 环境可能返回 24bpp/16bpp 或带 stride padding；直接 reshape 为 `(height,width,4)` 会 ValueError 或错位。
- **Evidence**：`image.shape = (bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4)`；未检查 `bmBitsPixel/bmWidthBytes`。
- **Fix**：使用 `GetDIBits` 强制 top-down 32bpp DIB；至少校验 `bmBitsPixel == 32` 且 `bmWidthBytes == bmWidth*4`。

### 25. MEDIUM — `RapidOCRService` 对新版本 rapidocr_onnxruntime 的构造参数可能不兼容
- **File:Line**：`src/service/ocr_service.py:44-60`；`pyproject.toml:37`
- **Problem**：代码默认传 `use_cuda`。`rapidocr_onnxruntime >=1.3.0` 无上限，后续版本可能改为 `det_use_cuda/cls_use_cuda/rec_use_cuda` 或 params/yaml 配置，导致 `TypeError: unexpected keyword argument 'use_cuda'`。
- **Evidence**：`kwargs["use_cuda"] = self.use_gpu`；依赖 `rapidocr-onnxruntime = { version = ">=1.3.0", optional = true }`。
- **Fix**：pin 已验证版本；或用 `inspect.signature(RapidOCR.__init__)` 动态选择参数；OCR extra 标注实验性。

### 26. MEDIUM — config-to-runtime 静默丢弃 `confirm_timeout`，真实 timeout 不按配置生效
- **File:Line**：`main.py:394-410,442-451`；`src/core/fishing/models.py:71-74`
- **Problem**：`main.py` 传入 `confirm_timeout`，但 `FishingConfig` 字段是 `cast_timeout`。`_construct_with_supported_kwargs` 静默过滤未知字段，因此用户配置不会生效且无 warning。
- **Evidence**：`"confirm_timeout": float(...)`；`valid_fields` 过滤后直接 `return cls(**filtered)`。
- **Fix**：改字段为 `cast_timeout`；unknown config key 必须 WARNING 或抛错；`validate_config` 覆盖 timeout 字段。

### 27. MEDIUM — `_pair/_rect` 与 `Rect.scale_from` 缺少正数/顺序校验
- **File:Line**：`main.py:460-472`；`src/core/interface.py:56-67`；`src/core/fishing/detector.py:67-90`
- **Problem**：`base_size: [0,0]` 会在 `Rect.scale_from` 除零；`bar_roi` 若 right<=left 或 bottom<=top 会得到空 ROI，导致检测永远失败。
- **Evidence**：`sx = target_w / base_w`；`_rect` 仅 int cast，不校验顺序。
- **Fix**：`validate_config` 校验 base_size 两个正整数、ROI 顺序合法且在 base_size 内、HSV 为 3 个 0..255 int。

### 28. MEDIUM — `RecognitionService.match_template` ABC 与实现签名不一致
- **File:Line**：`src/core/interface.py:201-208`；`src/service/recognition_service.py:46-52`
- **Problem**：ABC 无 `scales` 参数，实现新增 `scales: Sequence[float] | None`。未来替换 backend 或 mock 可能不支持调用方期待的多尺度参数。
- **Evidence**：接口 `def match_template(... threshold)`；实现 `def match_template(... threshold, scales=None)`。
- **Fix**：统一接口：要么 ABC 增加 `scales`，要么移除方法级 scales，只在 constructor/config 管理。

### 29. MEDIUM — `ControlService` ABC 与实现 humanize 参数不一致
- **File:Line**：`src/core/interface.py:146-173`；`src/service/control_service.py:236,251,266-273`
- **Problem**：实现 `key_down/key_up/click` 增加 `humanize` 参数，ABC 未声明。通过抽象类型调用时不可见，后续 backend 行为可能不一致。
- **Evidence**：ABC `key_down(self, key)`；实现 `key_down(self, key, humanize=True)`。
- **Fix**：将 `humanize: bool = True` 加到 ABC；或定义单独 Protocol/mixin。

### 30. LOW — VK mapping 基本正确，但缺少 LWIN/RWIN/APPS 扩展键预留
- **File:Line**：`src/service/control_service.py:16-44,58-76`
- **Problem**：当前常用键、F1-F24、箭头、PageUp/Down、Numpad Enter 扩展标志正确；但若未来支持 Windows key / Apps key，应加入 VK_MAP 与 `_EXTENDED_VKS`。
- **Evidence**：`_EXTENDED_VKS` 无 `VK_LWIN/VK_RWIN/VK_APPS`。
- **Fix**：补齐这些 VK，测试 lParam bit 24。

### 31. LOW — `_key_lparam` 不强制 KEYUP repeat_count 为 1
- **File:Line**：`src/service/control_service.py:103-139,251-255`
- **Problem**：当前 `key_up()` 默认 repeat=1，实际 OK；但 helper 若被未来调用传入 repeat>1，会生成不符合 WM_KEYUP 规范的 lParam。
- **Evidence**：`repeat_count = max(1, min(...))` 不区分 `is_up`。
- **Fix**：`if is_up: repeat_count = 1`。

### 32. LOW — `WM_MOUSEMOVE` / mouse up wParam 过于简化
- **File:Line**：`src/service/control_service.py:293,301,304`
- **Problem**：`WM_MOUSEMOVE` 使用 `wParam=0`，down 使用 MK_*，up 使用 0。普通 click 可用；若后续支持 drag/modifier-click，目标窗口无法看到 button/modifier state。
- **Evidence**：`PostMessage(... WM_MOUSEMOVE, 0, lparam)`；`PostMessage(... up_msg, 0, lparam)`。
- **Fix**：维护当前 mouse button/modifier bitmask，按 Win32 `MK_*` 语义构造 wParam。

### 33. LOW — `WindowService.status` property 有 EnumWindows 副作用
- **File:Line**：`src/service/window_service.py:86-90`
- **Problem**：读取 status 会在 hwnd 无效时 refresh，UI 高频绑定时可能反复扫描窗口。
- **Evidence**：`if self._hwnd is None or not IsWindow(...): self.refresh()`。
- **Fix**：status 做纯读，显式刷新由 UI timer/按钮触发。

### 34. LOW — `windows[0]` 按 z-order 选择，多个候选时不稳定
- **File:Line**：`src/service/window_service.py:222-227`
- **Problem**：`EnumWindows` 顺序受 z-order 影响；多个标题匹配窗口时可能因 Alt-Tab 改变目标。
- **Evidence**：`self._hwnd = windows[0][0] if windows else None`。
- **Fix**：优先 foreground 且 class/process 匹配，其次最大 client area，再其次稳定 PID/window creation time。

### 35. LOW — shipped config 覆盖了代码默认 exclude list，漏掉“镜像”
- **File:Line**：`src/service/window_service.py:31`；`config.yaml:11-13`；`main.py:344`
- **Problem**：代码默认排除 `("异环薄荷AI", "镜像")`，配置只传 `NTE-Assistant/异环薄荷AI`，导致 mirror/投屏窗口可能成为候选。
- **Evidence**：`exclude_keywords=tuple(window_cfg.get("exclude_keywords", ()))` 不与默认集合合并。
- **Fix**：配置列表与 `DEFAULT_EXCLUDE_KEYWORDS` 做 union。

### 36. LOW — `validate_capture` 异常 fail-open，会跳过 retry
- **File:Line**：`src/service/capture_service.py:111-118,78-94`
- **Problem**：`image.mean()` 异常时返回 True，使上层认为画面可用，不进入 retry。若 ndarray 已损坏，会把坏帧交给 OpenCV。
- **Evidence**：`except Exception: ... return True`。
- **Fix**：异常时返回 False，并触发 retry/错误路径。

### 37. LOW — `_interruptible_sleep` 极小竞态可能向 `time.sleep` 传负数
- **File:Line**：`src/service/fishing_service.py:157-162`
- **Problem**：while 条件检查后再次 `time.monotonic()`，若跨过 end，`end - now` 可为负。
- **Evidence**：`time.sleep(min(0.05, end - time.monotonic()))`。
- **Fix**：`remaining = max(0.0, end - time.monotonic())`；或用 `_stop_event.wait(min(0.05, remaining))`。

### 38. LOW — optional dependency 版本范围对 Python 3.12 / NumPy 2 组合缺少约束
- **File:Line**：`pyproject.toml:32-39`
- **Problem**：项目允许 Python `<3.13`，但 `numpy>=1.24.0`、`opencv-python>=4.8.0` 无上限/marker。Python 3.12 需要较新的 wheel；旧 OpenCV 与 NumPy 2 组合也可能 ABI 不兼容。
- **Evidence**：无 poetry.lock；依赖范围宽泛。
- **Fix**：增加 marker：Python 3.12 下 `numpy>=1.26`、`opencv-python>=4.9.0.80`；或生成/提交锁文件；明确 Windows 首测 Python 版本。

---

## Verified OK

- `WM_KEYDOWN=0x0100`、`WM_KEYUP=0x0101`、`WM_LBUTTONDOWN=0x0201`、`WM_LBUTTONUP=0x0202` 等使用 pywin32 `win32con` 常量，未发现手写错误值。
- VK mapping 中 `VK_RETURN`、`VK_SPACE`、`VK_ESCAPE`、方向键、Delete/Insert/Home/End/PageUp/PageDown、F1-F24 均来自 `win32con`，基础映射正确。
- `_key_lparam` 对 scancode bits 16-23、extended bit 24、previous-state bit 30、transition bit 31 的布局正确；KEYUP 当前调用路径会设置 bit 30/31。
- `MapVirtualKey(vk, 4)` 优先使用 `MAPVK_VK_TO_VSC_EX`，fallback 到 `MapVirtualKey(vk, 0)`，比用户问题中只用 `MapVirtualKeyW(vk,0)` 更完整；低 8 bit 写入 lParam 合理。
- 鼠标 click 使用 client coordinates（`x/y` 未转 screen），符合 `WM_MOUSE*` lParam 语义；`window_service.get_client_size()` 返回 client size。
- `GetClientRect` + `ClientToScreen` 用于 client rect on screen 的逻辑正确，支持多显示器负坐标；只是 capture 裁剪与 DWM rect 混用有问题。
- `_get_process_name` 中 `GetWindowThreadProcessId(hwnd)` 解包为 `_, pid` 正确；`OpenProcess` 后有 `finally: CloseHandle(handle)`，未发现 handle leak。
- `PROCESS_QUERY_LIMITED_INFORMATION = 0x1000` 常量正确。
- `pywin32>=306` Windows marker 存在于 `pyproject.toml:38`。
- `recognition_service.py` 用 `np.fromfile + cv2.imdecode` 读取模板，可处理 Windows 中文路径，比 `cv2.imread` 更稳。
- capture 输出 `COLOR_BGRA2RGB`，recognition 侧 `COLOR_RGB2GRAY/COLOR_RGB2HSV`，颜色空间匹配。
- `main.py` 在非 Windows 缺 pywin32 时，`create_app_services` 的 ImportError 会被 GUI 入口捕获并提示安装 pywin32；service 模块直接 import 仍会在 macOS 崩，但入口路径有保护。

---

## Cannot verify（必须 Windows 真机确认）

- PostMessage 对实际《异环》客户端是否完全无效、部分 UI 有效、或仅键盘无效；需要 live game smoke test。
- 游戏是否默认管理员权限运行；若是，UIPI/elevation mismatch 会立刻影响 PostMessage/SendInput 行为。
- `PrintWindow(PW_RENDERFULLCONTENT=0x2)` 对目标窗口在窗口化、无边框全屏、独占全屏、DX12/DX11、最小化状态下的真实成功率。
- DWM extended frame bounds 与 `GetWindowRect` 在目标游戏窗口、不同 DPI、多显示器负坐标下的实际差值。
- pywin32 `PyCBitmap` 析构是否会在当前版本自动 DeleteObject；需用 GDIView/Process Explorer 观察 GDI handle 曲线。
- `GetBitmapBits(True)` 在 RDP、HDR、虚拟显示器、不同 color depth 下的 `bmBitsPixel/bmWidthBytes`。
- `rapidocr_onnxruntime` 当前 resolver 实际安装版本的 `RapidOCR.__init__` 签名。
- Qt/PySide6 6.8 在当前 Windows 版本上是否在 import 时锁定 DPI awareness，还是 QApplication 构造时才锁定。

---

## Recommendations for first Windows test run

1. **先修 blocker**：启用 `class_name: "UnrealWindow"`、接入 `validate_process`、补 ctypes `argtypes/restype`、统一 capture 坐标系、给 GDI 分配加完整 finally。
2. **准备双输入 backend**：保留 PostMessage，但必须实现 SendInput fallback；启动后运行“按键是否改变游戏 UI”的自检。
3. **固定测试矩阵**：Windows 11 23H2/24H2，Python 3.11（优先）与 3.12，窗口化/无边框/全屏，100%/125%/150% DPI，多显示器含负坐标。
4. **增加诊断日志**：记录 hwnd/title/class/process/elevation/DPI awareness/client rect/window rect/DWM rect/PrintWindow return/mean brightness。
5. **监控资源**：用 Process Explorer 或 GDIView 观察 GDI Objects、USER Objects、handle count，连续运行 quest+fishing 至少 1 小时。
6. **捕获 A/B 测试**：同一窗口分别测试 `PrintWindow flags=2`、`flags=0`、screen DC BitBlt、WGC prototype，保存首帧与 ROI crop 以肉眼校验偏移。
7. **并发测试**：同时启动 quest 与 fishing，快速 start/stop 50 次，观察线程数量、按键是否卡住、cache 是否报错。
8. **配置错误测试**：故意设置 `base_size: [0,0]`、错误 ROI、空 class name、错误 process name，确认程序 fail-fast 而非静默运行。
