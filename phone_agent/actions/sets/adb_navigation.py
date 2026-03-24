"""ADB 导航工具集 - 返回、主页、等待等操作。"""

import time
from typing import Any, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.device_factory import get_device_factory
from phone_agent.actions.result import ActionResult


def handle_back(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理返回动作。

    Args:
        action: 动作字典
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    device_factory = get_device_factory()
    device_factory.back(device_id)
    return ActionResult(True, False)


def handle_home(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理主页动作。

    Args:
        action: 动作字典
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    device_factory = get_device_factory()
    device_factory.home(device_id)
    return ActionResult(True, False)


def handle_wait(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理等待动作。

    Args:
        action: 动作字典，包含 duration="x seconds"
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    duration_str = action.get("duration", "1 seconds")
    try:
        duration = float(duration_str.replace("seconds", "").strip())
    except ValueError:
        duration = 1.0

    time.sleep(duration)
    return ActionResult(True, False)
