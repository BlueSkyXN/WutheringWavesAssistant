import importlib.util
import os
from pathlib import Path

# 统一的环境变量管理
ENV_WWA_ROOT_PATH = "WWA_ROOT_PATH"
ENV_WWA_LOG_PATH = "WWA_LOG_PATH"
ENV_WWA_LOG_LEADER = "WWA_LOG_LEADER"
ENV_WWA_PARAM_CONFIG_PATH = "WWA_PARAM_CONFIG_PATH"
ENV_WWA_OCR_USE_GPU = "WWA_OCR_USE_GPU"


def __set_root_path():
    root_path = str(Path(__file__).parent.parent.parent)
    os.environ[ENV_WWA_ROOT_PATH] = root_path


__set_root_path()


def load_env():
    if importlib.util.find_spec("dotenv"):
        try:
            from dotenv import load_dotenv
            root_path = get_root_path()
            dotenv_path = Path(root_path).joinpath(".env")
            if dotenv_path.exists() and dotenv_path.is_file():
                load_dotenv(dotenv_path)
                # print(os.environ)
        except:
            pass


def get_root_path():
    return os.environ.get(ENV_WWA_ROOT_PATH)


def set_log_path(value: str):
    os.environ[ENV_WWA_LOG_PATH] = value


def get_log_path():
    return os.environ.get(ENV_WWA_LOG_PATH)  # x:/xxx/logs/wwa.log


def set_log_leader(value: bool):
    os.environ[ENV_WWA_LOG_LEADER] = str(value)


def get_log_leader():
    return os.environ.get(ENV_WWA_LOG_LEADER)  # "True" / None


def set_param_config_path(value: str):
    os.environ[ENV_WWA_PARAM_CONFIG_PATH] = value


def get_param_config_path():
    return os.environ.get(ENV_WWA_PARAM_CONFIG_PATH)  # x:/xxx/temp/config/param-config.json


def set_ocr_use_gpu(value: bool):
    os.environ[ENV_WWA_OCR_USE_GPU] = str(value)


def get_ocr_use_gpu():
    return os.environ.get(ENV_WWA_OCR_USE_GPU)  # "True" / None
