"""应用管理工具集 - 启动应用等操作。"""

from typing import Any, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.device_factory import get_device_factory
from phone_agent.actions.result import ActionResult


def handle_launch(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理启动应用动作。

    Args:
        action: 动作字典，包含 app="应用名称"
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    app_name = action.get("app")
    if not app_name:
        return ActionResult(False, False, "No app name specified")

    device_factory = get_device_factory()
    success = device_factory.launch_app(app_name, device_id)
    if success:
        return ActionResult(True, False)
    return ActionResult(False, False, f"App not found: {app_name}")
