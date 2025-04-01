import ctypes


def is_admin():
    try:
        # 检查是否有管理员权限
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        return False
