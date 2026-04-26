#!/usr/bin/env python3
"""
AutoPhone MCP Server

基于 Model Context Protocol (MCP) 的手机自动化服务器。
仅暴露 2 个 MCP 工具：tool_catalog（工具目录）和 call_tool（调度调用）。
远程智能体先获取目录，再按需调用具体工具。

支持 stdio 和 SSE 两种传输模式。

启动方式:
  # stdio 模式（本地调用）
  python -m phone_agent.mcp_server

  # SSE 网络模式（远程调用）
  python -m phone_agent.mcp_server --transport sse --host 0.0.0.0 --port 8080

  # CLI 命令
  autophone mcp
  autophone mcp --transport sse --port 8080
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from phone_agent.device_factory import DeviceType, get_device_factory, set_device_type
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)

CONFIG_PATH = str(Path(__file__).parent.parent / "config.json")

mcp = FastMCP(
    "AutoPhone",
    instructions=(
        "AutoPhone 是一个基于视觉语言模型的 Android 手机自动化工具。\n"
        "使用方式：\n"
        "1. 先调用 tool_catalog 获取所有可用工具的目录和参数说明\n"
        "2. 再调用 call_tool 并传入工具名和参数来执行具体操作\n"
        "使用前请确保 ADB 已安装且设备已连接。"
    ),
)

_api_instance = None


def _get_api():
    global _api_instance
    if _api_instance is None:
        from phone_agent.api import PhoneAgentAPI
        _api_instance = PhoneAgentAPI(config_path=CONFIG_PATH)
    return _api_instance


def _get_factory():
    return get_device_factory()


def _dataclass_to_dict(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return str(obj)


# ============================================================
# 内部工具注册表
# ============================================================

TOOL_CATALOG: dict[str, dict[str, Any]] = {}


def _register_tool(
    name: str,
    description: str,
    category: str,
    parameters: dict[str, Any],
):
    def decorator(handler):
        TOOL_CATALOG[name] = {
            "name": name,
            "description": description,
            "category": category,
            "parameters": parameters,
        }
        handler._autophone_tool_name = name
        return handler
    return decorator


# ============================================================
# 核心自动化工具
# ============================================================


@_register_tool(
    name="run_task",
    description="在手机上执行一个自然语言描述的自动化任务。AI Agent 会自动截图、分析屏幕、执行操作，直到任务完成。例如：\"打开微信\"、\"给张三发送消息你好\"、\"打开设置并调高音量\"。",
    category="核心自动化",
    parameters={
        "task": {"type": "string", "description": "自然语言描述的任务，如 \"打开微信并给张三发消息\"", "required": True},
        "save_screenshot": {"type": "boolean", "description": "是否在完成后保存截图（返回 base64 数据）", "required": False, "default": False},
        "verbose": {"type": "boolean", "description": "是否输出详细日志", "required": False, "default": False},
    },
)
def _run_task(task: str, save_screenshot: bool = False, verbose: bool = False) -> str:
    try:
        api = _get_api()
        result = api.run_task(task=task, save_screenshot=save_screenshot, verbose=verbose)
        data = _dataclass_to_dict(result)
        if data.get("screenshot_base64"):
            data["screenshot_base64"] = data["screenshot_base64"][:100] + "...(truncated)"
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="run_batch_parallel",
    description="多设备并行执行批量任务。自动检测可用设备，将任务均匀分配到各设备并发执行。适用于需要同时处理多个问题的场景。",
    category="核心自动化",
    parameters={
        "questions": {"type": "array", "items": {"type": "string"}, "description": "问题/任务列表，如 [\"问题1\", \"问题2\", \"问题3\"]", "required": True},
        "task_template": {"type": "string", "description": "任务模板，用 {content} 作为占位符，如 \"请回答：{content}\"", "required": False, "default": "{content}"},
        "embed_screenshot": {"type": "boolean", "description": "是否在结果中保存截图", "required": False, "default": False},
        "verbose": {"type": "boolean", "description": "是否输出详细日志", "required": False, "default": False},
    },
)
def _run_batch_parallel(
    questions: list[str],
    task_template: str = "{content}",
    embed_screenshot: bool = False,
    verbose: bool = False,
) -> str:
    try:
        api = _get_api()
        result = api.run_batch_parallel(
            questions=questions,
            task_template=task_template,
            embed_screenshot=embed_screenshot,
            verbose=verbose,
        )
        data = _dataclass_to_dict(result)
        for r in data.get("results", []):
            if r.get("screenshot_base64"):
                r["screenshot_base64"] = r["screenshot_base64"][:100] + "...(truncated)"
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 设备管理工具
# ============================================================


@_register_tool(
    name="list_devices",
    description="列出所有通过 ADB 连接的 Android 设备。返回设备 ID、连接状态、连接类型（USB/WiFi）和型号信息。",
    category="设备管理",
    parameters={},
)
def _list_devices() -> str:
    try:
        factory = _get_factory()
        devices = factory.list_devices()
        result = [_dataclass_to_dict(d) for d in devices]
        for d in result:
            if "connection_type" in d and hasattr(d["connection_type"], "value"):
                d["connection_type"] = d["connection_type"].value
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="get_screenshot",
    description="获取设备当前屏幕截图。返回截图的 base64 编码数据和分辨率信息。",
    category="设备管理",
    parameters={
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
        "enable_compression": {"type": "boolean", "description": "是否压缩截图（推荐开启以减少传输量）", "required": False, "default": True},
    },
)
def _get_screenshot(device_id: str | None = None, enable_compression: bool = True) -> str:
    try:
        factory = _get_factory()
        screenshot = factory.get_screenshot(device_id=device_id, enable_compression=enable_compression)
        return json.dumps(
            {
                "base64_data": screenshot.base64_data,
                "width": screenshot.width,
                "height": screenshot.height,
                "original_width": screenshot.original_width,
                "original_height": screenshot.original_height,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="get_current_app",
    description="获取设备当前前台运行的应用名称。",
    category="设备管理",
    parameters={
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _get_current_app(device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        app_name = factory.get_current_app(device_id=device_id)
        return json.dumps({"current_app": app_name}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="connect_device",
    description="通过 WiFi/网络连接到 Android 设备。设备需先启用 TCP/IP 调试模式（adb tcpip 5555）。",
    category="设备管理",
    parameters={
        "address": {"type": "string", "description": "设备地址，格式为 \"IP:端口\"，如 \"192.168.1.100:5555\"", "required": True},
        "timeout": {"type": "integer", "description": "连接超时时间（秒）", "required": False, "default": 10},
    },
)
def _connect_device(address: str, timeout: int = 10) -> str:
    try:
        factory = _get_factory()
        conn_cls = factory.get_connection_class()
        conn = conn_cls()
        success, message = conn.connect(address, timeout=timeout)
        return json.dumps({"success": success, "message": message}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="disconnect_device",
    description="断开与远程 Android 设备的连接。",
    category="设备管理",
    parameters={
        "address": {"type": "string", "description": "要断开的设备地址，为 null 时断开所有连接", "required": False, "default": None},
    },
)
def _disconnect_device(address: str | None = None) -> str:
    try:
        factory = _get_factory()
        conn_cls = factory.get_connection_class()
        conn = conn_cls()
        success, message = conn.disconnect(address)
        return json.dumps({"success": success, "message": message}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 设备控制原语工具
# ============================================================


@_register_tool(
    name="tap",
    description="在屏幕指定坐标处点击。",
    category="设备控制",
    parameters={
        "x": {"type": "integer", "description": "点击的 X 坐标", "required": True},
        "y": {"type": "integer", "description": "点击的 Y 坐标", "required": True},
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _tap(x: int, y: int, device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.tap(x, y, device_id=device_id)
        return json.dumps({"success": True, "action": "tap", "x": x, "y": y}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="double_tap",
    description="在屏幕指定坐标处双击。",
    category="设备控制",
    parameters={
        "x": {"type": "integer", "description": "双击的 X 坐标", "required": True},
        "y": {"type": "integer", "description": "双击的 Y 坐标", "required": True},
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _double_tap(x: int, y: int, device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.double_tap(x, y, device_id=device_id)
        return json.dumps({"success": True, "action": "double_tap", "x": x, "y": y}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="long_press",
    description="在屏幕指定坐标处长按。",
    category="设备控制",
    parameters={
        "x": {"type": "integer", "description": "长按的 X 坐标", "required": True},
        "y": {"type": "integer", "description": "长按的 Y 坐标", "required": True},
        "duration_ms": {"type": "integer", "description": "长按持续时间（毫秒），默认 3000ms", "required": False, "default": 3000},
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _long_press(x: int, y: int, duration_ms: int = 3000, device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.long_press(x, y, duration_ms=duration_ms, device_id=device_id)
        return json.dumps(
            {"success": True, "action": "long_press", "x": x, "y": y, "duration_ms": duration_ms},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="swipe",
    description="在屏幕上从起点滑动到终点。",
    category="设备控制",
    parameters={
        "start_x": {"type": "integer", "description": "起点 X 坐标", "required": True},
        "start_y": {"type": "integer", "description": "起点 Y 坐标", "required": True},
        "end_x": {"type": "integer", "description": "终点 X 坐标", "required": True},
        "end_y": {"type": "integer", "description": "终点 Y 坐标", "required": True},
        "duration_ms": {"type": "integer", "description": "滑动持续时间（毫秒）", "required": False, "default": None},
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _swipe(
    start_x: int, start_y: int, end_x: int, end_y: int,
    duration_ms: int | None = None, device_id: str | None = None,
) -> str:
    try:
        factory = _get_factory()
        factory.swipe(start_x, start_y, end_x, end_y, duration_ms=duration_ms, device_id=device_id)
        return json.dumps(
            {"success": True, "action": "swipe", "start": [start_x, start_y], "end": [end_x, end_y], "duration_ms": duration_ms},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="type_text",
    description="在当前输入框中输入文本（支持中文）。使用 ADB Keyboard 输入法，支持中文和多语言输入。",
    category="设备控制",
    parameters={
        "text": {"type": "string", "description": "要输入的文本内容", "required": True},
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _type_text(text: str, device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.type_text(text, device_id=device_id)
        return json.dumps({"success": True, "action": "type_text", "text": text}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="clear_text",
    description="清除当前输入框中的文本。",
    category="设备控制",
    parameters={
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _clear_text(device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.clear_text(device_id=device_id)
        return json.dumps({"success": True, "action": "clear_text"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="launch_app",
    description="启动指定应用。支持中英文应用名，如 \"微信\"、\"Chrome\"、\"Settings\"。可通过 list_supported_apps 工具查看所有支持的应用。",
    category="设备控制",
    parameters={
        "app_name": {"type": "string", "description": "应用名称（中英文均可），如 \"微信\"、\"设置\"", "required": True},
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _launch_app(app_name: str, device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        success = factory.launch_app(app_name, device_id=device_id)
        return json.dumps(
            {"success": success, "action": "launch_app", "app_name": app_name},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="press_back",
    description="按返回键。",
    category="设备控制",
    parameters={
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _press_back(device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.back(device_id=device_id)
        return json.dumps({"success": True, "action": "back"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="press_home",
    description="按主页键（Home 键）。",
    category="设备控制",
    parameters={
        "device_id": {"type": "string", "description": "设备 ID，为 null 时使用默认设备", "required": False, "default": None},
    },
)
def _press_home(device_id: str | None = None) -> str:
    try:
        factory = _get_factory()
        factory.home(device_id=device_id)
        return json.dumps({"success": True, "action": "home"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 历史与配置工具
# ============================================================


@_register_tool(
    name="get_task_history",
    description="获取任务执行历史记录。",
    category="历史与配置",
    parameters={
        "limit": {"type": "integer", "description": "返回的最大记录数，默认 20", "required": False, "default": 20},
    },
)
def _get_task_history(limit: int = 20) -> str:
    try:
        from phone_agent.history import get_history_manager
        mgr = get_history_manager()
        records = mgr.get_all_records(limit=limit)
        result = [_dataclass_to_dict(r) for r in records]
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="get_task_statistics",
    description="获取任务执行的统计信息，包括总数、成功率、平均步数和耗时。",
    category="历史与配置",
    parameters={},
)
def _get_task_statistics() -> str:
    try:
        from phone_agent.history import get_history_manager
        mgr = get_history_manager()
        stats = mgr.get_statistics()
        return json.dumps(stats, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="search_task_history",
    description="搜索包含关键词的任务历史记录。",
    category="历史与配置",
    parameters={
        "keyword": {"type": "string", "description": "搜索关键词", "required": True},
        "limit": {"type": "integer", "description": "返回的最大记录数", "required": False, "default": 20},
    },
)
def _search_task_history(keyword: str, limit: int = 20) -> str:
    try:
        from phone_agent.history import get_history_manager
        mgr = get_history_manager()
        records = mgr.search_records(keyword, limit=limit)
        result = [_dataclass_to_dict(r) for r in records]
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="list_supported_apps",
    description="列出所有支持通过应用名启动的应用列表。返回应用名到包名的映射。",
    category="历史与配置",
    parameters={},
)
def _list_supported_apps() -> str:
    try:
        from phone_agent.config.apps import APP_PACKAGES
        return json.dumps(APP_PACKAGES, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@_register_tool(
    name="get_config",
    description="获取当前 AutoPhone 的配置信息（API Key 已脱敏）。",
    category="历史与配置",
    parameters={},
)
def _get_config() -> str:
    try:
        config_path = Path(CONFIG_PATH)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "anthropic" in config.get("model", {}):
                config["model"]["anthropic"]["api_key"] = "***"
            if "openai" in config.get("model", {}):
                config["model"]["openai"]["api_key"] = "***"
            return json.dumps(config, ensure_ascii=False, indent=2)
        return json.dumps({"error": "config.json not found"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# 工具名 -> 处理函数映射
# ============================================================

_TOOL_HANDLERS: dict[str, callable] = {
    "run_task": _run_task,
    "run_batch_parallel": _run_batch_parallel,
    "list_devices": _list_devices,
    "get_screenshot": _get_screenshot,
    "get_current_app": _get_current_app,
    "connect_device": _connect_device,
    "disconnect_device": _disconnect_device,
    "tap": _tap,
    "double_tap": _double_tap,
    "long_press": _long_press,
    "swipe": _swipe,
    "type_text": _type_text,
    "clear_text": _clear_text,
    "launch_app": _launch_app,
    "press_back": _press_back,
    "press_home": _press_home,
    "get_task_history": _get_task_history,
    "get_task_statistics": _get_task_statistics,
    "search_task_history": _search_task_history,
    "list_supported_apps": _list_supported_apps,
    "get_config": _get_config,
}


# ============================================================
# MCP 对外暴露的 2 个工具
# ============================================================


@mcp.tool()
def tool_catalog() -> str:
    """
    获取 AutoPhone 全部可用工具的目录。

    返回每个工具的名称、分类、功能描述和参数说明。
    调用方应先获取此目录，了解有哪些工具可用，
    然后通过 call_tool 按名称调用具体工具。

    Returns:
        JSON 格式的工具目录列表
    """
    categories = {}
    for name, info in TOOL_CATALOG.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "name": info["name"],
            "description": info["description"],
            "parameters": info["parameters"],
        })

    return json.dumps(
        {
            "server": "AutoPhone MCP Server",
            "version": "1.0.0",
            "total_tools": len(TOOL_CATALOG),
            "usage": "先调用 tool_catalog 获取目录，再调用 call_tool(name, arguments) 执行具体工具",
            "categories": categories,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def call_tool(name: str, arguments: dict[str, Any] | None = None) -> str:
    """
    按名称调用 AutoPhone 的具体工具。

    使用前请先调用 tool_catalog 获取完整的工具目录和参数说明。

    Args:
        name: 工具名称，如 "run_task"、"tap"、"get_screenshot" 等
        arguments: 工具参数字典，键为参数名，值为参数值。
                   例如: {"task": "打开微信"} 或 {"x": 100, "y": 200}
                   无参数的工具可省略或传空字典 {}

    Returns:
        工具执行结果的 JSON 字符串
    """
    if name not in TOOL_CATALOG:
        available = ", ".join(sorted(TOOL_CATALOG.keys()))
        return json.dumps(
            {
                "success": False,
                "error": f"未知工具: {name}",
                "available_tools": available,
                "hint": "请先调用 tool_catalog 获取所有可用工具的目录",
            },
            ensure_ascii=False,
            indent=2,
        )

    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return json.dumps({"success": False, "error": f"工具 {name} 的处理函数未注册"}, ensure_ascii=False)

    kwargs = arguments or {}

    catalog_info = TOOL_CATALOG[name]
    params_spec = catalog_info.get("parameters", {})
    required_params = [k for k, v in params_spec.items() if v.get("required", False)]
    missing = [p for p in required_params if p not in kwargs]
    if missing:
        return json.dumps(
            {
                "success": False,
                "error": f"工具 {name} 缺少必需参数: {', '.join(missing)}",
                "required_parameters": required_params,
                "all_parameters": params_spec,
            },
            ensure_ascii=False,
            indent=2,
        )

    try:
        result = handler(**kwargs)
        return result
    except TypeError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"参数类型错误: {e}",
                "tool": name,
                "expected_parameters": params_spec,
                "received_arguments": kwargs,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# MCP 资源
# ============================================================


@mcp.resource("autophone://screenshot")
def screenshot_resource() -> str:
    """获取当前设备屏幕截图（base64 编码的 PNG 图片）。"""
    try:
        factory = _get_factory()
        screenshot = factory.get_screenshot(enable_compression=True)
        return screenshot.base64_data
    except Exception as e:
        return f"Error getting screenshot: {e}"


@mcp.resource("autophone://devices")
def devices_resource() -> str:
    """获取当前已连接的设备列表。"""
    try:
        factory = _get_factory()
        devices = factory.list_devices()
        result = [_dataclass_to_dict(d) for d in devices]
        for d in result:
            if "connection_type" in d and hasattr(d["connection_type"], "value"):
                d["connection_type"] = d["connection_type"].value
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.resource("autophone://current-app")
def current_app_resource() -> str:
    """获取当前设备前台运行的应用名称。"""
    try:
        factory = _get_factory()
        app_name = factory.get_current_app()
        return json.dumps({"current_app": app_name}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.resource("autophone://statistics")
def statistics_resource() -> str:
    """获取任务执行统计信息。"""
    try:
        from phone_agent.history import get_history_manager
        mgr = get_history_manager()
        stats = mgr.get_statistics()
        return json.dumps(stats, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# MCP 提示模板
# ============================================================


@mcp.prompt()
def phone_automation(task: str) -> str:
    """生成手机自动化任务的提示模板。"""
    return (
        f"请帮我完成以下手机自动化任务：{task}\n\n"
        "使用步骤：\n"
        "1. 先调用 tool_catalog 获取所有可用工具的目录\n"
        "2. 根据目录中的工具描述，调用 call_tool(name, arguments) 执行具体操作\n\n"
        "常用工具示例：\n"
        "- call_tool('run_task', {{'task': '打开微信'}})  执行完整自动化任务\n"
        "- call_tool('get_screenshot', {{}})  获取当前屏幕截图\n"
        "- call_tool('tap', {{'x': 100, 'y': 200}})  点击坐标\n"
        "- call_tool('launch_app', {{'app_name': '微信'}})  启动应用\n"
    )


@mcp.prompt()
def batch_automation(tasks: str) -> str:
    """生成批量手机自动化任务的提示模板。"""
    return (
        f"请帮我批量执行以下手机任务：\n{tasks}\n\n"
        "使用步骤：\n"
        "1. 先调用 tool_catalog 获取所有可用工具的目录\n"
        "2. 调用 call_tool('run_batch_parallel', {{'questions': [...], 'task_template': '...'}}) 并行执行\n"
        "   或逐个调用 call_tool('run_task', {{'task': '...'}}) 执行\n"
    )


# ============================================================
# 启动入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="AutoPhone MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="传输模式：stdio（本地）或 sse（网络远程调用）",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="SSE 模式监听地址（默认 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="SSE 模式监听端口（默认 8080）",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="config.json 配置文件路径",
    )
    args = parser.parse_args()

    global CONFIG_PATH
    if args.config:
        CONFIG_PATH = args.config

    set_device_type(DeviceType.ADB)

    if args.transport == "sse":
        print(f"🚀 AutoPhone MCP Server 启动中（SSE 模式）...")
        print(f"📡 监听地址: http://{args.host}:{args.port}")
        print(f"🔗 SSE 端点: http://{args.host}:{args.port}/sse")
        print(f"📋 暴露工具: tool_catalog, call_tool")
        print(f"🔧 内部工具: {len(TOOL_CATALOG)} 个（通过 call_tool 调度）")
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
