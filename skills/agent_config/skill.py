"""
Agent Config - 智能体配置技能执行模块

配置问答智能体所需的 ADB 连接、模型参数等信息。
"""

import json
from pathlib import Path
from typing import Any


def _load_config() -> dict:
    """从配置文件加载配置。"""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def _save_config(config: dict) -> bool:
    """保存配置到文件。"""
    config_path = Path(__file__).parent.parent / "config.json"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def set_device_execute(device_address: str = None, connection_type: str = "usb") -> dict:
    """
    配置设备连接技能执行函数
    """
    try:
        from phone_agent.adb.connection import ADBConnection
        from phone_agent.device_factory import get_device_factory

        config = _load_config()

        # 如果需要连接远程设备
        if device_address and connection_type == "wireless":
            conn = ADBConnection()
            success, message = conn.connect(device_address)
            if not success:
                return {"success": False, "error": message}

        # 获取设备列表
        devices = get_device_factory().list_devices()

        if devices:
            device = devices[0]
            result = {
                "success": True,
                "device_id": device.device_id,
                "connection_type": device.connection_type.value,
                "message": f"成功连接到设备 {device.device_id}"
            }
        else:
            result = {
                "success": connection_type == "wireless",
                "device_id": None,
                "connection_type": connection_type,
                "message": "无线连接配置已保存，但未检测到设备"
            }

        # 保存设备配置
        config['agent'] = config.get('agent', {})
        config['agent']['device_id'] = result.get('device_id')
        _save_config(config)

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def set_model_execute(
    provider: str = "local",
    model_name: str = "qwen3.5:4b",
    base_url: str = None,
    api_key: str = None
) -> dict:
    """
    配置模型技能执行函数
    """
    try:
        config = _load_config()

        # 确保 model 配置存在
        if 'model' not in config:
            config['model'] = {}

        # 设置提供商
        config['model']['provider'] = provider

        # 设置提供商具体配置
        if provider not in config['model']:
            config['model'][provider] = {}

        if model_name:
            config['model'][provider]['model'] = model_name
        if base_url:
            config['model'][provider]['base_url'] = base_url
        if api_key:
            config['model'][provider]['api_key'] = api_key

        # 保存配置
        if _save_config(config):
            return {
                "success": True,
                "provider": provider,
                "model_name": model_name,
                "base_url": base_url or config['model'][provider].get('base_url'),
                "message": "模型配置已保存"
            }
        else:
            return {"success": False, "error": "保存配置失败"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def set_params_execute(
    max_steps: int = 100,
    lang: str = "cn",
    verbose: bool = True
) -> dict:
    """
    配置参数技能执行函数
    """
    try:
        config = _load_config()

        # 确保 agent 配置存在
        if 'agent' not in config:
            config['agent'] = {}

        # 设置参数
        config['agent']['max_steps'] = max_steps
        config['agent']['lang'] = lang
        config['agent']['verbose'] = verbose

        # 保存配置
        if _save_config(config):
            return {
                "success": True,
                "max_steps": max_steps,
                "lang": lang,
                "verbose": verbose,
                "message": "参数配置已保存"
            }
        else:
            return {"success": False, "error": "保存配置失败"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_config_execute() -> dict:
    """
    获取配置技能执行函数
    """
    try:
        config = _load_config()

        return {
            "success": True,
            "config": {
                "device": {
                    "device_id": config.get('agent', {}).get('device_id'),
                    "type": config.get('device', {}).get('type', 'adb')
                },
                "model": {
                    "provider": config.get('model', {}).get('provider', 'local'),
                    "model_name": config.get('model', {}).get(
                        config.get('model', {}).get('provider', 'local'), {}
                    ).get('model', 'qwen3.5:4b'),
                    "base_url": config.get('model', {}).get(
                        config.get('model', {}).get('provider', 'local'), {}
                    ).get('base_url', 'http://localhost:11434/v1')
                },
                "agent": {
                    "max_steps": config.get('agent', {}).get('max_steps', 100),
                    "lang": config.get('agent', {}).get('lang', 'cn'),
                    "verbose": config.get('agent', {}).get('verbose', True)
                }
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute(sub_skill_id: str, **kwargs) -> dict:
    """
    Agent Config 主执行函数
    """
    executors = {
        "set_device": set_device_execute,
        "set_model": set_model_execute,
        "set_params": set_params_execute,
        "get_config": get_config_execute,
    }

    if sub_skill_id not in executors:
        return {"success": False, "error": f"未知的子技能：{sub_skill_id}"}

    executor = executors[sub_skill_id]
    return executor(**kwargs)
