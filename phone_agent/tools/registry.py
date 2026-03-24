"""工具注册表 - 管理所有工具集和工具的元数据。"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolMetadata:
    """单个工具的元数据。"""
    name: str
    description: str
    parameters: dict[str, str]  # 参数名 -> 参数说明
    example: str  # 使用示例


@dataclass
class ToolSetMetadata:
    """工具集的元数据。"""
    id: str
    name: str
    description: str
    tools: list[ToolMetadata] = field(default_factory=list)
    index_prompt: str = ""  # 用于智能体理解何时使用该工具集的关键词


class ToolRegistry:
    """
    工具注册表，管理所有工具集和工具。

    提供渐进式工具查询功能：
    1. list_tool_sets() - 获取所有工具集索引
    2. get_tool_set_info(set_name) - 获取工具集详情
    3. get_tool_details(set_name, tool_name) - 获取具体工具用法
    """

    def __init__(self):
        self._tool_sets: dict[str, ToolSetMetadata] = {}
        self._tool_handlers: dict[str, Callable] = {}
        self._init_builtin_tool_sets()

    def _init_builtin_tool_sets(self) -> None:
        """初始化内置工具集。"""

        # ========== ADB UI 交互工具集 ==========
        adb_ui = ToolSetMetadata(
            id="adb_ui",
            name="ADB UI 交互工具集",
            description="用于屏幕点击、滑动等 UI 交互操作",
            index_prompt="点击、滑动、触摸、交互、UI",
            tools=[
                ToolMetadata(
                    name="Tap",
                    description="点击屏幕上的特定点",
                    parameters={
                        "element": "[x,y] 相对坐标 (0-1000)",
                        "message": "(可选) 重要操作说明"
                    },
                    example='do(action="Tap", element=[500,500])'
                ),
                ToolMetadata(
                    name="Double Tap",
                    description="双击屏幕上的特定点",
                    parameters={"element": "[x,y] 相对坐标 (0-1000)"},
                    example='do(action="Double Tap", element=[500,500])'
                ),
                ToolMetadata(
                    name="Long Press",
                    description="长按屏幕上的特定点",
                    parameters={"element": "[x,y] 相对坐标 (0-1000)"},
                    example='do(action="Long Press", element=[500,500])'
                ),
                ToolMetadata(
                    name="Swipe",
                    description="滑动屏幕",
                    parameters={
                        "start": "[x1,y1] 起始坐标",
                        "end": "[x2,y2] 结束坐标"
                    },
                    example='do(action="Swipe", start=[500,800], end=[500,200])'
                ),
            ]
        )
        self._tool_sets["adb_ui"] = adb_ui

        # ========== ADB 导航工具集 ==========
        adb_nav = ToolSetMetadata(
            id="adb_navigation",
            name="ADB 导航工具集",
            description="用于页面导航和等待操作",
            index_prompt="导航、返回、主页、等待、页面",
            tools=[
                ToolMetadata(
                    name="Back",
                    description="返回上一级页面",
                    parameters={},
                    example='do(action="Back")'
                ),
                ToolMetadata(
                    name="Home",
                    description="回到系统桌面",
                    parameters={},
                    example='do(action="Home")'
                ),
                ToolMetadata(
                    name="Wait",
                    description="等待页面加载",
                    parameters={"duration": "等待秒数"},
                    example='do(action="Wait", duration="3 seconds")'
                ),
            ]
        )
        self._tool_sets["adb_navigation"] = adb_nav

        # ========== 应用管理工具集 ==========
        app_mgmt = ToolSetMetadata(
            id="app_management",
            name="应用管理工具集",
            description="用于启动和管理应用程序",
            index_prompt="应用、启动、打开、APP",
            tools=[
                ToolMetadata(
                    name="Launch",
                    description="启动指定的应用程序",
                    parameters={"app": "应用名称"},
                    example='do(action="Launch", app="微信")'
                ),
            ]
        )
        self._tool_sets["app_management"] = app_mgmt

        # ========== 输入工具集 ==========
        input_tools = ToolSetMetadata(
            id="input_tools",
            name="输入工具集",
            description="用于文本输入操作",
            index_prompt="输入、打字、文本、键盘",
            tools=[
                ToolMetadata(
                    name="Type",
                    description="在当前聚焦的输入框中输入文本",
                    parameters={"text": "要输入的文本"},
                    example='do(action="Type", text="Hello")'
                ),
                ToolMetadata(
                    name="Type_Name",
                    description="输入人名",
                    parameters={"text": "人名"},
                    example='do(action="Type_Name", text="张三")'
                ),
            ]
        )
        self._tool_sets["input_tools"] = input_tools

        # ========== 文件处理工具集 ==========
        file_tools = ToolSetMetadata(
            id="file_tools",
            name="文件处理工具集",
            description="用于 Excel 文件读取和批量处理",
            index_prompt="文件、Excel、批量、读取、写入、答案",
            tools=[
                ToolMetadata(
                    name="ReadExcel",
                    description="读取 Excel 文件内容并返回摘要",
                    parameters={
                        "file": "Excel 文件路径",
                        "column": "(可选) 指定读取的列名"
                    },
                    example='do(action="ReadExcel", file="questions.xlsx")'
                ),
                ToolMetadata(
                    name="Execute_Excel_Batch",
                    description="批量执行 Excel 中的任务",
                    parameters={
                        "file": "Excel 文件路径",
                        "task": "任务模板，可使用{content}占位符",
                        "column": "(可选) 问题列名，默认'问题'",
                        "embed_screenshot": "(可选) 是否嵌入截图",
                        "compare_answer": "(可选) 是否对比标准答案",
                        "max_questions": "(可选) 最大问题数，0 表示全部"
                    },
                    example='do(action="Execute_Excel_Batch", file="questions.xlsx", task="请回答：{content}")'
                ),
                ToolMetadata(
                    name="GetExcelQuestion",
                    description="获取 Excel 中下一道待处理的问题（命令行方式）",
                    parameters={
                        "file": "Excel 文件路径",
                        "row": "(可选) 指定行号，不指定则自动查找待处理的行"
                    },
                    example='do(action="GetExcelQuestion", file="questions.xlsx")'
                ),
                ToolMetadata(
                    name="WriteExcelAnswer",
                    description="将答案写入 Excel 指定行（命令行方式）",
                    parameters={
                        "file": "Excel 文件路径",
                        "row": "行号",
                        "answer": "答案内容"
                    },
                    example='do(action="WriteExcelAnswer", file="questions.xlsx", row=2, answer="这是答案")'
                ),
            ]
        )
        self._tool_sets["file_tools"] = file_tools

        # ========== 系统辅助工具集 ==========
        sys_tools = ToolSetMetadata(
            id="system_tools",
            name="系统辅助工具集",
            description="系统级辅助操作",
            index_prompt="系统、接管、交互、笔记、API、辅助",
            tools=[
                ToolMetadata(
                    name="Take_over",
                    description="请求用户接管（登录、验证码等）",
                    parameters={"message": "接管原因说明"},
                    example='do(action="Take_over", message="需要用户登录")'
                ),
                ToolMetadata(
                    name="Interact",
                    description="请求用户选择（有多个选项时）",
                    parameters={},
                    example='do(action="Interact")'
                ),
                ToolMetadata(
                    name="Note",
                    description="记录当前页面内容",
                    parameters={"message": "记录的内容"},
                    example='do(action="Note", message="当前页面显示...")'
                ),
                ToolMetadata(
                    name="Call_API",
                    description="总结或评论当前页面内容",
                    parameters={"instruction": "总结指令"},
                    example='do(action="Call_API", instruction="总结以上内容")'
                ),
            ]
        )
        self._tool_sets["system_tools"] = sys_tools

    def list_tool_sets(self) -> list[dict[str, str]]:
        """
        获取所有工具集的索引列表（简化版，用于主提示词）。

        Returns:
            工具集索引列表，每项包含 id, name, description
        """
        return [
            {
                "id": ts.id,
                "name": ts.name,
                "description": ts.description,
            }
            for ts in self._tool_sets.values()
        ]

    def get_tool_set_info(self, set_name: str) -> Optional[dict[str, Any]]:
        """
        获取工具集的详细信息（包含工具列表，不含详细用法）。

        Args:
            set_name: 工具集 ID

        Returns:
            工具集信息字典，如果不存在则返回 None
        """
        tool_set = self._tool_sets.get(set_name)
        if not tool_set:
            return None

        return {
            "id": tool_set.id,
            "name": tool_set.name,
            "description": tool_set.description,
            "index_prompt": tool_set.index_prompt,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                }
                for t in tool_set.tools
            ]
        }

    def get_tool_details(self, set_name: str, tool_name: str) -> Optional[dict[str, Any]]:
        """
        获取具体工具的详细使用说明。

        Args:
            set_name: 工具集 ID
            tool_name: 工具名称

        Returns:
            工具详细信息字典，如果不存在则返回 None
        """
        tool_set = self._tool_sets.get(set_name)
        if not tool_set:
            return None

        for tool in tool_set.tools:
            if tool.name == tool_name:
                return {
                    "set_id": set_name,
                    "set_name": tool_set.name,
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "example": tool.example,
                }

        return None

    def get_all_tool_details(self) -> dict[str, list[dict[str, Any]]]:
        """
        获取所有工具的详细信息（用于完整文档）。

        Returns:
            以工具集 ID 为键的工具详情字典
        """
        result = {}
        for set_id, tool_set in self._tool_sets.items():
            result[set_id] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                    "example": t.example,
                }
                for t in tool_set.tools
            ]
        return result

    def search_tool_sets(self, keyword: str) -> list[str]:
        """
        根据关键词搜索相关的工具集。

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的工具集 ID 列表
        """
        matched = []
        for set_id, tool_set in self._tool_sets.items():
            # 在 ID、名称、描述、索引提示中搜索
            search_text = f"{set_id} {tool_set.name} {tool_set.description} {tool_set.index_prompt}".lower()
            if keyword.lower() in search_text:
                matched.append(set_id)
        return matched

    def register_tool_set(self, metadata: ToolSetMetadata) -> None:
        """
        注册新的工具集。

        Args:
            metadata: 工具集元数据
        """
        self._tool_sets[metadata.id] = metadata

    def get_handler(self, action_name: str) -> Optional[Callable]:
        """
        获取动作的处理函数。

        Args:
            action_name: 动作名称

        Returns:
            处理函数，如果不存在则返回 None
        """
        return self._tool_handlers.get(action_name)

    def register_handler(self, action_name: str, handler: Callable) -> None:
        """
        注册动作处理函数。

        Args:
            action_name: 动作名称
            handler: 处理函数
        """
        self._tool_handlers[action_name] = handler


# 全局单例
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册表实例。"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def list_tool_sets() -> list[dict[str, str]]:
    """获取所有工具集的索引列表。"""
    return get_registry().list_tool_sets()


def get_tool_set_info(set_name: str) -> Optional[dict[str, Any]]:
    """获取工具集的详细信息。"""
    return get_registry().get_tool_set_info(set_name)


def get_tool_details(set_name: str, tool_name: str) -> Optional[dict[str, Any]]:
    """获取具体工具的详细使用说明。"""
    return get_registry().get_tool_details(set_name, tool_name)
