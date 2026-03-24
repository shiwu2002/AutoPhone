"""用于捕获 Android 设备截图的截图工具 - 优化版。

优化点:
1. 分离 ScreenshotData (DTO) 和 Screenshot (业务对象)
2. is_sensitive 触发异常而非静默返回
3. 简化坐标映射器的使用
"""

import base64
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from PIL import Image

from phone_agent.adb.cmd_executor import CommandExecutor
from phone_agent.utils.resolution import ResolutionConverter, CoordinateMapper


@dataclass
class ScreenshotData:
    """
    截图数据传输对象 (DTO) - 仅包含原始数据。

    用于跨模块传递，不包含业务逻辑。
    """
    base64_data: str
    width: int
    height: int
    original_width: Optional[int] = None
    original_height: Optional[int] = None


@dataclass
class Screenshot:
    """
    截图业务对象 - 包含完整功能和元数据。

    Attributes:
        data: 原始截图数据
        is_sensitive: 是否为敏感屏幕（支付页面等）
        converter: 分辨率转换器
        mapper: 坐标映射器
    """

    data: ScreenshotData
    is_sensitive: bool = False
    converter: Optional[ResolutionConverter] = None
    mapper: Optional[CoordinateMapper] = None

    @property
    def base64_data(self) -> str:
        """获取 base64 数据。"""
        return self.data.base64_data

    @property
    def width(self) -> int:
        """获取当前宽度（压缩后）。"""
        return self.data.width

    @property
    def height(self) -> int:
        """获取当前高度（压缩后）。"""
        return self.data.height

    @property
    def original_width(self) -> Optional[int]:
        """获取原始宽度。"""
        return self.data.original_width

    @property
    def original_height(self) -> Optional[int]:
        """获取原始高度。"""
        return self.data.original_height

    def to_dict(self) -> dict:
        """转换为字典（用于 API 传输）。"""
        return {
            "base64_data": self.base64_data,
            "width": self.width,
            "height": self.height,
            "original_width": self.original_width,
            "original_height": self.original_height,
            "is_sensitive": self.is_sensitive,
        }

    @classmethod
    def from_data(cls, data: ScreenshotData) -> "Screenshot":
        """从 ScreenshotData 创建 Screenshot。"""
        return cls(data=data)


class SensitiveScreenError(Exception):
    """敏感屏幕异常 - 当无法截图时抛出（如支付页面）。"""
    pass


def get_screenshot(
    device_id: Optional[str] = None,
    timeout: int = 10,
    enable_compression: bool = True,
    raise_on_sensitive: bool = False,
) -> Screenshot:
    """
    从已连接的 Android 设备捕获截图。

    Args:
        device_id: 可选的 ADB 设备 ID。
        timeout: 截图超时时间（秒）。
        enable_compression: 是否压缩图像到 1000px。
        raise_on_sensitive: 敏感屏幕是否抛出异常（默认返回黑色截图）。

    Returns:
        Screenshot 对象。

    Raises:
        SensitiveScreenError: 当 is_sensitive=True 且 raise_on_sensitive=True 时。
    """
    temp_path = os.path.join(tempfile.gettempdir(), f"screenshot_{uuid.uuid4()}.png")
    adb_prefix = _get_adb_prefix(device_id)

    try:
        # 执行截图命令
        result = subprocess.run(
            adb_prefix + ["shell", "screencap", "-p", "/sdcard/tmp.png"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 检查截图失败（敏感屏幕）
        output = result.stdout + result.stderr
        if "Status: -1" in output or "Failed" in output:
            if raise_on_sensitive:
                raise SensitiveScreenError("无法截图，可能是敏感屏幕（支付/密码页面）")
            return _create_fallback_screenshot(is_sensitive=True)

        # 拉取截图到本地
        subprocess.run(
            adb_prefix + ["pull", "/sdcard/tmp.png", temp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if not os.path.exists(temp_path):
            return _create_fallback_screenshot(is_sensitive=False)

        # 读取并处理图像
        img = Image.open(temp_path)
        original_width, original_height = img.size

        # 压缩图像
        converter = None
        mapper = None
        if enable_compression:
            converter = ResolutionConverter()
            img = converter.compress_to_1k(img)
            mapper = CoordinateMapper.from_converter(converter)

        width, height = img.size

        # 转换为 base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 清理临时文件
        os.remove(temp_path)

        # 创建数据对象
        data = ScreenshotData(
            base64_data=base64_data,
            width=width,
            height=height,
            original_width=original_width,
            original_height=original_height,
        )

        # 创建业务对象
        return Screenshot(
            data=data,
            is_sensitive=False,
            converter=converter,
            mapper=mapper,
        )

    except SensitiveScreenError:
        raise
    except Exception as e:
        print(f"Screenshot error: {e}")
        if raise_on_sensitive:
            raise
        return _create_fallback_screenshot(is_sensitive=False)


def _get_adb_prefix(device_id: Optional[str]) -> list:
    """获取 ADB 命令前缀。"""
    if device_id:
        return ["adb", "-s", device_id]

    # 检查多设备
    try:
        result = CommandExecutor.run_silent(["adb", "devices"], timeout=5)
        devices = []
        for line in result.stdout.strip().split("\n")[1:]:
            if line.strip() and "\tdevice" in line:
                devices.append(line.split("\t")[0].strip())

        if len(devices) == 0:
            raise ValueError("No connected devices")
        elif len(devices) > 1:
            return ["adb", "-s", devices[0]]
    except Exception:
        pass

    return ["adb"]


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """创建黑色回退图像。"""
    default_width, default_height = 1080, 2400

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    data = ScreenshotData(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        original_width=None,
        original_height=None,
    )

    return Screenshot(
        data=data,
        is_sensitive=is_sensitive,
        converter=None,
        mapper=None,
    )
