"""配置加载与管理模块 - 支持环境变量和配置合并。"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ProviderConfig:
    """单个模型提供商的配置。"""
    base_url: str
    model: str
    api_key: str = ""
    max_tokens: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfig":
        return cls(
            base_url=data.get("base_url", ""),
            model=data.get("model", ""),
            api_key=data.get("api_key", ""),
            max_tokens=data.get("max_tokens")
        )


@dataclass
class ModelConfig:
    """模型配置。"""
    provider: str = "local"
    use_thinking: bool = False
    providers: dict[str, ProviderConfig] = field(default_factory=dict)

    def get_provider_config(self, provider_name: str = None) -> ProviderConfig:
        """获取指定提供商的配置，默认为当前 provider。"""
        name = provider_name or self.provider
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not configured")
        return self.providers[name]

    @classmethod
    def from_dict(cls, data: dict) -> "ModelConfig":
        providers_data = data.get("providers", {})
        providers = {name: ProviderConfig.from_dict(cfg) for name, cfg in providers_data.items()}

        return cls(
            provider=data.get("provider", "local"),
            use_thinking=data.get("use_thinking", False),
            providers=providers
        )


@dataclass
class AgentConfig:
    """Agent 配置。"""
    max_steps: int = 0
    device_id: Optional[str] = None
    verbose: bool = True
    lang: str = "cn"
    max_context_rounds: int = 5
    remember_app_info: bool = True
    max_repeated_actions: int = 3
    enable_repeat_detection: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        return cls(
            max_steps=data.get("max_steps", 0),
            device_id=data.get("device_id"),
            verbose=data.get("verbose", True),
            lang=data.get("lang", "cn"),
            max_context_rounds=data.get("max_context_rounds", 5),
            remember_app_info=data.get("remember_app_info", True),
            max_repeated_actions=data.get("max_repeated_actions", 3),
            enable_repeat_detection=data.get("enable_repeat_detection", True)
        )


@dataclass
class DeviceConfig:
    """设备配置。"""
    type: str = "adb"
    remote_address: Optional[str] = None
    auto_connect: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceConfig":
        return cls(
            type=data.get("type", "adb"),
            remote_address=data.get("remote_address"),
            auto_connect=data.get("auto_connect", True)
        )


@dataclass
class ServerConfig:
    """Server 配置。"""
    host: str = "0.0.0.0"
    port: int = 5001
    enable_cors: bool = True
    auth_enabled: bool = False
    auth_token: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ServerConfig":
        return cls(
            host=data.get("host", "0.0.0.0"),
            port=data.get("port", 5001),
            enable_cors=data.get("enable_cors", True),
            auth_enabled=data.get("auth_enabled", False),
            auth_token=data.get("auth_token", "")
        )


class ConfigManager:
    """
    配置管理器 - 统一处理配置加载和环境变量覆盖。

    优先级：环境变量 > config.json > 默认值
    """

    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

    # 环境变量映射
    ENV_MAPPING = {
        "AUTOPHONE_PROVIDER": ("model", "provider"),
        "AUTOPHONE_BASE_URL": ("model", "providers", "local", "base_url"),
        "AUTOPHONE_MODEL": ("model", "providers", "local", "model"),
        "AUTOPHONE_API_KEY": ("model", "providers", "local", "api_key"),
        "AUTOPHONE_ANTHROPIC_API_KEY": ("model", "providers", "anthropic", "api_key"),
        "AUTOPHONE_OPENAI_API_KEY": ("model", "providers", "openai", "api_key"),
        "AUTOPHONE_OLLAMA_URL": ("model", "providers", "local", "base_url"),
        "AUTOPHONE_OLLAMA_MODEL": ("model", "providers", "local", "model"),
        "AUTOPHONE_DEVICE_ID": ("agent", "device_id"),
        "AUTOPHONE_LANG": ("agent", "lang"),
        "AUTOPHONE_VERBOSE": ("agent", "verbose"),
        "AUTOPHONE_SERVER_HOST": ("server", "host"),
        "AUTOPHONE_SERVER_PORT": ("server", "port"),
        "AUTOPHONE_SERVER_TOKEN": ("server", "auth_token"),
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._raw_config: dict = {}
        self._load_config()
        self._apply_env_overrides()

    def _load_config(self) -> None:
        """从文件加载配置。"""
        if not self.config_path.exists():
            self._raw_config = self._get_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._raw_config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  配置文件加载失败：{e}，使用默认配置")
            self._raw_config = self._get_default_config()

    def _get_default_config(self) -> dict:
        """返回默认配置。"""
        return {
            "model": {
                "provider": "local",
                "use_thinking": False,
                "providers": {
                    "local": {
                        "base_url": "http://localhost:11434/v1",
                        "model": "qwen3.5:4b",
                        "api_key": "ollama"
                    }
                }
            },
            "agent": {
                "max_steps": 0,
                "verbose": True,
                "lang": "cn"
            },
            "device": {
                "type": "adb",
                "auto_connect": True
            },
            "server": {
                "host": "0.0.0.0",
                "port": 5001,
                "auth_enabled": False
            }
        }

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖。"""
        for env_var, path in self.ENV_MAPPING.items():
            value = os.environ.get(env_var)
            if value:
                self._set_nested_value(path, value)

    def _set_nested_value(self, path: tuple, value: str) -> None:
        """设置嵌套配置值。"""
        config = self._raw_config
        for key in path[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        last_key = path[-1]
        # 类型转换
        current = config.get(last_key)
        if isinstance(current, bool):
            config[last_key] = value.lower() in ("true", "1", "yes")
        elif isinstance(current, int):
            config[last_key] = int(value)
        elif isinstance(current, float):
            config[last_key] = float(value)
        else:
            config[last_key] = value

    def get(self, *path, default=None):
        """
        获取配置值，支持嵌套路径。

        Example:
            config.get("model", "provider")
            config.get("server", "host", default="localhost")
        """
        value = self._raw_config
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def model(self) -> ModelConfig:
        """获取模型配置。"""
        return ModelConfig.from_dict(self._raw_config.get("model", {}))

    @property
    def agent(self) -> AgentConfig:
        """获取 Agent 配置。"""
        return AgentConfig.from_dict(self._raw_config.get("agent", {}))

    @property
    def device(self) -> DeviceConfig:
        """获取设备配置。"""
        return DeviceConfig.from_dict(self._raw_config.get("device", {}))

    @property
    def server(self) -> ServerConfig:
        """获取 Server 配置。"""
        return ServerConfig.from_dict(self._raw_config.get("server", {}))

    def get_model_credentials(self, provider: str = None) -> dict:
        """
        获取模型凭据，优先从环境变量读取。
        兼容旧格式 (model.openai) 和新格式 (model.providers.openai)。

        Returns:
            包含 api_key 和 base_url 的字典
        """
        provider_name = provider or self.get("model", "provider", default="local")

        # 尝试新格式：model.providers.{provider}
        provider_config = self.get("model", "providers", provider_name, default={})

        # 如果新格式为空，尝试旧格式：model.{provider}
        if not provider_config:
            provider_config = self.get("model", provider_name, default={})

        # 环境变量优先
        if provider_name == "anthropic":
            api_key = os.environ.get("AUTOPHONE_ANTHROPIC_API_KEY") or provider_config.get("api_key", "")
        elif provider_name == "openai":
            api_key = os.environ.get("AUTOPHONE_OPENAI_API_KEY") or provider_config.get("api_key", "")
        else:
            api_key = os.environ.get("AUTOPHONE_API_KEY") or provider_config.get("api_key", "")

        return {
            "api_key": api_key,
            "base_url": provider_config.get("base_url", ""),
            "model": provider_config.get("model", "")
        }

    def save(self, path: Optional[Path] = None) -> None:
        """保存配置到文件。"""
        save_path = path or self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._raw_config, f, indent=2, ensure_ascii=False)


# 全局单例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Path] = None) -> ConfigManager:
    """获取全局配置管理器实例。"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def reload_config(config_path: Optional[Path] = None) -> ConfigManager:
    """重新加载配置。"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
