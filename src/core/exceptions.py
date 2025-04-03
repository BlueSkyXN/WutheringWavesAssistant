
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


