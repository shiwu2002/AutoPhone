"""
PhoneAgent Tools Skill - 主技能执行逻辑

此技能集用于管理 PhoneAgent 的核心功能，包括：
- ADB 设备连接/断开
- 模型配置管理
- 任务执行
- 历史记录查询
- Excel 批量处理
"""

import json
import subprocess
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

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available, Excel features will be limited")


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

    Args:
        connection_request: 连接请求描述
        device_address: 设备地址（无线连接时使用）

    Returns:
        dict: 连接结果
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        conn = ADBConnection()

        # 如果需要连接远程设备
        if device_address:
            success, message = conn.connect(device_address)
            if not success:
                return {"success": False, "error": message}

        # 获取设备列表
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

    Args:
        device_address: 设备地址（可选，不填则断开所有）

    Returns:
        dict: 断开结果
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        conn = ADBConnection()
        address = device_address if device_address else 'all'
        success, message = conn.disconnect(address if address != 'all' else None)

        return {
            "success": success,
            "message": message
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def model_config_execute(current_config: str = None, config_request: str = None) -> dict:
    """
    模型配置管理技能执行函数

    Args:
        current_config: 当前配置 JSON 字符串
        config_request: 配置请求描述

    Returns:
        dict: 配置结果
    """
    try:
        config = _load_config()

        # 如果有新的配置请求，解析并更新
        if config_request:
            try:
                # 尝试解析 JSON 格式的配置请求
                new_config = json.loads(config_request)

                # 更新模型配置
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

                # 保存配置
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
                # 如果不是 JSON 格式，尝试解析自然语言请求
                return {
                    "success": True,
                    "provider": config.get('model', {}).get('provider', 'local'),
                    "model_name": config.get('model', {}).get(
                        config.get('model', {}).get('provider', 'local'), {}
                    ).get('model', 'qwen3.5:4b'),
                    "message": f"配置请求已接收：{config_request}（需要更具体的配置参数）"
                }

        # 返回当前配置
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

    Args:
        task: 任务描述
        model_provider: 模型提供商
        model_name: 模型名称
        device_id: 设备 ID
        max_steps: 最大执行步数

    Returns:
        dict: 任务执行结果
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        config = _load_config()

        # 构建覆盖配置
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

        # 检查设备
        devices = get_device_factory().list_devices()
        if not devices:
            return {"success": False, "error": "没有可用的 ADB 设备"}

        # 创建并执行任务
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

    Args:
        limit: 返回记录数量限制
        success_filter: 成功状态过滤（true/false/all）
        keyword: 搜索关键词

    Returns:
        dict: 历史记录列表
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        history_mgr = get_history_manager()

        if keyword:
            records = history_mgr.search_records(keyword, limit=limit)
        elif success_filter == 'true':
            records = history_mgr.get_successful_records(limit=limit)
        elif success_filter == 'false':
            records = history_mgr.get_failed_records(limit=limit)
        else:
            records = history_mgr.get_all_records(limit=limit)

        # 转换为字典格式
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

    Returns:
        dict: 统计信息
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        history_mgr = get_history_manager()
        stats = history_mgr.get_statistics()

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def clear_history_execute() -> dict:
    """
    清空历史记录技能执行函数

    Returns:
        dict: 清空结果
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        history_mgr = get_history_manager()

        if history_mgr.clear_all():
            return {
                "success": True,
                "message": "所有历史记录已清空"
            }
        else:
            return {"success": False, "error": "清空历史记录失败"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def excel_preview_execute(file_path: str, question_column: str = None) -> dict:
    """
    Excel 文件预览技能执行函数

    Args:
        file_path: Excel 文件路径
        question_column: 问题列名（可选）

    Returns:
        dict: Excel 预览信息
    """
    try:
        if not PANDAS_AVAILABLE:
            return {
                "success": False,
                "error": "pandas not available"
            }

        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file_path}"}

        df = pd.read_excel(path)
        columns = df.columns.tolist()

        # 自动检测问题列
        if not question_column:
            for col in columns:
                col_lower = col.lower()
                if '问题' in col_lower or 'question' in col_lower:
                    question_column = col
                    break
            if not question_column:
                question_column = columns[0] if columns else None

        if not question_column:
            return {"success": False, "error": "无法确定问题列"}

        questions = df[question_column].dropna().astype(str).tolist()
        questions = [q.strip() for q in questions if q.strip() and q != 'nan']

        return {
            "success": True,
            "columns": columns,
            "question_column": question_column,
            "questions": questions,
            "count": len(questions)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def excel_batch_execute(
    file_path: str,
    task_template: str,
    output_file: str = None,
    embed_screenshot: bool = False,
    column: str = None
) -> dict:
    """
    Excel 批量任务执行技能执行函数

    Args:
        file_path: Excel 文件路径
        task_template: 任务模板描述
        output_file: 输出文件路径
        embed_screenshot: 是否嵌入截图
        column: 问题列名

    Returns:
        dict: 批量执行结果
    """
    try:
        if not PHONE_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "PhoneAgent modules not available"
            }

        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not available"}

        # 导入 Excel 批量处理函数
        try:
            from bin.excel_task import process_excel_questions
        except ImportError:
            return {"success": False, "error": "Excel batch processing module not available"}

        config = _load_config()
        model_cfg = _build_model_config(config)
        agent_cfg = _build_agent_config(config)

        output_path = output_file or file_path

        results = process_excel_questions(
            excel_path=file_path,
            task_template=task_template,
            output_path=output_path,
            model_cfg=model_cfg,
            agent_cfg=agent_cfg,
            embed_screenshot=embed_screenshot,
            column=column
        )

        # 转换结果格式
        formatted_results = []
        success_count = 0
        for r in results:
            formatted_results.append({
                "question": r.get('question', ''),
                "answer": r.get('answer', ''),
                "success": r.get('success', False)
            })
            if r.get('success', False):
                success_count += 1

        return {
            "success": True,
            "results": formatted_results,
            "output_file": output_path,
            "statistics": {
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# 主执行函数，根据 sub_skill_id 分发到不同的执行函数
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
        "excel_preview": excel_preview_execute,
        "excel_batch": excel_batch_execute,
    }

    if sub_skill_id not in executors:
        return {"success": False, "error": f"未知的子技能：{sub_skill_id}"}

    executor = executors[sub_skill_id]
    return executor(**kwargs)
