"""工具集模块 - 按功能域分类的工具实现。"""

# 延迟导入，避免循环导入
from phone_agent.actions.sets.adb_ui import handle_tap, handle_double_tap, handle_long_press, handle_swipe
from phone_agent.actions.sets.adb_navigation import handle_back, handle_home, handle_wait
from phone_agent.actions.sets.app_management import handle_launch
from phone_agent.actions.sets.input_tools import handle_type
from phone_agent.actions.sets.file_tools import handle_read_excel, handle_execute_excel_batch
from phone_agent.actions.sets.system_tools import handle_takeover, handle_interact, handle_note, handle_call_api

# 工具名称到处理函数的映射
TOOL_HANDLERS = {
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
}

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
