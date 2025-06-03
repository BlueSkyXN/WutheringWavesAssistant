import threading
import time

from pynput import mouse, keyboard

# 按键录制

output_file = "recorded_mouse_clicks.txt"
events = []

# 时间戳计算
last_time = time.time()


def get_delay():
    global last_time
    now = time.time()
    delay_ms = int((now - last_time) * 1000)
    last_time = now
    return delay_ms


# 录制状态标志
is_recording = False
mouse_listener = None
keyboard_listener = None


def on_click(x, y, button, pressed):
    if not is_recording:
        return
    delay = get_delay()
    if delay > 0:
        print(f'Delay {delay}')
        events.append(f'Delay {delay}')
    action = "Click" if pressed else "Release"
    print(f'{action} {button} at ({x}, {y})')
    events.append(f'{action} {button} at ({x}, {y})')


def on_press(key):
    global is_recording
    try:
        if hasattr(key, 'char') and key.char == 'z':
            # 切换录制状态
            if is_recording:
                print("🎬 停止录制")
                stop_recording()
                is_recording = False
            else:
                print("🎬 开始录制")
                events.clear()
                is_recording = True
                start_mouse_recording()
        elif is_recording:
            delay = get_delay()
            if delay > 0:
                print(f'Delay {delay}')
                events.append(f'Delay {delay}')
            if hasattr(key, 'char') and key.char in {'e', 'q', 'r', 't'}:
                print(f'KeyDown {key.char}')
                events.append(f'KeyDown {key.char}')
            elif key == keyboard.Key.space:
                print('KeyDown space')
                events.append('KeyDown space')
    except AttributeError:
        pass


def on_release(key):
    if not is_recording:
        return
    try:
        delay = get_delay()
        if delay > 0:
            print(f'Delay {delay}')
            events.append(f'Delay {delay}')
        if hasattr(key, 'char') and key.char in {'e', 'q', 'r', 't'}:
            print(f'KeyUp {key.char}')
            events.append(f'KeyUp {key.char}')
        elif key == keyboard.Key.space:
            print('KeyUp space')
            events.append('KeyUp space')
    except AttributeError:
        pass


def start_mouse_recording():
    global mouse_listener
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()


def stop_recording():
    global mouse_listener
    if mouse_listener:
        mouse_listener.stop()
    # save_events()


def save_events():
    with open(output_file, "w", encoding='utf-8') as f:
        for event in events:
            f.write(event + "\n")
    print(f"✅ 录制完成，已保存到当前目录：{output_file}")


def start_keyboard_listener():
    global keyboard_listener
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    keyboard_listener.start()
    keyboard_listener.join()


# 启动键盘监听线程
keyboard_thread = threading.Thread(target=start_keyboard_listener)
keyboard_thread.daemon = True
keyboard_thread.start()
keyboard_thread.join()
