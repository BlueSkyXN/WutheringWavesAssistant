from pydantic import BaseModel, Field

from src.config.app_config import AppConfig
from src.config.echo_config import EchoModel
from src.config.gui_config import ParamConfig
from src.config.keyboard_mapping_config import KeyboardMappingConfig


class Config(BaseModel):
    """ 所有的配置 """
    model_config = {"arbitrary_types_allowed": True}
    app: AppConfig = Field(default_factory=AppConfig.build, title="应用配置，旧版，仅旧版自动战斗在用")
    echo: EchoModel = Field(default_factory=EchoModel.build, title="声骸词条配置",
                            description="配置声骸合成和锁定需要的词条")
    keyboard_mapping: KeyboardMappingConfig = Field(default_factory=KeyboardMappingConfig, title="游戏内按键映射")
    param: ParamConfig = Field(default_factory=ParamConfig.build, title="新版参数配置")
