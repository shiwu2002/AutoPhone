"""
PhoneAgent Tools Skill - 主技能执行逻辑

此技能集用于管理 PhoneAgent 的核心功能，包括：
- ADB 设备连接/断开
- 模型配置管理
- 任务执行
- 历史记录查询
"""

import json
from pathlib import Path
from typing import Any, Optional

# 导入 PhoneAgent 相关模块
try:
    from phone_agent import PhoneAgent
    from phone_agent.agent import AgentConfig
    from phone_agent.model import ModelConfig
    from phone_agent.history import get_history_manager
    from phone_agent.adb.connection import ADBConnection
    from phone_agent.device_factory import get_device_factory
    PHONE_AGENT_AVAILABLE = True
except ImportError:
    PHONE_AGENT_AVAILABLE = False
    print("Warning: PhoneAgent modules not available, some features will be limited")


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


def _build_model_config(config: dict, override: dict = None) -> Optional['ModelConfig']:
    """构建模型配置。"""
    if not PHONE_AGENT_AVAILABLE:
        return None

    if override:
        model_config_data = {**config.get('model', {}), **override}
        agent_config_data = {**config.get('agent', {}), **override.get('agent', {})}
    else:
        model_config_data = config.get('model', {})
        agent_config_data = config.get('agent', {})

    provider = model_config_data.get('provider', 'local')
    provider_config = model_config_data.get(provider, {})

    return ModelConfig(
        base_url=model_config_data.get('base_url') or provider_config.get('base_url', 'http://localhost:8000/v1'),
        model_name=model_config_data.get('model_name') or provider_config.get('model', 'qwen3.5:4b'),
        api_key=model_config_data.get('api_key') or provider_config.get('api_key', 'EMPTY'),
        use_thinking=model_config_data.get('use_thinking', False),
        lang=agent_config_data.get('lang', 'cn'),
        provider=provider,
    )


def _build_agent_config(config: dict, override: dict = None) -> Optional['AgentConfig']:
    """构建代理配置。"""
    if not PHONE_AGENT_AVAILABLE:
        return None

    if override:
        agent_config_data = {**config.get('agent', {}), **override.get('agent', {})}
    else:
        agent_config_data = config.get('agent', {})

    return AgentConfig(
        max_steps=int(agent_config_data.get('max_steps', 100)),
        device_id=agent_config_data.get('device_id'),
        lang=agent_config_data.get('lang', 'cn'),
        verbose=bool(agent_config_data.get('verbose', True)),
    )


def adb_connect_execute(connection_request: str, device_address: str = None) -> dict:
    """
    ADB 设备连接技能执行函数
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {"success": False, "error": "PhoneAgent modules not available"}

        conn = ADBConnection()

        if device_address:
            success, message = conn.connect(device_address)
            if not success:
                return {"success": False, "error": message}

        devices = get_device_factory().list_devices()

        if not devices:
            return {
                "success": False,
                "error": "没有可用的设备，请先连接 ADB 设备（USB 或无线）"
            }

        device = devices[0]
        return {
            "success": True,
            "device_id": device.device_id,
            "device_model": device.model or "Unknown",
            "connection_type": device.connection_type.value,
            "message": f"成功连接到设备 {device.device_id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def adb_disconnect_execute(device_address: str = None) -> dict:
    """
    ADB 设备断开技能执行函数
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {"success": False, "error": "PhoneAgent modules not available"}

        conn = ADBConnection()
        address = device_address if device_address else 'all'
        success, message = conn.disconnect(address if address != 'all' else None)

        return {"success": success, "message": message}

    except Exception as e:
        return {"success": False, "error": str(e)}


