"""系统辅助工具集 - 接管、交互、笔记、API 调用等。"""

from typing import Any, Callable, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.actions.result import ActionResult


def handle_takeover(
    action: dict[str, Any],
    screenshot: Screenshot,
    device_id: Optional[str] = None,
    takeover_callback: Optional[Callable[[str], None]] = None,
    **kwargs,
) -> ActionResult:
    """
    处理接管请求动作（登录、验证码等）。

    Args:
        action: 动作字典，包含 message="接管原因"
        screenshot: Screenshot 对象
        device_id: 设备 ID
        takeover_callback: 接管回调函数

    Returns:
        ActionResult: 执行结果
    """
    message = action.get("message", "User intervention required")
    if takeover_callback:
        takeover_callback(message)
    return ActionResult(True, False, message="已请求用户接管")


def handle_interact(
    action: dict[str, Any],
    screenshot: Screenshot,
    device_id: Optional[str] = None,
    **kwargs,
) -> ActionResult:
    """
    处理交互请求动作（需要用户选择）。

    Args:
        action: 动作字典
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    return ActionResult(True, False, message="User interaction required")


def handle_note(
    action: dict[str, Any],
    screenshot: Screenshot,
    device_id: Optional[str] = None,
    **kwargs,
) -> ActionResult:
    """
    处理笔记动作（记录页面内容）。

    Args:
        action: 动作字典，包含 message="记录内容"
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    # 笔记动作用于记录页面内容，供后续总结使用
    message = action.get("message", "")
    return ActionResult(True, False, message=f"已记录：{message[:100]}...")


def handle_call_api(
    action: dict[str, Any],
    screenshot: Screenshot,
    device_id: Optional[str] = None,
    **kwargs,
) -> ActionResult:
    """
    处理 API 调用动作（总结/评论内容）。

    Args:
        action: 动作字典，包含 instruction="总结指令"
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    # API 调用动作用于总结或评论内容
    instruction = action.get("instruction", "总结以上内容")
    return ActionResult(True, False, message=f"已执行分析：{instruction}")
