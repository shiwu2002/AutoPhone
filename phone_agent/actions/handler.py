"""用于处理 AI 模型输出的动作处理器。"""

import ast
import time
from collections import defaultdict
from typing import Any, Callable, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.config.timing import TIMING_CONFIG
from phone_agent.device_factory import get_device_factory
from phone_agent.tools.registry import get_registry, list_tool_sets, get_tool_set_info, get_tool_details
from phone_agent.actions.result import ActionResult
from phone_agent.actions.sets import TOOL_HANDLERS
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


class ActionHandler:
    """
    处理来自 AI 模型的动作执行。

    Args:
        device_id: 用于多设备设置的可选 ADB 设备 ID。
        confirmation_callback: 用于敏感操作确认的可选回调。
            应返回 True 以继续，False 以取消。
        takeover_callback: 用于接管请求的可选回调（登录、验证码等）。
        model_config: 模型配置（用于 Excel 批量处理工具）。
        agent_config: Agent 配置（用于 Excel 批量处理工具）。
    """

    # ========== 防死循环配置 ==========
    MAX_CONSECUTIVE_FAILURES = 3  # 最大连续失败次数，超过后提示换方法
    FAIL_FAST = False  # 连续失败达到阈值后是否直接终止任务，False=让大模型决定，True=直接结束

    def __init__(
        self,
        device_id: Optional[str] = None,
        confirmation_callback: Optional[Callable[[str], bool]] = None,
        takeover_callback: Optional[Callable[[str], None]] = None,
        model_config: Optional[Any] = None,
        agent_config: Optional[Any] = None,
    ):
        self.device_id = device_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover
        self.model_config = model_config
        self.agent_config = agent_config
        self.registry = get_registry()

        # ========== 失败统计变量 ==========
        self._consecutive_failures = 0  # 全局连续失败次数
        self._action_fail_counts = defaultdict(int)  # 每个动作的失败次数

    def execute(
        self, action: dict[str, Any], screenshot: Screenshot
    ) -> ActionResult:
        """执行来自 AI 模型的动作。

        Args:
            action: 来自模型的动作字典
            screenshot: Screenshot 对象，包含屏幕尺寸和坐标映射器

        Returns:
            ActionResult: 动作执行结果，包含成功状态和是否结束
        """
        action_type = action.get("_metadata")

        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )

        # 处理工具查询动作
        if action_type == "query":
            return self._handle_query_action(action, screenshot)

        if action_type != "do":
            return ActionResult(
                success=False,
                should_finish=True,
                message=f"Unknown action type: {action_type}",
            )

        action_name = action.get("action")
        if action_name is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message="No action specified in the command",
            )

        # 先尝试从工具集处理器中查找
        handler_method = TOOL_HANDLERS.get(action_name)

        if handler_method is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Unknown action: {action_name}",
            )

        try:
            # 调用处理函数，传入必要的上下文
            try:
                result = handler_method(
                    action,
                    screenshot,
                    device_id=self.device_id,
                    model_config=self.model_config,
                    agent_config=self.agent_config,
                    takeover_callback=self.takeover_callback,
                )
            except TypeError:
                # 向后兼容：如果处理函数不需要额外参数
                result = handler_method(action, screenshot)

            # ========== 执行成功，重置失败计数器 ==========
            if result.success:
                self._consecutive_failures = 0
                action_name = action.get("action", "unknown")
                if action_name in self._action_fail_counts:
                    self._action_fail_counts[action_name] = 0

            return result

        except Exception as e:
            logger.error(f"Action failed: {e}", exc_info=True)

            # ========== 失败统计和防死循环逻辑 ==========
            self._consecutive_failures += 1
            action_name = action.get("action", "unknown")
            self._action_fail_counts[action_name] += 1
            action_fail_count = self._action_fail_counts[action_name]

            # 基础错误信息
            base_msg = f"Action failed: {str(e)}"
            error_msg = base_msg
            should_finish = False

            # 1. 全局连续失败达到阈值的处理
            if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                error_msg = (
                    f"⚠️ 已经连续失败{self._consecutive_failures}次，请勿再重复相同操作！"
                    f"请尝试其他方法（比如返回上一页、重新进入应用、调整坐标等），如果无法完成任务请直接结束。"
                    f"本次错误：{str(e)}"
                )
                should_finish = self.FAIL_FAST  # 根据配置决定是否直接结束

            # 2. 单个动作多次失败的提示
            elif action_fail_count >= 2:
                error_msg = (
                    f"⚠️ 动作[{action_name}]已经失败{action_fail_count}次，请调整参数后重试或者更换其他操作。"
                    f"本次错误：{str(e)}"
                )

            # 3. 针对特定错误类型的个性化提示
            error_lower = str(e).lower()
            if "coordinate out of bounds" in error_lower or "outside screen" in error_lower or "超出屏幕" in error_lower:
                error_msg = f"❌ 点击坐标超出屏幕范围，请调整坐标值（有效范围0-1000）后重试。错误：{str(e)}"
            elif "app not found" in error_lower or "没有找到应用" in error_lower or "未安装" in error_lower:
                error_msg = f"❌ 应用未安装，请确认应用名称正确或者更换其他应用。错误：{str(e)}"
                should_finish = True  # 应用未安装直接结束，没必要重试
            elif "input method not ready" in error_lower or "输入法" in error_lower:
                error_msg = f"❌ 输入法未准备好，请先点击输入框激活后再尝试输入。错误：{str(e)}"
            elif "timeout" in error_lower or "超时" in error_lower:
                error_msg = f"⚠️ 操作超时，可能是页面未加载完成，请稍等片刻后重试或者返回上一页。错误：{str(e)}"
            elif "permission denied" in error_lower or "权限" in error_lower:
                error_msg = f"❌ 权限不足，无法执行该操作，请开启相应权限后重试。错误：{str(e)}"
                should_finish = True  # 权限问题无法通过重试解决

            # 返回结果
            return ActionResult(
                success=False,
                should_finish=should_finish,
                message=error_msg
            )

    def _handle_query_action(self, action: dict[str, Any], screenshot: Screenshot) -> ActionResult:
        """
        处理工具查询动作。

        Args:
            action: 查询动作字典
            screenshot: Screenshot 对象

        Returns:
            ActionResult: 查询结果
        """
        query_type = action.get("query_type")

        if query_type == "GetToolIndex":
            # 获取所有工具集索引
            tool_sets = list_tool_sets()
            message = "可用工具集索引：\n\n"
            for ts in tool_sets:
                message += f"- {ts['id']}: {ts['name']} ({ts['description']})\n"
            message += "\n查看工具集详情：do(action=\"GetToolSet\", set_name=\"adb_ui\")"
            return ActionResult(True, False, message=message)

        elif query_type == "GetToolSet":
            # 获取指定工具集的详细信息
            set_name = action.get("set_name")
            if not set_name:
                return ActionResult(False, False, "GetToolSet 需要 set_name 参数")

            info = get_tool_set_info(set_name)
            if not info:
                return ActionResult(False, False, f"工具集不存在：{set_name}")

            message = f"工具集：{info['name']}\n"
            message += f"描述：{info['description']}\n"
            message += f"适用场景：{info['index_prompt']}\n\n"
            message += "包含工具：\n"
            for tool in info['tools']:
                message += f"  - {tool['name']}: {tool['description']}\n"
            message += f"\n查看工具详情：do(action=\"GetTool\", set_name=\"{set_name}\", tool_name=\"Tap\")"
            return ActionResult(True, False, message=message)

        elif query_type == "GetTool":
            # 获取具体工具的详细使用说明
            set_name = action.get("set_name")
            tool_name = action.get("tool_name")

            if not set_name or not tool_name:
                return ActionResult(False, False, "GetTool 需要 set_name 和 tool_name 参数")

            details = get_tool_details(set_name, tool_name)
            if not details:
                return ActionResult(False, False, f"工具不存在：{set_name}.{tool_name}")

            message = f"工具：{details['name']}\n"
            message += f"所属工具集：{details['set_name']}\n"
            message += f"描述：{details['description']}\n\n"
            message += "参数：\n"
            for param, desc in details['parameters'].items():
                message += f"  - {param}: {desc}\n"
            message += f"\n示例：{details['example']}"
            return ActionResult(True, False, message=message)

        else:
            return ActionResult(False, False, f"Unknown query type: {query_type}")

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """使用控制台输入的默认确认回调。"""
        response = input(f"Sensitive operation: {message}\nConfirm? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """使用控制台输入的默认接管回调。"""
        input(f"{message}\nPress Enter after completing manual operation...")


def parse_action(response: str) -> dict[str, Any]:
    """
    从模型响应中解析动作。

    Args:
        response: 来自模型的原始响应字符串。

    Returns:
        解析后的动作字典。

    Raises:
        ValueError: 如果响应无法解析。
    """
    print(f"Parsing action: {response}")
    try:
        response = response.strip()

        # 处理工具查询动作
        if response.startswith('do(action="GetToolIndex")'):
            return {"_metadata": "query", "query_type": "GetToolIndex"}
        elif response.startswith('do(action="GetToolSet"'):
            try:
                response = response.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                tree = ast.parse(response, mode="eval")
                if isinstance(tree.body, ast.Call):
                    call = tree.body
                    action = {"_metadata": "query", "query_type": "GetToolSet"}
                    for keyword in call.keywords:
                        key = keyword.arg
                        if key is None:
                            raise ValueError("Unnamed keyword argument")
                        value = ast.literal_eval(keyword.value)
                        action[key] = value
                    return action
            except (SyntaxError, ValueError) as e:
                raise ValueError(f"Failed to parse GetToolSet: {e}")
        elif response.startswith('do(action="GetTool"'):
            try:
                response = response.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                tree = ast.parse(response, mode="eval")
                if isinstance(tree.body, ast.Call):
                    call = tree.body
                    action = {"_metadata": "query", "query_type": "GetTool"}
                    for keyword in call.keywords:
                        key = keyword.arg
                        if key is None:
                            raise ValueError("Unnamed keyword argument")
                        value = ast.literal_eval(keyword.value)
                        action[key] = value
                    return action
            except (SyntaxError, ValueError) as e:
                raise ValueError(f"Failed to parse GetTool: {e}")

        # 处理 Type/Type_Name 特殊情况
        if response.startswith('do(action="Type"') or response.startswith(
            'do(action="Type_Name"'
        ):
            text = response.split("text=", 1)[1][1:-2]
            action = {"_metadata": "do", "action": "Type", "text": text}
            return action

        # 处理标准 do 动作
        elif response.startswith("do"):
            try:
                response = response.replace('\n', '\\n')
                response = response.replace('\r', '\\r')
                response = response.replace('\t', '\\t')

                tree = ast.parse(response, mode="eval")
                if not isinstance(tree.body, ast.Call):
                    raise ValueError("Expected a function call")

                call = tree.body
                action = {"_metadata": "do"}
                for keyword in call.keywords:
                    key = keyword.arg
                    if key is None:
                        raise ValueError("Unnamed keyword argument in action")
                    value = ast.literal_eval(keyword.value)
                    action[key] = value

                return action
            except (SyntaxError, ValueError) as e:
                raise ValueError(f"Failed to parse do() action: {e}")

        # 处理 finish 动作
        elif response.startswith("finish"):
            action = {
                "_metadata": "finish",
                "message": response.replace("finish(message=", "")[1:-2],
            }
            return action
        else:
            raise ValueError(f"Failed to parse action: {response}")
    except Exception as e:
        raise ValueError(f"Failed to parse action: {e}")


def do(**kwargs: Any) -> dict[str, Any]:
    """用于创建 'do' 动作的辅助函数。"""
    kwargs["_metadata"] = "do"
    return kwargs


def finish(**kwargs: Any) -> dict[str, Any]:
    """用于创建 'finish' 动作的辅助函数。"""
    kwargs["_metadata"] = "finish"
    return kwargs
