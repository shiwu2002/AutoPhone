"""工具集模块 - 按功能域分类的工具实现。"""

from phone_agent.actions.registry import get_registry

# 延迟导入具体处理器
from phone_agent.actions.sets.adb_ui import handle_tap, handle_double_tap, handle_long_press, handle_swipe
from phone_agent.actions.sets.adb_navigation import handle_back, handle_home, handle_wait
from phone_agent.actions.sets.app_management import handle_launch
from phone_agent.actions.sets.input_tools import handle_type
from phone_agent.actions.sets.file_tools import handle_read_excel, handle_execute_excel_batch
from phone_agent.actions.sets.system_tools import handle_takeover, handle_interact, handle_note, handle_call_api

# 获取全局注册表并批量注册（向后兼容）
_registry = get_registry()
_registry.register_bulk({
    # ADB UI
    "Tap": handle_tap,
    "Double Tap": handle_double_tap,
    "Long Press": handle_long_press,
    "Swipe": handle_swipe,
    # Navigation
    "Back": handle_back,
    "Home": handle_home,
    "Wait": handle_wait,
    # App Management
    "Launch": handle_launch,
    # Input
    "Type": handle_type,
    "Type_Name": handle_type,
    # File Tools
    "ReadExcel": handle_read_excel,
    "Execute_Excel_Batch": handle_execute_excel_batch,
    # System Tools
    "Take_over": handle_takeover,
    "Interact": handle_interact,
    "Note": handle_note,
    "Call_API": handle_call_api,
})

# 向后兼容：保留 TOOL_HANDLERS 字典
TOOL_HANDLERS = _registry._handlers

__all__ = [
    "TOOL_HANDLERS",
    "handle_tap",
    "handle_double_tap",
    "handle_long_press",
    "handle_swipe",
    "handle_back",
    "handle_home",
    "handle_wait",
    "handle_launch",
    "handle_type",
    "handle_read_excel",
    "handle_execute_excel_batch",
    "handle_takeover",
    "handle_interact",
    "handle_note",
    "handle_call_api",
]
