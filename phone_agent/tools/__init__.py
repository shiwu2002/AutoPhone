"""PhoneAgent 工具模块。"""

# 延迟导入 Excel 工具，避免循环导入
# from phone_agent.tools.excel_tool import ExcelTool, execute_excel_batch, ExcelBatchResult
from phone_agent.tools.registry import (
    ToolRegistry,
    ToolMetadata,
    ToolSetMetadata,
    get_registry,
    list_tool_sets,
    get_tool_set_info,
    get_tool_details,
)

__all__ = [
    # Excel tools (延迟导入)
    # "ExcelTool",
    # "execute_excel_batch",
    # "ExcelBatchResult",
    # Registry
    "ToolRegistry",
    "ToolMetadata",
    "ToolSetMetadata",
    "get_registry",
    "list_tool_sets",
    "get_tool_set_info",
    "get_tool_details",
]
