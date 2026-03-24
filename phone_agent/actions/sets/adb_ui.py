"""ADB UI 交互工具集 - 点击、滑动等操作。"""

from typing import Any, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.device_factory import get_device_factory
from phone_agent.actions.result import ActionResult
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


def _convert_relative_to_absolute(
    element: list[int],
    screenshot: Screenshot,
    use_region: bool = False,
) -> tuple[int, int] | tuple[tuple[int, int], tuple[int, int]]:
    """
    将相对坐标 (0-1000) 转换为绝对像素。

    Args:
        element: [x, y] 相对坐标
        screenshot: Screenshot 对象
        use_region: 是否返回区域而非单点

    Returns:
        如果是单点：(x, y)
        如果是区域：((x1, y1), (x2, y2))
    """
    if screenshot.mapper is None:
        x = int(element[0] / 1000 * screenshot.width)
        y = int(element[1] / 1000 * screenshot.height)
        return (x, y) if not use_region else ((x, y), (x, y))

    x_1k = element[0] / 1000 * screenshot.width
    y_1k = element[1] / 1000 * screenshot.height

    if use_region:
        return screenshot.mapper.to_original_region(x_1k, y_1k)
    else:
        return screenshot.mapper.to_original_coordinate(x_1k, y_1k, add_click_offset=False)


def handle_tap(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理点击动作。

    Args:
        action: 动作字典，包含 element=[x,y]
        screenshot: Screenshot 对象
        device_id: 设备 ID
        **kwargs: 额外参数（用于向后兼容）

    Returns:
        ActionResult: 执行结果
    """
    element = action.get("element")
    if not element:
        return ActionResult(False, False, "No element coordinates")

    x, y = _convert_relative_to_absolute(element, screenshot)
    device_factory = get_device_factory()
    try:
        device_factory.tap(x, y, device_id)
        return ActionResult(True, False)
    except Exception as e:
        logger.error(f"handle_tap: 执行失败 - {e}", exc_info=True)
        return ActionResult(False, False, f"Tap failed: {e}")


def handle_double_tap(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理双击动作。

    Args:
        action: 动作字典，包含 element=[x,y]
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    element = action.get("element")
    if not element:
        return ActionResult(False, False, "No element coordinates")

    x, y = _convert_relative_to_absolute(element, screenshot)
    device_factory = get_device_factory()
    device_factory.double_tap(x, y, device_id)
    return ActionResult(True, False)


def handle_long_press(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理长按动作。

    Args:
        action: 动作字典，包含 element=[x,y]
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    element = action.get("element")
    if not element:
        return ActionResult(False, False, "No element coordinates")

    x, y = _convert_relative_to_absolute(element, screenshot)
    device_factory = get_device_factory()
    device_factory.long_press(x, y, device_id=device_id)
    return ActionResult(True, False)


def handle_swipe(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理滑动动作。

    Args:
        action: 动作字典，包含 start=[x1,y1], end=[x2,y2]
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    start = action.get("start")
    end = action.get("end")

    if not start or not end:
        return ActionResult(False, False, "Missing swipe coordinates")

    start_x, start_y = _convert_relative_to_absolute(start, screenshot)
    end_x, end_y = _convert_relative_to_absolute(end, screenshot)

    device_factory = get_device_factory()
    device_factory.swipe(start_x, start_y, end_x, end_y, device_id=device_id)
    return ActionResult(True, False)