def model_config_execute(current_config: str = None, config_request: str = None) -> dict:
    """
    模型配置管理技能执行函数
    """
    try:
        config = _load_config()

        if config_request:
            try:
                new_config = json.loads(config_request)

                if 'provider' in new_config:
                    config['model'] = config.get('model', {})
                    config['model']['provider'] = new_config['provider']

                if 'model_name' in new_config:
                    provider = config.get('model', {}).get('provider', 'local')
                    if provider not in config['model']:
                        config['model'][provider] = {}
                    config['model'][provider]['model'] = new_config['model_name']

                if 'base_url' in new_config:
                    provider = config.get('model', {}).get('provider', 'local')
                    if provider not in config['model']:
                        config['model'][provider] = {}
                    config['model'][provider]['base_url'] = new_config['base_url']

                if 'api_key' in new_config:
                    provider = config.get('model', {}).get('provider', 'local')
                    if provider not in config['model']:
                        config['model'][provider] = {}
                    config['model'][provider]['api_key'] = new_config['api_key']

                if _save_config(config):
                    return {
                        "success": True,
                        "provider": config.get('model', {}).get('provider', 'local'),
                        "model_name": config.get('model', {}).get(
                            config.get('model', {}).get('provider', 'local'), {}
                        ).get('model', 'qwen3.5:4b'),
                        "base_url": config.get('model', {}).get(
                            config.get('model', {}).get('provider', 'local'), {}
                        ).get('base_url', 'http://localhost:11434/v1'),
                        "message": "配置已更新并保存"
                    }
                else:
                    return {"success": False, "error": "保存配置失败"}

            except json.JSONDecodeError:
                return {
                    "success": True,
                    "provider": config.get('model', {}).get('provider', 'local'),
                    "model_name": config.get('model', {}).get(
                        config.get('model', {}).get('provider', 'local'), {}
                    ).get('model', 'qwen3.5:4b'),
                    "message": f"配置请求已接收：{config_request}（需要更具体的配置参数）"
                }

        provider = config.get('model', {}).get('provider', 'local')
        provider_config = config.get('model', {}).get(provider, {})

        return {
            "success": True,
            "provider": provider,
            "model_name": provider_config.get('model', 'qwen3.5:4b'),
            "base_url": provider_config.get('base_url', 'http://localhost:11434/v1'),
            "current_config": config
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_task_execute(
    task: str,
    model_provider: str = None,
    model_name: str = None,
    device_id: str = None,
    max_steps: int = None
) -> dict:
    """
    执行手机任务技能执行函数
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {"success": False, "error": "PhoneAgent modules not available"}

        config = _load_config()

        override = {}
        if model_provider:
            override['provider'] = model_provider
        if model_name:
            provider = model_provider or config.get('model', {}).get('provider', 'local')
            if provider not in override:
                override[provider] = {}
            override[provider] = override.get(provider, {})
            override[provider]['model'] = model_name

        model_config = _build_model_config(config, override if override else None)
        agent_config = _build_agent_config(config)

        if device_id:
            agent_config.device_id = device_id
        if max_steps:
            agent_config.max_steps = max_steps

        devices = get_device_factory().list_devices()
        if not devices:
            return {"success": False, "error": "没有可用的 ADB 设备"}

        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
        result = agent.run(task)

        return {
            "success": True,
            "result": result,
            "steps_executed": agent.step_count,
            "message": "任务执行完成"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def query_history_execute(
    limit: int = 100,
    success_filter: str = "all",
    keyword: str = None
) -> dict:
    """
    查询历史记录技能执行函数
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {"success": False, "error": "PhoneAgent modules not available"}

        history_mgr = get_history_manager()

        if keyword:
            records = history_mgr.search_records(keyword, limit=limit)
        elif success_filter == 'true':
            records = history_mgr.get_successful_records(limit=limit)
        elif success_filter == 'false':
            records = history_mgr.get_failed_records(limit=limit)
        else:
            records = history_mgr.get_all_records(limit=limit)

        records_list = []
        for record in records:
            record_dict = record.to_dict()
            records_list.append({
                "task": record_dict.get('task', ''),
                "success": record_dict.get('success', False),
                "timestamp": record_dict.get('timestamp', ''),
                "steps": record_dict.get('steps', 0)
            })

        return {
            "success": True,
            "count": len(records_list),
            "records": records_list
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_stats_execute() -> dict:
    """
    获取统计信息技能执行函数
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {"success": False, "error": "PhoneAgent modules not available"}

        history_mgr = get_history_manager()
        stats = history_mgr.get_statistics()

        return {"success": True, "statistics": stats}

    except Exception as e:
        return {"success": False, "error": str(e)}


def clear_history_execute() -> dict:
    """
    清空历史记录技能执行函数
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {"success": False, "error": "PhoneAgent modules not available"}

        history_mgr = get_history_manager()

        if history_mgr.clear_all():
            return {"success": True, "message": "所有历史记录已清空"}
        else:
            return {"success": False, "error": "清空历史记录失败"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# 主执行函数
def execute(sub_skill_id: str, **kwargs) -> dict:
    """
    PhoneAgent Tools 主执行函数

    Args:
        sub_skill_id: 子技能 ID
        **kwargs: 子技能参数

    Returns:
        dict: 执行结果
    """
    executors = {
        "adb_connect": adb_connect_execute,
        "adb_disconnect": adb_disconnect_execute,
        "model_config": model_config_execute,
        "execute_task": execute_task_execute,
        "query_history": query_history_execute,
        "get_stats": get_stats_execute,
        "clear_history": clear_history_execute,
    }

    if sub_skill_id not in executors:
        return {"success": False, "error": f"未知的子技能：{sub_skill_id}"}

    executor = executors[sub_skill_id]
    return executor(**kwargs)
