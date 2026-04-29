"""用于捕获 Android 设备截图的截图工具。"""

import base64
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from phone_agent.adb.cmd_executor import CommandExecutor
from phone_agent.utils.resolution import ResolutionConverter, CoordinateMapper


@dataclass
class Screenshot:
    """表示捕获的截图。"""

    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False
    # 分辨率转换相关
    converter: ResolutionConverter | None = None
    mapper: CoordinateMapper | None = None
    original_width: int | None = None
    original_height: int | None = None


def get_screenshot(device_id: str | None = None, timeout: int = 10, enable_compression: bool = True) -> Screenshot:
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
        # Execute screenshot command
        # 执行ADB截屏命令，将截图保存到手机的/sdcard/tmp.png路径
        # screencap是Android系统自带的截屏工具，-p参数表示输出PNG格式
        result = subprocess.run(
            adb_prefix + ["shell", "screencap", "-p", "/sdcard/tmp.png"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 检查截屏是否失败（通常是因为当前页面是敏感页面，如支付、银行APP禁止截屏）
        output = result.stdout + result.stderr
        if "Status: -1" in output or "Failed" in output:
            # 截屏失败时返回黑色 fallback 图片，并标记为敏感页面
            return _create_fallback_screenshot(is_sensitive=True)

        # 将保存在手机上的截图文件拉取到本地电脑的临时目录
        subprocess.run(
            adb_prefix + ["pull", "/sdcard/tmp.png", temp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # 检查拉取是否成功，如果本地临时文件不存在则返回 fallback 图片
        if not os.path.exists(temp_path):
            return _create_fallback_screenshot(is_sensitive=False)

        # 读取本地截图文件并进行处理
        img = Image.open(temp_path)
        original_width, original_height = img.size  # 记录原始屏幕分辨率

        # 如果开启了压缩功能（默认开启），则将图片压缩到1080p以减少token消耗
        converter = None
        mapper = None
        if enable_compression:
            converter = ResolutionConverter()
            img = converter.compress_to_1k(img)  # 等比例压缩到宽度1080像素
            # 创建坐标映射器，用于后续将大模型返回的压缩图坐标转换回实际屏幕坐标
            mapper = CoordinateMapper.from_converter(converter)

        width, height = img.size  # 压缩后的图片尺寸

        # 将处理后的图片转换为Base64编码，方便传给大模型接口
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 清理本地临时文件，避免占用磁盘空间
        os.remove(temp_path)

        # 封装成Screenshot对象返回，包含所有需要的信息
        return Screenshot(
            base64_data=base64_data,      # Base64编码的图片数据
            width=width,                  # 压缩后的图片宽度
            height=height,                # 压缩后的图片高度
            is_sensitive=False,           # 是否是敏感页面截图
            converter=converter,          # 分辨率转换器实例
            mapper=mapper,                # 坐标映射器实例
            original_width=original_width,# 原始屏幕宽度
            original_height=original_height# 原始屏幕高度
        )

    # 捕获所有异常，保证流程不会因为截屏失败而中断
    except Exception as e:
        print(f"Screenshot error: {e}")
        # 发生异常时返回 fallback 图片
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
        converter=None,
        original_width=None,
        original_height=None
    )
