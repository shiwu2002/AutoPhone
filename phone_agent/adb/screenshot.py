"""用于捕获 Android 设备截图的截图工具。"""

import base64
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Tuple

from PIL import Image

from phone_agent.adb.cmd_executor import CommandExecutor, is_console_mode_enabled


@dataclass
class Screenshot:
    """表示捕获的截图。"""

    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


def get_screenshot(device_id: str | None = None, timeout: int = 10) -> Screenshot:
    """
    从已连接的 Android 设备捕获截图。

    Args:
        device_id: 用于多设备设置的可选 ADB 设备 ID。
        timeout: 截图操作的超时时间（秒）。

    Returns:
        包含 base64 数据和尺寸的 Screenshot 对象。

    Note:
        如果截图失败（例如在支付页面等敏感屏幕上），
        将返回一个黑色回退图像并设置 is_sensitive=True。
    """
    temp_path = os.path.join(tempfile.gettempdir(), f"screenshot_{uuid.uuid4()}.png")
    adb_prefix = _get_adb_prefix(device_id)

    try:
        # Execute screenshot command - 使用静默模式，因为需要获取输出
        result = CommandExecutor.run_silent(
            adb_prefix + ["shell", "screencap", "-p", "/sdcard/tmp.png"],
            timeout=timeout,
        )

        # Check for screenshot failure (sensitive screen)
        output = result.stdout + result.stderr
        if "Status: -1" in output or "Failed" in output:
            return _create_fallback_screenshot(is_sensitive=True)

        # Pull screenshot to local temp path - 使用静默模式
        CommandExecutor.run_silent(
            adb_prefix + ["pull", "/sdcard/tmp.png", temp_path],
            timeout=5,
        )

        if not os.path.exists(temp_path):
            return _create_fallback_screenshot(is_sensitive=False)

        # Read and encode image
        img = Image.open(temp_path)
        width, height = img.size

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Cleanup
        os.remove(temp_path)

        return Screenshot(
            base64_data=base64_data, width=width, height=height, is_sensitive=False
        )

    except Exception as e:
        print(f"Screenshot error: {e}")
        return _create_fallback_screenshot(is_sensitive=False)


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specification.

    If device_id is not specified and multiple devices are connected,
    use the first device.
    """
    if device_id:
        return ["adb", "-s", device_id]

    # Check for multiple devices
    try:
        result = CommandExecutor.run_silent(["adb", "devices"], timeout=5)
        devices = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            if line.strip() and "\tdevice" in line:
                devices.append(line.split("\t")[0].strip())

        if len(devices) == 0:
            raise ValueError("No connected devices")
        elif len(devices) > 1:
            # Use first device by default
            return ["adb", "-s", devices[0]]
    except Exception:
        pass

    return ["adb"]


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """当截图失败时创建黑色回退图像。"""
    default_width, default_height = 1080, 2400

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return Screenshot(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        is_sensitive=is_sensitive,
    )
