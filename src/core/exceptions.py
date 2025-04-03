from functools import wraps


def raise_as(exception_class):
    """装饰器：将捕获的异常重新抛出为指定的异常类"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                # 捕获到的原始异常包装成指定的异常类
                raise exception_class() from e

        return wrapper

    return decorator


class ScreenshotError(Exception):
    """Generic screenshot error"""

    def __init__(self, message="Screenshot capture failed"):
        super().__init__(message)


class ForegroundScreenshotError(ScreenshotError):
    """Foreground screenshot error"""

    def __init__(self, message="Failed to capture foreground screenshot"):
        super().__init__(message)


class BackgroundScreenshotError(ScreenshotError):
    """Background screenshot error"""

    def __init__(self, message="Failed to capture background screenshot"):
        super().__init__(message)


class WindowError(Exception):
    """Generic window error"""

    def __init__(self, message="Window operation failed"):
        super().__init__(message)


class HwndError(WindowError):
    """Hwnd error"""

    def __init__(self, message="Hwnd operation failed"):
        super().__init__(message)
