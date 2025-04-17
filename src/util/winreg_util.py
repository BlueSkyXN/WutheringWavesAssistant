import logging
import winreg
from pathlib import Path

logger = logging.getLogger(__name__)

WINREG_GAME_KEYS = [
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\KRInstall Wuthering Waves",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\KRInstall Wuthering Waves Overseas",
]


def get_install_path() -> str | None:
    for key_str in WINREG_GAME_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_str) as key:
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                if not install_path:
                    logger.info(f"注册表键存在但 InstallPath 为空: {key_str}")
                    continue
                logger.debug("install_path: %s", install_path)
                program_path = Path(install_path).joinpath("Wuthering Waves Game/Wuthering Waves.exe")
                logger.debug(f"从注册表读取游戏路径: {program_path}")
                return str(program_path)
        except FileNotFoundError:
            logger.debug(f"注册表路径不存在: {key_str}")
        except PermissionError:
            logger.warning(f"没有权限访问注册表项: {key_str}")
        except Exception:
            logger.exception(f"读取注册表 {key_str} 时异常")
    return None
